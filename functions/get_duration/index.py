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
2. service's role has OSSReadAccess
3. event format
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4"
}
'''

FFPROBE_BUKCET_NAME = os.environ["FFPROBE_BUKCET_NAME"]
FFPROBE_BIN_KEY = os.environ["FFPROBE_BIN_KEY"]

# a decorator for print the excute time of a function
def print_excute_time(func):
    def wrapper(*args, **kwargs):
        local_time = time.time()
        ret = func(*args, **kwargs)
        LOGGER.info('current Function [%s] excute time is %.2f seconds' %
                    (func.__name__, time.time() - local_time))
        return ret
    return wrapper

@print_excute_time
def initializer(context):
    if not os.path.exists('/tmp/ffprobe'):
        creds = context.credentials
        auth = oss2.StsAuth(creds.accessKeyId,
                            creds.accessKeySecret, creds.securityToken)
        oss_client = oss2.Bucket(
            auth, 'oss-%s-internal.aliyuncs.com' % context.region, FFPROBE_BUKCET_NAME)
        oss_client.get_object_to_file(FFPROBE_BIN_KEY, '/tmp/ffprobe')
        os.system("chmod 777 /tmp/ffprobe")
    return "succ"


@print_excute_time
def handler(event, context):
    evt = json.loads(event)
    oss_bucket_name = evt["bucket_name"]
    object_key = evt["object_key"]
    creds = context.credentials
    auth = oss2.StsAuth(creds.accessKeyId,
                        creds.accessKeySecret, creds.securityToken)
    oss_client = oss2.Bucket(
        auth, 'oss-%s-internal.aliyuncs.com' % context.region, oss_bucket_name)

    object_url = oss_client.sign_url('GET', object_key, 15 * 60)

    cmd = '/tmp/ffprobe -show_entries format=duration -v quiet -of csv="p=0" -i {0}'.format(
        object_url)
    raw_result = subprocess.check_output(cmd, shell=True)
    result = raw_result.decode().replace("\n", "").strip()
    duration = float(result)
    return duration