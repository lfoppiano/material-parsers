import json
import os
import random

from locust import HttpUser, task, between, tag
from locust.contrib.fasthttp import FastHttpUser


class QuickstartUser(FastHttpUser):
    wait_time = between(5, 9)

    paragraphs = []

    # @task
    # def process_class(self):
    #     pass

    @tag('classify_temperature')
    @task
    def classify_temperature(self):
        n = random.randint(0, len(self.paragraphs) - 1)
        paragraph = self.paragraphs[n]

        headers = {"Accept": "application/json"}
        files = {"input": json.dumps(paragraph)}
        self.client.post(path="/classify/tc", data=files, headers=headers, name="/classify/tc")

    @tag('process_links')
    @task
    def process_links(self):
        n = random.randint(0, len(self.paragraphs) - 1)
        paragraph = self.paragraphs[n]

        headers = {"Accept": "application/json"}
        files = {"input": json.dumps(paragraph)}
        self.client.post(path="/process/link/single", data=files, headers=headers, name="/process/link/single")


    def on_start(self):
        # pydevd_pycharm.settrace('localhost', port=8999, stdoutToServer=True, stderrToServer=True)
        for root, dirs, files in os.walk("paragraphs/"):
            for file_ in files:
                if not file_.lower().endswith(".json"):
                    continue
                abs_path = os.path.join(root, file_)

                with open(abs_path, 'r') as f:
                    paragraphs = json.load(f)
                    self.paragraphs.extend(paragraphs)

