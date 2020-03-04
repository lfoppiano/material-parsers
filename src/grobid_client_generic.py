import json
import time

import requests

from src.client import ApiClient

'''
This client is a generic client for any Grobid application and sub-modules.
At the moment, it supports only single document processing.    
'''


class grobid_client_generic(ApiClient):

    def __init__(self, config_path='./config.json'):
        self.config = None
        self._load_config(config_path)

    def _load_config(self, path='./config.json'):
        """
        Load the json configuration 
        """
        config_json = open(path).read()
        self.config = json.loads(config_json)

        # test if the server is up and running...
        the_url = 'http://' + self.config['grobid_server']
        if len(self.config['grobid_port']) > 0:
            the_url += ":" + self.config['grobid_port']
        the_url += self.config['url_mapping']['ping']

        r = requests.get(the_url)
        status = r.status_code

        if status != 200:
            print('GROBID server does not appear up and running ' + str(status))
        else:
            print("GROBID server is up and running")

    def process_text(self, input, params={}):
        pass

    def process_pdf_batch(self, pdf_files, params={}):
        pass

    def process_pdf(self, pdf_file, method_name, params={}, headers={"Accept": "application/json"}):

        files = {
            'input': (
                pdf_file,
                open(pdf_file, 'rb'),
                'application/pdf',
                {'Expires': '0'}
            )
        }

        the_url = 'http://' + self.config['grobid_server']
        if len(self.config['grobid_port']) > 0:
            the_url += ":" + self.config['grobid_port']
        the_url += self.config['url_mapping'][method_name]

        res, status = self.post(
            url=the_url,
            files=files,
            data=params,
            headers=headers
        )

        if status == 503:
            time.sleep(self.config['sleep_time'])
            return self.process_pdf(pdf_file, method_name, params, headers)
        elif status != 200:
            print('Processing failed with error ' + str(status))
        else:
            return res.text
