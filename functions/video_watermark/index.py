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
    "vf_args" : "drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:text='hello函数计算':x=100:y=50:fontsize=24:fontcolor=red:shadowy=2",
    "filter_complex_args": "overlay=0:0:1"
}

filter_complex_args 优先级 > vf_args

vf_args:
- 文字水印
vf_args = "drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:text='hello函数计算':x=50:y=50:fontsize=24:fontcolor=red:shadowy=1"
- 图片水印, 静态图片
vf_args = "movie=/code/logo.png[watermark];[in][watermark]overlay=10:10[out]"

filter_complex_args: 图片水印, 动态图片gif
filter_complex_args = "overlay=0:0:1"
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
    vf_args = evt.get("vf_args", "")
    filter_complex_args = evt.get("filter_complex_args")

    if not (vf_args or filter_complex_args):
        assert "at least one of 'vf_args' and 'filter_complex_args' has value"

    creds = context.credentials
    auth = oss2.StsAuth(creds.accessKeyId,
                        creds.accessKeySecret, creds.securityToken)
    oss_client = oss2.Bucket(
        auth, 'oss-%s-internal.aliyuncs.com' % context.region, oss_bucket_name)

    input_path = oss_client.sign_url('GET', object_key, 3600)
    fileDir, shortname, extension = get_fileNameExt(object_key)
    dst_video_path = os.path.join("/tmp", "watermark_" + shortname + extension)

    cmd = ["ffmpeg", "-y", "-i", input_path,
           "-vf", vf_args, dst_video_path]

    if filter_complex_args:  # gif
        cmd = ["ffmpeg", "-y", "-i", input_path, "-ignore_loop", "0",
               "-i", "/code/logo.gif", "-filter_complex", filter_complex_args, dst_video_path]

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

    video_key = os.path.join(output_dir, fileDir, shortname + extension)
    oss_client.put_object_from_file(video_key, dst_video_path)

    LOGGER.info("Uploaded {} to {} ".format(dst_video_path, video_key))

    os.remove(dst_video_path)

    return "ok"
