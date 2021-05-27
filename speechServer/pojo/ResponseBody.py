# -*- coding: utf-8 -*-
# @Time  : 2021/5/25 21:52
# @Author : lovemefan
# @Email : lovemefan@outlook.com
# @File : ResponseBody.py
import json


class ResponseBody:
    def __init__(self, code: int, message: str, data: str = "", sid: str = ""):
        self.__code = code
        self.__message = message
        self.__message = message
        self.__data = data
        self.__sid = sid

    def __str__(self):
        return {
            "code": self.__code,
            "message": self.__message,
            "data": self.__data,
            "sid": self.__sid,
        }.__str__()

    def __dict__(self):
        return {
            "code": self.__code,
            "message": self.__message,
            "data": self.__data,
            "sid": self.__sid,
        }

    def json(self):
        return json.dumps(self.__dict__())