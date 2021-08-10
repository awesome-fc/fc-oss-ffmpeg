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

    cmd = ["ffprobe",  "-show_entries", "format=duration",
           "-v", "quiet", "-of", "csv", "-i",  object_url]
    raw_result = subprocess.check_output(cmd)
    result = raw_result.decode().replace("\n", "").strip().split(",")[1]
    duration = float(result)
    return duration
