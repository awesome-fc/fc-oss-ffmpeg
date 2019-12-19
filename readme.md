## 应用简介

- [函数计算 FC](https://help.aliyun.com/product/50980.html)：阿里云函数计算是事件驱动的全托管计算服务。通过函数计算，您无需管理服务器等基础设施，只需编写代码并上传。函数计算会为您准备好计算资源，以弹性、可靠的方式运行您的代码，并提供日志查询、性能监控、报警等功能。

- [对象存储 OSS](https://help.aliyun.com/document_detail/31817.html)：阿里云提供的海量、安全、低成本、高可靠的云存储服务

本应用实现的是: 基于函数计算 FC + FFmpeg 实现 Serverless 架构的弹性高可用的高度自定义音视频处理主题

#### 1. [get_media_meta: 获取音视频 meta](#get_media_meta)
#### 2. [get_duration: 获取音视频时长](#get_duration)
#### 3. [transcode: 功能强大的并行视频转码器](#transcode)
#### 4. [get_sprites: 功能强大雪碧图制作函数](#get_sprites)
#### 5. [video_watermark: 功能强大的视频添加水印功能](#video_watermark)
#### 6. [video_gif: 功能强大的 video 提取为 gif 函数](#video_gif)
#### 7. [audio_convert: 音频格式转换器](#audio_convert)

本项目中只是展现了这 7 个示例， FC + FFmpeg 可以实现对 oss 上的音视频进行任意的自定义处理， 欢迎大家提 issue 完善示例。

## 示例效果显示
<img src="fc-oss-ffmpeg.gif?raw=true">

## 方案优势

### 成本比较

实验对象：

- 视频是 89s 的 mov 标清短视频: [480P.mov](https://fc-hz-demo.oss-cn-hangzhou.aliyuncs.com/fnf_video/inputs/480P.mov)

- 音频为 89s 的 mp3 音频: [480P.mp3](https://fc-hz-demo.oss-cn-hangzhou.aliyuncs.com/fnf_video/inputs/480P.mp3)

|  函数   | 内存规格  | 执行时间 | 一次计费(元) | 备注 |
|  ----  | ----  |  ----  |  ----  | ---- |
| get_media_meta  | 128M | <100ms  | 0.0000013885 |  |
| get_duration  | 128M | <200ms  |  0.000002777 |  |
| audio_convert  | 128M | <400ms  | 0.000005554 | mp3 转 wav |
| get_sprites  | 256M | <3200ms  | 0.000088864 | 每10秒截图一次， 生成 3*3 的雪碧图 |
| video_gif  | 128M |  <1000ms | 0.000013885 | 截取30-32秒的视频生成 GIF |
| video_watermark  | 256M | <4100ms  | 0.000113857 | png水印 |

函数计算每月有很大的免费额度：

- 调用次数：每月前 100 万次函数调用免费。

- 执行时间：每月前 400000(GB*秒) 费用免费。

详情：[函数计算计费](https://help.aliyun.com/document_detail/137980.html)

### 转码

#### 性能

实验视频为是 89s 的 mov 文件 4K 视频: [4K.mov](https://fc-hz-demo.oss-cn-hangzhou.aliyuncs.com/fnf_video/inputs/4K.mov)，云服务进行 mov -> mp4 普通转码需要消耗的时间为 188s， 将这个参考时间记为 T

|  视频切片时间   | FC转码耗时 | 性能加速百分比 |
|  ----  | ----  | ----  |
|  45s |  160s |  117.5% |
|  25s |  100s  |  188% |
|  15s |  70s |  268.6% |
|  10s |  45s |  417.8% |
|  5s  |  35s  |  537.1% |

> 性能加速百分比 = T / FC转码耗时

从上表可以看出，设置的视频切片时间越短， 视频转码时间越短， 函数计算可以自动瞬时调度出更多的计算资源来一起完成这个视频的转码, 转码性能优异。

#### 成本
实验视频为是 89s 的 mov 文件短视频， 测试视频地址：
[480P.mov](https://fc-hz-demo.oss-cn-hangzhou.aliyuncs.com/fnf_video/inputs/480P.mov) [720P.mov](https://fc-hz-demo.oss-cn-hangzhou.aliyuncs.com/fnf_video/inputs/720P.mov)  [1080P.mov](https://fc-hz-demo.oss-cn-hangzhou.aliyuncs.com/fnf_video/inputs/1080P.mov)  [4K.mov](https://fc-hz-demo.oss-cn-hangzhou.aliyuncs.com/fnf_video/inputs/4K.mov)

> 测试命令: `ffmpeg -i test.mov -preset superfast test.mp4`， 函数内存规格设置为 3G
	
**格式转换**


| 分辨率 | bitrate |  帧率 | FC 转码耗费时间 | FC 转码费用 | 腾#云视频处理费用 | 成本下降百分比 |
| ------ | ------ | ------ | ------ | ------ | ------ | ------ |
| 标清 640*480   |  618 kb/s | 24 | 11s | 0.00366564 | 0.032 | 88.5% |
| 高清 1280*720  |  1120 kb/s | 24 | 31s | 0.01033044 |0.065 | 84.1% |
| 超清 1920*1080 |  1942 kb/s |  24 | 66s | 0.02199384 | 0.126 | 82.5% |
| 4K  3840*2160 |  5250 kb/s| 24 | 260s | 0.0866424 | 0.556 | 84.4% |

	
> 成本下降百分比 = （腾#云视频处理费用 - FC 转码费用）/ 腾#云视频处理费用
	
> [腾#云视频处理](https://cloud.tencent.com/document/product/862/36180)，计费使用普通转码，转码时长不足一分钟，按照一分钟计算，这里计费采用的是 2 min，即使采用 1.5 min 计算， 成本下降百分比也在 80% 左右。

## 部署

### 准备工作

免费开通[函数计算](https://statistics.functioncompute.com/?title=FcOssFFmpeg&theme=ServerlessVideo&author=rsong&src=article&url=http://fc.console.aliyun.com) 和[对象存储](https://oss.console.aliyun.com/)

### 安装 Fun 工具

-	安装版本为8.x 最新版或者10.x 、12.x [nodejs](https://nodejs.org/en/download/package-manager/#debian-and-ubuntu-based-linux-distributions-enterprise-linux-fedora-and-snap-packages)

-	安装 [funcraf](https://github.com/alibaba/funcraft/blob/master/docs/usage/installation-zh.md)

	```
	$ npm install @alicloud/fun -g
	```

- 安装完成后， 执行 `fun config`，按照提示完成 fun 的配置，参考：[getting_started](https://github.com/alibaba/funcraft/blob/master/docs/usage/getting_started-zh.md)

### Clone 工程，在工程目录上，命令行输入 `fun deploy` 执行

```
$ git clone https://github.com/awesome-fc/fc-oss-ffmpeg.git
$ cd fc-oss-ffmpeg
$ fun deploy
```

<a name="get_media_meta"></a>
## get_media_meta 获取音视频 meta
函数 get_get_media_meta 以 json 格式返回音视频的完整 meta 信息, 音视频大小不限

**event format:**

``` json
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4"
}
```

**response:**

```json
{
   "format": {
      "bit_rate": "488281",
      "duration": "179.955000",
      "filename": "http://fc-hz-demo.oss-cn-hangzhou-internal.aliyuncs.com/fnf_video%2Finputs%2Fb.mov",
      "format_long_name": "QuickTime / MOV",
      "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
      ...
   },
   "streams": []
   ...
}
```

**python sdk 调用函数示例:**

```python
# -*- coding: utf-8 -*-
import fc2
import json

client = fc2.Client(endpoint="http://1123456.cn-hangzhou.fc.aliyuncs.com",accessKeyID="xxxxxxxx",accessKeySecret="yyyyyy")

resp = client.invoke_function("FcOssFFmpeg", "get_media_meta", payload=json.dumps(
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4"
})).data

print(resp)

```

<a name="get_duration"></a>
## get_duration 获取音视频时长
音视频大小不限, 相对于 get_media_meta 这个函数更加简化，单纯返回音视频的时间长度

**event format:**

``` json
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4"
}
```

**response:**

`20.45`

**python sdk 调用函数示例:**

```python
# -*- coding: utf-8 -*-
import fc2
import json

client = fc2.Client(endpoint="http://1123456.cn-hangzhou.fc.aliyuncs.com",accessKeyID="xxxxxxxx",accessKeySecret="yyyyyy")

resp = client.invoke_function("FcOssFFmpeg", "get_duration", payload=json.dumps(
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4"
})).data

print(resp)

```


<a name="transcode"></a>
## transcode 功能强大的并行视频转码器

<img src="transcode.png?raw=true">

如上图所示， 利用函数计算的毫秒级动态扩容 + 分治思想实现快速转码， 通过设置合理的分片时间， 达到加快转码的目的。

**event format:**

``` json
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4",
    "dst_type" : ".mov",
    "segment_time_seconds": 20,
    "output_dir" : "output/"
}
```

- dst_type: 转码后的目标格式
- segment_time_seconds: 切片的分段时间
- output_dir: 转码后视频在 OSS bucket 中的前缀

**response:**

`ok`

转码后的视频会保存在 OSS 的这个 output_dir 目录中

**python sdk 调用函数示例:**

```python
# -*- coding: utf-8 -*-
import fc2
import json

client = fc2.Client(endpoint="http://1123456.cn-hangzhou.fc.aliyuncs.com",accessKeyID="xxxxxxxx",accessKeySecret="yyyyyy")

resp = client.invoke_function("FcOssFFmpeg", "transcode", payload=json.dumps(
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4",
    "dst_type" : ".mov",
    "segment_time_seconds": 20,
    "output_dir" : "output/"
})).data

print(resp)

```

**更高自定义需求**

- 打破 /tmp 有 512M 限制

- 更加复杂的视频处理流程， 比如多种格式多种分辨率转码同时进行， 并进行 CDN 预热等各种自定义操作

推荐配合使用[函数工作流](https://help.aliyun.com/product/113549.html)实现功能更加完善视频处理方案: [fc-fnf-video-processing](https://github.com/awesome-fc/fc-fnf-video-processing/tree/master/video-processing)


<a name="get_sprites"></a>
## get_sprites 功能强大雪碧图制作函数

**event format:**

``` json
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4",
    "output_dir" : "output/",
    "tile": "3*4",
    "start": 0,
    "duration": 2,
    "itsoffset": 0,
    "scale": "-1:-1",
    "interval": 5,
    "padding": 1,
    "color": "black",
    "dst_type": "png"
}
```

- tile: 必填， 雪碧图的 rows * cols
- start: 可选， 默认是为 0
- duration: 可选，表示基于 start 之后的多长时间的视频内进行截图，

	> 比如 start 为 10， duration 为 20，表示基于视频的10s-30s内进行截图

- interval: 可选，每隔多少秒截图一次， 默认为 1
- scale: 可选，截图的大小, 默认为 -1:-1， 默认为原视频大小, 320:240, iw/2:ih/2 
- itsoffset: 可选，默认为 0, delay多少秒，配合start、interval使用

	- 假设 start 为 0， interval 为 10，itsoffset 为 0， 那么截图的秒数为 5， 15， 25 ...
	
	- 假设 start 为 0， interval 为 10，itsoffset 为 1， 那么截图的秒数为 4， 14， 24 ...
	
	- 假设 start 为 0， interval 为 10，itsoffset 为 4.999(不要写成5，不然会丢失0秒的那一帧图)， 那么截图的秒数为 0， 10， 20 ...
	
	- 假设 start 为 0， interval 为 10，itsoffset 为 -1， 那么截图的秒数为 6， 16，26 ...

- padding: 可选，图片之间的间隔, 默认为 0
- color: 可选，雪碧图背景颜色，默认黑色， https://ffmpeg.org/ffmpeg-utils.html#color-syntax
- dst_type: 可选，生成的雪碧图图片格式，默认为 png，主要为 png 或者 jpg，[image2](https://ffmpeg.org/ffmpeg-all.html#image2-1)

**response:**

`ok`

生成1张或者多张雪碧图保存到 bucket 的该目录( `output_dir + "/" + dir(object_key)`  )中，假设截图的数量小于等于  tile 指定的 rows * cols， 生成一张雪碧图， 否则生成多张雪碧图

**python sdk 调用函数示例:**

```python
# -*- coding: utf-8 -*-
import fc2
import json

client = fc2.Client(endpoint="http://1123456.cn-hangzhou.fc.aliyuncs.com",accessKeyID="xxxxxxxx",accessKeySecret="yyyyyy")

resp = client.invoke_function("FcOssFFmpeg", "get_sprites", payload=json.dumps(
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4",
    "output_dir" : "output/"
})).data

print(resp)

```

<a name="video_watermark"></a>
## video_watermark 功能强大的视频添加水印功能

实现对视频添加 文字水印、 静态图片水印和动态 gif 水印

**event format:**

``` json
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4",
    "output_dir" : "output/",
    "vf_args" : "drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:text='hello函数计算':x=100:y=50:fontsize=24:fontcolor=red",
    "filter_complex_args": "overlay=0:0:1"
}
```

其中优先级: filter_complex_args > vf_args，即有 filter_complex_args 参数的时候，忽视 vf_args 参数

**vf_args:**

- 文字水印

	vf_args = "drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:text='hello函数计算':x=50:y=50:fontsize=24:fontcolor=red:shadowy=1"

- 图片水印, 静态图片

	vf_args = "movie=/code/logo.png[watermark];[in][watermark]overlay=10:10[out]"

**filter_complex_args:**

- 图片水印, 动态图片gif

	filter_complex_args = "overlay=0:0:1"

**response:**

`ok`

生成具有水印的视频，保存到 bucket 的该目录( `output_dir + "/" + dir(object_key)`  )中

**python sdk 调用函数示例:**

```python
# -*- coding: utf-8 -*-
import fc2
import json

client = fc2.Client(endpoint="http://1123456.cn-hangzhou.fc.aliyuncs.com",accessKeyID="xxxxxxxx",accessKeySecret="yyyyyy")

resp = client.invoke_function("FcOssFFmpeg", "video_watermark", payload=json.dumps(
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4",
     "output_dir" : "output/",
    "vf_args" : "drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:text='hello函数计算':x=100:y=50:fontsize=24:fontcolor=red"
})).data

print(resp)

```

<a name="video_gif"></a>
## video_gif 功能强大的 video 提取为 gif 函数

- video 转为 gif

- 支持某段时间内视频转为 gif

- 支持从某段时间开始后的指定帧数转为 gif


**event format:**

``` json
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4",
    "output_dir" : "output/",
    "vframes" : 20,
    "start": 0,
    "duration": 2,
}
```

- start 可选， 默认是为 0

- vframes  和 duration 可选， 当同时填写的时候， 以 duration 为准，当都没有填写的时候， 默认整个视频转为gif

**response:**

`ok`

生成 gif 图片，保存到 bucket 的该目录( `output_dir + "/" + dir(object_key)`  )中

**python sdk 调用函数示例:**

```python
# -*- coding: utf-8 -*-
import fc2
import json

client = fc2.Client(endpoint="http://1123456.cn-hangzhou.fc.aliyuncs.com",accessKeyID="xxxxxxxx",accessKeySecret="yyyyyy")

resp = client.invoke_function("FcOssFFmpeg", "video_gif", payload=json.dumps(
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp4",
    "output_dir" : "output/",
})).data

print(resp)

```

<a name="audio_convert"></a>
## audio_convert: 音频格式转换器

**event format:**

``` json
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp3",
    "output_dir" : "output/",
    "dst_type": ".wav",
    "ac": 1,
    "ar": 4000
}
```

- ac 可选，声道数

- ar 可选，采样率

**response:**

`ok`

生成目标格式的音频文件，保存到 bucket 的该目录( `output_dir + "/" + dir(object_key)`  )中

**python sdk 调用函数示例:**

```python
# -*- coding: utf-8 -*-
import fc2
import json

client = fc2.Client(endpoint="http://1123456.cn-hangzhou.fc.aliyuncs.com",accessKeyID="xxxxxxxx",accessKeySecret="yyyyyy")

resp = client.invoke_function("FcOssFFmpeg", "audio_convert", payload=json.dumps(
{
    "bucket_name" : "test-bucket",
    "object_key" : "a.mp3",
    "output_dir" : "output/",
    "dst_type": ".wav",
    "ac": 1,
    "ar": 8000,
})).data

print(resp)

```