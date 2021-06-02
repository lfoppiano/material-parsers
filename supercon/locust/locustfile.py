import os
import random

from locust import HttpUser, task, between, tag


class QuickstartUser(HttpUser):
    wait_time = between(5, 9)

    pdf_list = []

    @tag('process_pdf')
    @task
    def process_pdf(self):
        n = random.randint(0, len(self.pdf_list) - 1)
        pdf = self.pdf_list[n]

        headers = {"Accept": "application/json"}
        files = {
            'input': (
                pdf,
                open(pdf, 'rb'),
                'application/pdf',
                {'Expires': '0'}
            )
        }

        self.client.post(url="/service/process/pdf", files=files, headers=headers, name="process/pdf")

    def on_start(self):
        # pydevd_pycharm.settrace('localhost', port=8999, stdoutToServer=True, stderrToServer=True)
        for root, dirs, files in os.walk("/Users/lfoppiano/development/projects/grobid/grobid-superconductors/resources/dataset/superconductors/corpus/pdf/batches"):
            for file_ in files:
                if not file_.lower().endswith(".pdf"):
                    continue
                abs_path = os.path.join(root, file_)

                self.pdf_list.append(abs_path)
