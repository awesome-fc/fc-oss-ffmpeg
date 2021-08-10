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
    "vframes" : 20,
    "start": 0,
    "duration": 2
}
start 可选， 默认是为 0
vframes  和 duration 可选， 当同时填写的时候， 以 duration 为准
当都没有填写的时候， 默认整个视频转为gif
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
    vframes = evt.get("vframes")
    if vframes:
        vframes = str(vframes)
    ss = evt.get("start", 0)
    ss = str(ss)
    t = evt.get("duration")
    if t:
        t = str(t)
    creds = context.credentials
    auth = oss2.StsAuth(creds.accessKeyId,
                        creds.accessKeySecret, creds.securityToken)
    oss_client = oss2.Bucket(
        auth, 'oss-%s-internal.aliyuncs.com' % context.region, oss_bucket_name)

    input_path = oss_client.sign_url('GET', object_key, 3600)
    fileDir, shortname, extension = get_fileNameExt(object_key)
    gif_path = os.path.join("/tmp", shortname + ".gif")

    cmd = ["ffmpeg", "-y",  "-ss", ss, "-accurate_seek",
           "-i", input_path, "-pix_fmt", "rgb24", gif_path]
    if t:
        cmd = ["ffmpeg", "-y", "-ss", ss, "-t", t,  "-accurate_seek",
               "-i", input_path, "-pix_fmt", "rgb24", gif_path]
    else:
        if vframes:
            cmd = ["ffmpeg", "-y",  "-ss", ss,  "-accurate_seek", "-i",
                   input_path, "-vframes", vframes, "-y", "-f", "gif", gif_path]

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

    gif_key = os.path.join(output_dir, fileDir, shortname + ".gif")

    oss_client.put_object_from_file(gif_key, gif_path)

    LOGGER.info("Uploaded {} to {} ".format(
        gif_path, gif_key))

    os.remove(gif_path)

    return "ok"
