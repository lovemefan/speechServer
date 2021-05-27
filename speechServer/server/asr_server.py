# -*- coding: utf-8 -*-
# @Time  : 2021/5/25 21:16
# @Author : lovemefan
# @Email : lovemefan@outlook.com
# @File : asr_server.py
import json
import queue

from sanic import Sanic
import asyncio
from sanic.log import logger
from websockets.legacy.protocol import WebSocketCommonProtocol

from config import WEBSOCKETS_TIME_OUT
from speechServer.pojo.ResponseBody import ResponseBody
from speechServer.utils.SignatureUtils import check_signature
from speechServer.utils.snowflake import IdWorker

app = Sanic("asr_server")
app.config.KEEP_ALIVE_TIMEOUT = 1
app.config.REQUEST_TIMEOUT = 1
app.config.RESPONSE_TIMEOUT = 10
app.config.WEBSOCKET_PING_INTERVAL = 2
app.config.WEBSOCKET_TIMEOUT = 10
# @app.listener('before_server_start')
# async def setup_db_redis(app, loop):
#     redis = aioredis.from_url("redis://localhost")
#     await redis.set("my-key", "value")
#     value = await redis.get("my-key", encoding="utf-8")
#     print(value)


# @app.listener('after_server_stop')
# async def close_db_redis(app, loop):
#     pass

# 储存客户端
client = dict()


@app.websocket("/asr", version=1)
async def handle(request, ws):
    args = request.args
    print(type(ws))
    # check_signature 鉴权算法查看文档
    if check_signature(args):

        while True:
            session_id = IdWorker().get_id()
            # 注册到客户端字典里面
            client[session_id] = queue.Queue()
            # disconnect if receive nothing in WEBSOCKETS_TIME_OUT seconds
            # 在规定时间未接收到任何消息就主动关闭
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=WEBSOCKETS_TIME_OUT)
                # handle the receive messages
                # 处理接受到的数据
                logger.info(f"message: {message}")
                if message.lower() == "ping":
                    # answer if receive the heartbeats
                    await ws.send('pong')
                    continue
                else:
                    # handle the messages except heartbeats
                    data = await asyncio.wait_for(ws.recv(), timeout=WEBSOCKETS_TIME_OUT)
                    data = json.loads(data)

                    await ws.send(f"{args}")

            except asyncio.TimeoutError:
                # Timeout handle
                # 处理超时
                await ws.send(ResponseBody(code=408, message="Connection Timeout").json())
                await ws.close(408, "TIMEOUT")
                break

            except asyncio.exceptions.CancelledError:
                # closed by client handle
                # 处理被客户端主动关闭连接
                logger.info("client closed the connection")
                break

            except json.decoder.JSONDecodeError:
                await ws.send(ResponseBody(code=408, message="Connection Timeout").json())
                await ws.close(403, "the String must be json format")
                break

    else:
        await ws.send(ResponseBody(code=401, message="Unauthorized").json())
        await ws.close(401, "Unauthorized")


async def handle_messages_from_redis(ws: WebSocketCommonProtocol):
    """
    receive the results from redis by subscribe the channel ，put the results in queue respectively
    从redis订阅数据,并将结果放到对应session的队列当中
    :param ws:
    :return:
    """
    pass


async def handle_data_from_client(data, ws):
    """
    handle the data from client
    处理客户端的数据
    including :
    1): validate the data and deliver data publish to redis from client
    2): receive the results from the corresponding session queue
    验证数据，接受接受数据并发布到redis，从对应的session的队列中取出数据
    :param data: the data of client
    :param ws: the websocket instance to send and receive
    :return:
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)