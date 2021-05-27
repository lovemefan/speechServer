# -*- coding: utf-8 -*-
# @Time  : 2021/5/25 21:16
# @Author : lovemefan
# @Email : lovemefan@outlook.com
# @File : asr_server.py
import json

from sanic import Sanic
import asyncio

import aioredis
from sanic.log import logger

from config import WEBSOCKETS_TIME_OUT
from pojo.ResponseBody import ResponseBody

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


@app.websocket("/asr", version=1)
async def handle(request, ws):
    args = request.args
    # 鉴权
    if check_signature(args):
        while True:

            message = await asyncio.wait_for(ws.recv(), timeout=WEBSOCKETS_TIME_OUT)
            logger.info(f"message: {message}")
            if message.lower() == "ping":
                await ws.send('pong')
                continue
            else:
                await ws.send(f"{args}")
            # await ws.recv()

    else:
        await ws.send(ResponseBody(code=401, message="Unauthorized").json())
        await ws.close(401, "Unauthorized")


@app.websocket("/feed")
async def feed(request, ws):
    while True:
        data = "hello!"
        print("Sending: " + data)
        await ws.send(data)
        data = await ws.recv()
        print("Received: " + data)






        return True


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)