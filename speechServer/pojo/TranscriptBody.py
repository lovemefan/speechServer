#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2021/5/27 下午7:45
# @Author  : lovemefan
# @File    : TranscriptBody.py
import json


class TranscriptBody:
    """The transcript body is the result of speech translation task.
    Using as the return format from speech SDK (service layer) to speechRoute (routes layer)
    """
    def __init__(self, task_id: str = None, speech_id: str = None, status_text: str = None, data: str = None):
        """initial the Transcript body
        Args:
            task_id (str): task id
            speech_id (str): status code, detail see backend/utils/StatusCode.py
            status_text (str): Describe text of status.
            data (str)： list of Sentences corresponding to speech,
            each sentence conclude text and timestamp information.
        """
        self.task_id = task_id
        self.speech_id = speech_id
        self.status_text = status_text
        self.data = data

    def __dict__(self):
        return {
            "task_id": self.task_id,
            "speech_id": self.speech_id,
            "status_text": self.status_text,
            "data": self.data
        }

    def json(self):
        return json.dumps(self.__dict__())


