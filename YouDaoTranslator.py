# -*- coding: utf-8 -*-
#
#
# 非实时转写调用demo

import hashlib
import json
import os
import time
import uuid

import requests

asr_host = 'https://openapi.youdao.com/api/audio'

# 请求的接口名
api_prepare = '/prepare'
api_upload = '/upload'
api_merge = '/merge'
api_get_progress = '/get_progress'
api_get_result = '/get_result'
# 文件分片大小10M
file_piece_sice = 10485760

class RequestApi(object):
    def __init__(self, app_key, app_secret, upload_file_path, lang):
        self.app_key = app_key
        self.app_secret = app_secret
        self.upload_file_path = upload_file_path
        self.lang = lang

    def encrypt(signStr):
        hash = hashlib.sha256()
        hash.update(signStr.encode('utf-8'))
        return hash.hexdigest()

    def gene_params(self, apiname, taskid=None, slice_id=None):
        app_key = self.app_key
        app_secret = self.app_secret
        upload_file_path = self.upload_file_path
        nonce = str(uuid.uuid1())
        curtime = str(int(time.time()))
        signStr = app_key + nonce + curtime + app_secret
        hash = hashlib.sha256()
        hash.update(signStr.encode('utf-8'))
        sign = hash.hexdigest()
        file_len = os.path.getsize(upload_file_path)
        file_name = os.path.basename(upload_file_path)
        format = os.path.splitext(upload_file_path)[-1][1:]
        print(file_name)

        param_dict = {}

        if apiname == api_prepare:
            # slice_num是指分片数量，如果您使用的音频都是较短音频也可以不分片，直接将slice_num指定为1即可
            slice_num = int(file_len / file_piece_sice) + (0 if (file_len % file_piece_sice == 0) else 1)
            param_dict['appKey'] = app_key
            param_dict['sign'] = sign
            param_dict['curtime'] = curtime
            param_dict['salt'] = nonce
            param_dict['signType'] = "v4"
            param_dict['langType'] = self.lang
            param_dict['fileSize'] = str(file_len)
            param_dict['name'] = file_name
            param_dict['format'] = format
            param_dict['sliceNum'] = str(slice_num)
        elif apiname == api_upload:
            param_dict['appKey'] = app_key
            param_dict['sign'] = sign
            param_dict['curtime'] = curtime
            param_dict['salt'] = nonce
            param_dict['signType'] = "v4"
            param_dict['q'] = taskid
            param_dict['sliceId'] = slice_id
        elif apiname == api_merge:
            param_dict['appKey'] = app_key
            param_dict['sign'] = sign
            param_dict['curtime'] = curtime
            param_dict['salt'] = nonce
            param_dict['signType'] = "v4"
            param_dict['q'] = taskid
        elif apiname == api_get_progress or apiname == api_get_result:
            param_dict['appKey'] = app_key
            param_dict['sign'] = sign
            param_dict['curtime'] = curtime
            param_dict['salt'] = nonce
            param_dict['signType'] = "v4"
            param_dict['q'] = taskid
        return param_dict

    def gene_request(self, apiname, data, files=None, headers=None):
        response = requests.post(asr_host + apiname, data=data, files=files, headers=headers)
        result = json.loads(response.text)
        if result["errorCode"] == "0":
            print("{} success:".format(apiname))
            return result
        else:
            print("{} error:".format(apiname))
            exit(0)
            return result

    # 预处理
    def prepare_request(self):
        return self.gene_request(apiname=api_prepare,
                                 data=self.gene_params(api_prepare))

    # 上传
    def upload_request(self, taskid, upload_file_path):
        file_object = open(upload_file_path, 'rb')
        try:
            index = 1
            while True:
                content = file_object.read(file_piece_sice)
                if not content or len(content) == 0:
                    break
                files = {
                    "file": content
                }
                response = self.gene_request(api_upload,
                                             data=self.gene_params(api_upload, taskid=taskid,
                                                                   slice_id=index),
                                             files=files)
                if response.get('errorCode') != "0":
                    # 上传分片失败
                    print('upload slice fail, response: ' + str(response))
                    return False
                print('upload slice ' + str(index) + ' success')
                index += 1
        finally:
            'file index:' + str(file_object.tell())
            file_object.close()
        return True

    # 合并
    def merge_request(self, taskid):
        return self.gene_request(api_merge, data=self.gene_params(api_merge, taskid=taskid))

    # 获取进度
    def get_progress_request(self, taskid):
        return self.gene_request(api_get_progress, data=self.gene_params(api_get_progress, taskid=taskid))

    # 获取结果
    def get_result_request(self, taskid):
        return self.gene_request(api_get_result, data=self.gene_params(api_get_result, taskid=taskid))

    def all_api_request(self):
        # 1. 预处理
        pre_result = self.prepare_request()
        taskid = pre_result["result"]
        print(taskid)
        # 2 . 分片上传
        self.upload_request(taskid=taskid, upload_file_path=self.upload_file_path)
        # 3 . 文件合并
        self.merge_request(taskid=taskid)
        # 4 . 获取任务进度
        while True:
            # 每隔20秒获取一次任务进度
            progress = self.get_progress_request(taskid)
            progress_dic = progress
            if progress_dic['errorCode'] != "0":
                print('task error: ' + progress_dic['failed'])
                return
            else:
                result = progress_dic['result']
                print(result[0])
                if result[0]['status'] == '9':
                    print('task ' + taskid + ' finished')
                    break
                print('The task ' + taskid + ' is in processing, task status: ' + str(result))

            # 每次获取进度间隔20S
            time.sleep(20)
        # 5 . 获取结果
        result = self.get_result_request(taskid=taskid)
        return result

