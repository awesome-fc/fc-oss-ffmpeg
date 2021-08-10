# -*- coding: utf-8 -*-
import subprocess
import oss2
import logging
import json
import os
import time

logging.getLogger("oss2.api").setLevel(logging.ERROR)
logging.getLogger("oss2.auth").setLevel(logging.ERROR)

LOGGER = logging.getLogger()

'''
1. function and bucket locate in same region
2. service's role has OSSFullAccess
3. event format
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4",
    "output_dir" : "output/",
    "tile": "3*4",
    "start": 0,
    "duration": 10,
    "itsoffset": 0,
    "scale": "-1:-1",
    "interval": 2,
    "padding": 1, 
    "color": "black",
    "dst_type": "jpg"
}
tile: 必填， 雪碧图的 rows * cols
start: 可选， 默认是为 0
duration: 可选，表示基于 start 之后的多长时间的视频内进行截图，
比如 start 为 10， duration 为 20，表示基于视频的10s-30s内进行截图
interval: 可选，每隔多少秒截图一次， 默认为 1
scale: 可选，截图的大小, 默认为 -1:-1， 默认为原视频大小, 320:240, iw/2:ih/2 
itsoffset: 可选，默认为 0, delay多少秒，配合start、interval使用
- 假设 start 为 0， interval 为 10，itsoffset 为 0， 那么截图的秒数为 5， 15， 25 ...
- 假设 start 为 0， interval 为 10，itsoffset 为 1， 那么截图的秒数为 4， 14， 24 ...
- 假设 start 为 0， interval 为 10，itsoffset 为 4.999(不要写成5，不然会丢失0秒的那一帧图)， 那么截图的秒数为 0， 10， 20 ...
- 假设 start 为 0， interval 为 10，itsoffset 为 -1， 那么截图的秒数为 6， 16，26 ...
padding: 可选，图片之间的间隔, 默认为 0
color: 可选，雪碧图背景颜色，默认黑色， https://ffmpeg.org/ffmpeg-utils.html#color-syntax
dst_type: 可选，生成的雪碧图图片格式，默认为 jpg，主要为 jpg 或者 png， https://ffmpeg.org/ffmpeg-all.html#image2-1
'''

# a decorator for print the excute time of a function


def print_excute_time(func):
    def wrapper(*args, **kwargs):
        local_time = time.time()
        ret = func(*args, **kwargs)
        LOGGER.info('current Function [%s] excute time is %.2f seconds' %
                    (func.__name__, time.time() - local_time))
        return ret
    return wrapper


def get_fileNameExt(filename):
    (fileDir, tempfilename) = os.path.split(filename)
    (shortname, extension) = os.path.splitext(tempfilename)
    return fileDir, shortname, extension


@print_excute_time
def handler(event, context):
    LOGGER.info(event)
    evt = json.loads(event)
    oss_bucket_name = evt["bucket_name"]
    object_key = evt["object_key"]
    output_dir = evt["output_dir"]
    tile = evt["tile"]
    ss = evt.get("start", 0)
    ss = str(ss)
    t = evt.get("duration")
    if t:
        t = str(t)

    itsoffset = evt.get("itsoffset", 0)
    itsoffset = str(itsoffset)
    scale = evt.get("scale", "-1:-1")
    interval = str(evt.get("interval", 1))
    padding = str(evt.get("padding", 0))
    color = str(evt.get("color", "black"))
    dst_type = str(evt.get("dst_type", "jpg"))

    creds = context.credentials
    auth = oss2.StsAuth(creds.accessKeyId,
                        creds.accessKeySecret, creds.securityToken)
    oss_client = oss2.Bucket(
        auth, 'oss-%s-internal.aliyuncs.com' % context.region, oss_bucket_name)

    input_path = oss_client.sign_url('GET', object_key, 3600)
    fileDir, shortname, extension = get_fileNameExt(object_key)

    cmd = ['ffmpeg', '-ss', ss, '-itsoffset', itsoffset, '-y', '-i', input_path,
           '-f', 'image2', '-vf', "fps=1/{0},scale={1},tile={2}:padding={3}:color={4}".format(
               interval, scale, tile, padding, color),
           '/tmp/{0}%d.{1}'.format(shortname, dst_type)]

    if t:
        cmd = ['ffmpeg', '-ss', ss, '-itsoffset', itsoffset, '-t', t, '-y', '-i', input_path,
               '-f', 'image2', '-vf', "fps=1/{0},scale={1},tile={2}:padding={3}:color={4}".format(
                   interval, scale, tile, padding, color),
               '/tmp/{0}%d.{1}'.format(shortname, dst_type)]

    LOGGER.info("cmd = {}".format(" ".join(cmd)))
    try:
        subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as exc:
        LOGGER.error('returncode:{}'.format(exc.returncode))
        LOGGER.error('cmd:{}'.format(exc.cmd))
        LOGGER.error('output:{}'.format(exc.output))
        LOGGER.error('stderr:{}'.format(exc.stderr))
        LOGGER.error('stdout:{}'.format(exc.stdout))

    for filename in os.listdir('/tmp/'):
        filepath = '/tmp/' + filename
        if filename.startswith(shortname):
            filekey = os.path.join(output_dir, fileDir, filename)
            oss_client.put_object_from_file(filekey, filepath)
            os.remove(filepath)
            LOGGER.info("Uploaded {} to {}".format(filepath, filekey))
    return "ok"
