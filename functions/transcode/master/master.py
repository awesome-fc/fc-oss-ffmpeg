# -*- coding: utf-8 -*-
import subprocess
import oss2
import logging
import json
import os
import time
from urllib.parse import unquote
import fc2
from threading import Thread

logging.getLogger("oss2.api").setLevel(logging.ERROR)
logging.getLogger("oss2.auth").setLevel(logging.ERROR)

LOGGER = logging.getLogger()

'''
1. function and bucket locate in same region
2. service's role has OSSFullAccess and FCInvokeAccess
3. event format
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4",
    "dst_type" : ".mov",
    "segment_time_seconds": 20,
    "output_dir" : "output/"
}

- dst_type: 转码后的目标格式

- segment_time_seconds: 切片的分段时间

- output_dir: 转码后视频在 OSS bucket 中的前缀

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


def sub_transcode(fcClient, subEvent):
    service_name = subEvent.pop('service_name')
    function_name = subEvent.pop('function_name')
    ret = fcClient.invoke_function(
        service_name, function_name, json.dumps(subEvent))
    if ret != "ok":
        assert "sub_transcode fail, event = {}; error = {}".format(
            json.dumps(subEvent),  ret)
    else:
        return "ok"


@print_excute_time
def handler(event, context):
    start = time.time()
    evt = json.loads(event)
    oss_bucket_name = evt["bucket_name"]
    object_key = evt["object_key"]
    dst_type = evt["dst_type"].strip()
    output_dir = evt["output_dir"]
    segment_time_seconds = str(evt.get("segment_time_seconds", 20))

    creds = context.credentials
    auth = oss2.StsAuth(creds.accessKeyId,
                        creds.accessKeySecret, creds.securityToken)
    oss_client = oss2.Bucket(
        auth, 'oss-%s-internal.aliyuncs.com' % context.region, oss_bucket_name)

    shortname, extension = get_fileNameExt(object_key)

    input_path = oss_client.sign_url('GET', object_key, 3600)

    # split video to pieces
    split_cmd = ["/code/ffmpeg", "-y",  "-i",  input_path, "-c", "copy", "-f", "segment", "-segment_time", segment_time_seconds, "-reset_timestamps", "1",
                 "/tmp/split_" + shortname + '_piece_%02d' + extension]
    try:
        subprocess.run(
            split_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as exc:
        LOGGER.error(
            'split video to pieces returncode:{}'.format(exc.returncode))
        LOGGER.error('split video to pieces cmd:{}'.format(exc.cmd))
        LOGGER.error('split video to pieces output:{}'.format(exc.output))
        LOGGER.error('split video to pieces stderr:{}'.format(exc.stderr))
        LOGGER.error('split video to pieces stdout:{}'.format(exc.stdout))

    split_keys = []
    for filename in os.listdir('/tmp/'):
        filepath = '/tmp/' + filename
        if filename.startswith('split_' + shortname):
            filekey = os.path.join(output_dir, context.request_id, filename)
            oss_client.put_object_from_file(filekey, filepath)
            os.remove(filepath)
            split_keys.append(filekey)
            LOGGER.info("Uploaded {} to {}".format(filepath, filekey))

    LOGGER.info("split spend time = {}".format(time.time() - start))
    start = time.time()

    # call worker parallel to transcode
    endpoint = "http://{}.{}-internal.fc.aliyuncs.com".format(
        context.account_id, context.region)
    fcClient = fc2.Client(endpoint=endpoint, accessKeyID=creds.accessKeyId,
                          accessKeySecret=creds.accessKeySecret, securityToken=creds.securityToken, Timeout=600)

    LOGGER.info("split_keys = {}".format(json.dumps(split_keys)))

    sub_service_name = context.service.name
    sub_function_name = 'transcode-worker'

    LOGGER.info("worker function name = {}".format(sub_function_name))

    ts = []
    for obj_key in split_keys:
        subEvent = {
            "bucket_name": oss_bucket_name,
            "object_key": obj_key,
            "dst_type": dst_type,
            "output_dir": os.path.join(output_dir, context.request_id),
            "service_name": sub_service_name,
            "function_name": sub_function_name
        }
        LOGGER.info(json.dumps(subEvent))
        t = Thread(target=sub_transcode, args=(fcClient, subEvent,))
        t.start()
        ts.append(t)

    for t in ts:
        t.join()

    LOGGER.info("transcode spend time = {}".format(time.time() - start))
    start = time.time()

    # merge split pieces which is transcoded
    segs_filename = "segs_{}.txt".format(shortname)
    segs_filepath = os.path.join('/tmp/', segs_filename)
    if os.path.exists(segs_filepath):
        os.remove(segs_filepath)

    output_prefix = os.path.join(output_dir, context.request_id)
    prefix = os.path.join(output_prefix, 'transcoded_split_' + shortname)
    LOGGER.info("output prefix " + prefix)
    split_files = []
    with open(segs_filepath, "a") as f:
        for obj in oss2.ObjectIterator(oss_client, prefix=prefix):
            if obj.key.endswith(dst_type):
                filename = obj.key.replace("/", "_")
                filepath = "/tmp/" + filename
                split_files.append(filepath)
                oss_client.get_object_to_file(obj.key, filepath)
                f.write("file '%s'\n" % filepath)

    # debug
    with open(segs_filepath, "r") as f:
        LOGGER.info("segs_file content = {}".format(json.dumps(f.read())))

    merged_filename = "merged_" + shortname + dst_type
    merged_filepath = os.path.join("/tmp/", merged_filename)
    
    merge_cmd = ["/code/ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
                 segs_filepath, "-c", "copy", "-fflags", "+genpts", merged_filepath]
    try:
        subprocess.run(
            merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as exc:
        LOGGER.error('merge split pieces returncode:{}'.format(exc.returncode))
        LOGGER.error('merge split pieces cmd:{}'.format(exc.cmd))
        LOGGER.error('merge split pieces output:{}'.format(exc.output))
        LOGGER.error('merge split pieces stderr:{}'.format(exc.stderr))
        LOGGER.error('merge split pieces stdout:{}'.format(exc.stdout))

    merged_key = os.path.join(output_prefix, merged_filename)
    oss_client.put_object_from_file(merged_key, merged_filepath)
    LOGGER.info("Uploaded {} to {}".format(merged_filepath, merged_key))

    LOGGER.info("merge spend time = {}".format(time.time() - start))

    os.remove(segs_filepath)
    for fp in split_files:
        os.remove(fp)

    # clear all split_video and transcoded split_video on oss
    # todo ...

    return "ok"