def GenWAVFile(input_name, output_name):
    #cmd_line = "ffmpeg -y -ss 00:00:00 -t 01:00:00 -i \"" + input_name + "\" -ac 1 -ar 16000 -async 1 \"" + output_name + "\""
    cmd_line = "ffmpeg -y  -i \"" + input_name + "\" -ac 1 -ar 16000 -async 1 \"" + output_name + "\""
    rv = os.system(cmd_line)

def GenTimeByMillisecons(ms):
    hour = ms / (1000 * 60 * 60)
    ms = ms % (1000 * 60 * 60)
    minute = ms / (1000 * 60)
    ms = ms % (1000 * 60)
    second = ms / 1000
    millisecond = ms % 1000
    return hour,minute,second,millisecond


def ClipWord(words):
    result = []
    word_len = len(words)
    line_len = 50
    start_index = 0
    while start_index < word_len:
        end_index = start_index + line_len
        if end_index >= word_len:
            result.append(words[start_index:word_len])
            break
        one_line = words[start_index:end_index]
        last_index = one_line.rfind(' ')
        if last_index != -1:
            end_index = start_index + last_index
        one_line = words[start_index:end_index]
        start_index = start_index + len(one_line)
        result.append(one_line)
    return result

def SaveSrt(filename, result_time, result_time_end, result_word):
    file = open(filename,'w')
    index = 1
    num = len(result_time)
    for i in range(0, num):
        file.write('%d'%(i+1))
        file.write('\n')
        sh,sm,ss,sms = GenTimeByMillisecons(result_time[i])
        eh,em,es,ems = GenTimeByMillisecons(result_time_end[i])
        file.write('%d:%d:%d,%d --> %d:%d:%d,%d'%(sh,sm,ss,sms,eh,em,es,ems))
        file.write('\n')
        #print(len(result_word[i]))
        clip_words = ClipWord(result_word[i])
        for word in clip_words:
            file.write(word)
            file.write('\n')
    file.close()

def GenSrtFile(file_name, result, success_file, fail_file):
    if result['errorCode'] != '0':
        print("Failed", file_name)
        fail_file.append(file_name)
        return None
    else:
        print("Success", file_name)
        success_file.append(file_name)
        sentences = result['result']
        time_begin = []
        time_end = []
        words = []
        for one_record in sentences:
            sentence = one_record['sentence']
            if len(sentence) > 0:
                tb_list = one_record['word_timestamps']
                te_list = one_record['word_timestamps_eds']
                tb = tb_list[0]
                te = te_list[len(te_list) - 1]
                words.append(sentence)
                time_begin.append(tb)
                time_end.append(te)
        SaveSrt(file_name, time_begin, time_end, words)

# 注意：如果出现requests模块报错："NoneType" object has no attribute 'read', 请尝试将requests模块更新到2.20.0或以上版本(本demo测试版本为2.20.0)
# 输入有道智云开放平台的应用Id（appKey），密钥和待转写的文件路径
app_key = 自己申请的key
app_secret = 自己申请的密钥

def getAllMp4Name(path):
    path_collection = set()
    for dirpath, dirnames, filenames in os.walk(path):
        for file in filenames:
            if file.endswith('.mp4'):
                fullpath = os.path.join(dirpath, file)
                path_collection.add(fullpath)
    return path_collection

def GenSrtForMp4(file_name, success_file, fail_file):
    wav_file_name = 'temp.wav'
    srt_file_name = file_name + '.srt'
    result_txt_file = file_name + '.txt'
    if(os.path.exists(srt_file_name)):
        print("FileExist：",srt_file_name)
        success_file.append(srt_file_name)
        return
    print("1.GenWAVFile")
    GenWAVFile(file_name, wav_file_name)
    print("2.Recognition")
    api = RequestApi(app_key= app_key, app_secret=app_secret, upload_file_path=wav_file_name, lang="en")
    result = api.all_api_request()
    print("3.GenSrtFile")
    GenSrtFile(srt_file_name, result, success_file, fail_file)
    txt_file = open(result_txt_file,'w')
    txt_file.write(str(result))
    txt_file.close()

def GenSrtInFolder(folder_name):
    video_files = getAllMp4Name("..\\video")
    success_file = []
    fail_file = []
    for file in video_files:
        GenSrtForMp4(file, success_file, fail_file)
    print("success:",len(success_file))
    for file in success_file:
        print(file)
    print("fail:",len(fail_file))
    for file in fail_file:
        print(file)
    return success_file, fail_file

def GenSrtOneFile(file_name):
    success_file = []
    fail_file = []
    GenSrtForMp4(file_name, success_file, fail_file)

if __name__ == '__main__':
    #success_file, fail_file = GenSrtInFolder("..\\video")
    #迟迟没有结果,原因看着是因为超过一个小时了
    #GenSrtOneFile("..\\video\\GDC Vault - GDC Pitch Presents How to pitch your GAME to publishers.mp4")
    GenSrtOneFile("3.mp4")
    #时间对不上，生成wav的时候长短和视频不匹配
    #GenSrtOneFile("..\\video\\GDC Vault - Tools Summit The Rust Programming Language for Game Tooling.mp4")


