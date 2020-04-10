# -*- coding: utf-8 -*-
import subprocess
import oss2
import logging
import json
import os
import time
from urllib.parse import unquote

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
    "dst_type" : ".mov",
    "output_dir" : "output/"
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
    return shortname, extension

@print_excute_time
def handler(event, context):
    LOGGER.info(event)
    evt = json.loads(event)
    oss_bucket_name = evt["bucket_name"]
    object_key = evt["object_key"]
    dst_type = evt["dst_type"].strip()
    output_dir = evt["output_dir"]
    creds = context.credentials
    auth = oss2.StsAuth(creds.accessKeyId,
                        creds.accessKeySecret, creds.securityToken)
    oss_client = oss2.Bucket(
        auth, 'oss-%s-internal.aliyuncs.com' % context.region, oss_bucket_name)

    shortname, extension = get_fileNameExt(object_key)
    
    transcoded_filepath = os.path.join(
        "/tmp/", "transcoded_" + shortname + dst_type)
    
    input_path = oss_client.sign_url('GET', object_key, 3600)
    
    cmd = ["/code/ffmpeg", "-y", "-i", input_path,
           "-preset", "superfast", transcoded_filepath]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as exc:
        LOGGER.error('returncode:{}'.format(exc.returncode))
        LOGGER.error('cmd:{}'.format(exc.cmd))
        LOGGER.error('output:{}'.format(exc.output))
        LOGGER.error('detail:{}'.format(
            result.stderr.decode()))
    
    transcoded_key = os.path.join(
        output_dir, "transcoded_" + shortname + dst_type)
    
    oss_client.put_object_from_file(transcoded_key, transcoded_filepath)
    
    LOGGER.info("Uploaded {} to {} ".format(
        transcoded_filepath, transcoded_key))

    return "ok"
