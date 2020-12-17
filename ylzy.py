# -*- coding: utf-8 -*-
import sys
#reload(sys)
#sys.setdefaultencoding("utf-8")

from flask import Flask, request
from flask_socketio import SocketIO, emit, disconnect

import numpy as np

import queue
from google.cloud import speech
import google
from functools import partial

LOG = {"screen":False, "file":True, "file_path":"./log.txt"}

app = Flask(__name__, template_folder='./')
app.config['SECRET_KEY'] = 'secret!'

socketio = SocketIO(app, cors_allowed_origins="*")

RESULT_SAVING_DIR = "./wavAndTxt/"
userVoices = {

}

def _print(*args,**kwargs):
    print_screen = print
    print_file = partial(print, file=LOG["file_path"])
    if LOG["screen"]:
        __print = print_screen
    elif LOG["file"]:
        __print = print_file
    __print(*args,**kwargs)

@socketio.on('connect_event')
def connected_msg(msg):
    _print("连接ID：" + request.sid + "触发connect_event", "收到配置参数：",msg)
    voiceQueue = queue.Queue()
    userVoices[request.sid]= {
        'voiceQueue': voiceQueue,
    }
    emit("connection_established", {'data':"nothing to say, just do it!"})
    error_msg = "正常！"

    try:
        for result in google_ASR(request.sid,**msg):

            if result['type'] in ("final"): 
                _print("收到Google解析后的结果{result}".format(result=result))
                try:
                    emit('server_response', {'data':result["result"], "bg":result["bg"].__str__(), "ed": result["ed"].__str__()})
                except KeyError as e:
                    if "disconnected" in str(e):
                        _print("client was disconnected!!")
                    else:
                        raise e
            if result['type'] in ("partial"):
                emit("server_partial_response",{'data':result["result"]})

            elif result['type'] == "error":
                emit('server_response',{'data': "错误："+ result["result"]})
    
    except Exception as e:
        _print("错误发生在sid:"+request.sid)
        error_msg = "超时！"
        raise e
        #_print(e)
        #emit("server_response",{'data':"连接超时或语音服务异常!"})
    finally:
        #emit("server_response_end",{'data':error_msg},callback=lambda:disconnect())
        _print("end","!"*50)
        emit("server_response_end",{'data':error_msg})


@socketio.on('voice_push_event')
def client_msg(msg):
    try:
        voiceQueue = userVoices[request.sid]['voiceQueue']
    except KeyError as e:
        _print("发生键错误，可能是用户未在创建链接时调用connected_msg！")
        _print(str(e))
        
    try:
        voiceData = msg['voiceData']
    except KeyError as e:
        _print("即将发生键错误，查看发送信息为：")
        _print(len(msg))
        if msg == {}:
            return "client_msg is empty dict!"
        else:
            raise e
    if voiceData is None or len(voiceData)==0:
         return
    
    import time
    _print("收到"+ str(type(voiceData)) +"块，大小:{voiceData_len} 来自{sid}".format(voiceData_len=len(voiceData),sid=request.sid))

    if type(voiceData) == type([0]):
        voiceData = np.array(voiceData,np.int8).tobytes()
        _print("将list int8 转 bytes")

    voiceQueue.put(voiceData)
    emit("voice_ack",{"data":"received "+ str(len(voiceData)) + " bytes block, continue to push event"})
    return "client_msg recieved"


def google_ASR(sid,language_code="zh_CN",sample_rate="16000"):
    voiceQueue = userVoices[sid]['voiceQueue']

    client = speech.SpeechClient()
    config = speech.types.RecognitionConfig(
        encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=int(sample_rate),
        language_code=language_code,
        max_alternatives=1,
        enable_word_time_offsets=False,
        enable_automatic_punctuation=True)

    streaming_config = speech.types.StreamingRecognitionConfig(
        config=config,
        interim_results=True)

    def audioGenerator(voiceQueue,sid):
        import time
        timename = time.strftime('%Y-%m-%d_%H:%M:%S',time.localtime(time.time()))
        timeoutCnt = 0
        lastTimeoutTime = time.time()
        with open(RESULT_SAVING_DIR+'{timename}_{sid}.wav'.format(timename=timename,sid=sid),'wb') as f:
            while True:
                try:
                    chunk = voiceQueue.get(timeout=2)
                    if chunk == "EOF":
                        _print("终止生成器")
                        break
                    f.write(chunk)
                    _print("yield 余下的块")
                    yield chunk
                except queue.Empty as e:
                    timeoutTime = time.time()
                    timeoutInterval = timeoutTime - lastTimeoutTime
                    _print("yield 0 防止超时")
                    if timeoutCnt >7 and timeoutInterval < 20:
                        break
                    else:
                        # 每15秒一个连续超时计数区间，15秒内连续超时次数大于7次终止服务
                        # 如果上一次超时时间间隔超过15秒，重新计算时次数,以此分隔计数区间
                        if timeoutInterval >= 20:
                            _print("进入新的连续超时计数区间")
                            lastTimeoutTime = timeoutTime
                            timeoutCnt = 0
                        yield bytes([0,0]) 
                        timeoutCnt += 1

    firstItem = voiceQueue.get()
    voiceQueue.put(firstItem)
    
    audio_generator = audioGenerator(voiceQueue,sid)
    
    requests = (speech.types.StreamingRecognizeRequest(
                    audio_content=content)
                    for content in audio_generator)

    def eternal_response(requests, streaming_config, voiceQueue):

        responses = client.streaming_recognize(streaming_config,
                                                    requests)

        responses = (r for r in responses if (
            r.results and r.results[0].alternatives))
        try:       
            for r in responses:
                if r.results and r.results[0].alternatives:
                    yield r
        except google.api_core.exceptions.OutOfRange as e:
            _print(e)
            _print("超过305秒， 递归","!"*50)
            for r in eternal_response(requests, streaming_config, voiceQueue):
                yield r

    item = {"type":"final","result":"声音异常！！！", "bg":"0","ed":"0"}

    #_print("正准备解析")
    cnt = 0
    num_chars_printed = 0

    # last fianl result end time
    last_final_offset = 0

    for response in eternal_response(requests, streaming_config, voiceQueue):
        cnt +=1
        #_print("正在为第{cnt}个块进行解析")
        if not response.results:
            continue

        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        top_alternative = result.alternatives[0]
        transcript = top_alternative.transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        #
        # If the previous result was longer than this one, we need to #print
        # some extra spaces to overwrite the previous result
        overwrite_chars = ' ' * (num_chars_printed - len(transcript))
        
        result_seconds = 0
        result_nanos = 0

        if result.result_end_time.seconds:
            result_seconds = result.result_end_time.seconds

        if result.result_end_time.nanos:
            result_nanos = result.result_end_time.nanos

        # result end time since audio start
        result_end_time = int((result_seconds * 1000)
                                     + (result_nanos / 1000000))

        if not result.is_final:
            result = transcript + overwrite_chars + "\n"
            _print(result)
            num_chars_printed = len(transcript)
            item = {"type":"partial","result":result}
        else:
            result = transcript + overwrite_chars
            num_chars_printed = 0
            item = {"type":"final","result":result, "bg":last_final_offset, "ed":result_end_time}
            last_final_offset = result_end_time

        if item['type'] == 'final':
            with open(RESULT_SAVING_DIR+'{sid}.txt'.format(sid=sid),'w') as f:
                f.write(item['result'])

        yield item

    if cnt == 0:
        yield item



if __name__ == '__main__':
    #f = open("flask.log",'a')
    #sys.stdout = f
    #sys.stderr = f
    socketio.run(app, host='0.0.0.0',port=7000,debug=True)