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
    "object_key" : "a.mp3",
    "output_dir" : "output/",
    "dst_type": ".wav",
    "ac": 1,
    "ar": 4000
}
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
    dst_type = evt["dst_type"]
    ac = evt.get("ac")
    ar = evt.get("ar")

    creds = context.credentials
    auth = oss2.StsAuth(creds.accessKeyId,
                        creds.accessKeySecret, creds.securityToken)
    oss_client = oss2.Bucket(
        auth, 'oss-%s-internal.aliyuncs.com' % context.region, oss_bucket_name)

    input_path = oss_client.sign_url('GET', object_key, 3600)
    fileDir, shortname, extension = get_fileNameExt(object_key)

    cmd = ['ffmpeg', '-i', input_path,
           '/tmp/{0}{1}'.format(shortname, dst_type)]
    if ac:
        if ar:
            cmd = ['ffmpeg', '-i', input_path, "-ac",
                   str(ac), "-ar", str(ar),  '/tmp/{0}{1}'.format(shortname, dst_type)]
        else:
            cmd = ['ffmpeg', '-i', input_path, "-ac",
                   str(ac), '/tmp/{0}{1}'.format(shortname, dst_type)]
    else:
        if ar:
            cmd = ['ffmpeg', '-i', input_path, "-ar",
                   str(ar),  '/tmp/{0}{1}'.format(shortname, dst_type)]

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
