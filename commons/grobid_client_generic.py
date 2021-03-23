import json
import time
import os

import requests

from client import ApiClient

'''
This client is a generic client for any Grobid application and sub-modules.
At the moment, it supports only single document processing.    

Source: https://github.com/kermitt2/grobid-client-python 
'''
class grobid_client_generic(ApiClient):


    def __init__(self, config_path='./config.json', ping=False):
        self.config = None
        self._load_config(config_path, ping)
        os.environ['NO_PROXY'] = "nims.go.jp"

    def __init__(self, config={}, ping=False):
        self._load_config(config=config, ping=ping)
        os.environ['NO_PROXY'] = "nims.go.jp"

    def _load_config(self, path='./config.json', ping=False):
        """
        Load the json configuration 
        """
        config_json = open(path).read()
        self.config = json.loads(config_json)
        if ping:
            self.ping_grobid()

    def _load_config(self, config, ping=False):
        self.config = config
        if ping:
            self.ping_grobid()

    def ping_grobid(self):
        # test if the server is up and running...
        ping_url = self.get_grobid_url("ping")

        r = requests.get(ping_url)
        status = r.status_code

        if status != 200:
            print('GROBID server does not appear up and running ' + str(status))
        else:
            print("GROBID server is up and running")


    def get_grobid_url(self, action):
        grobid_config = self.config['grobid']
        base_url = grobid_config['server'] + grobid_config['prefix']
        action_url = base_url + grobid_config['url_mapping'][action]

        return action_url

    def process_text(self, input, method_name='superconductors', params={}, headers={"Accept": "application/json"}):

        files = {
            'text': input
        }

        the_url = self.get_grobid_url(method_name)

        res, status = self.post(
            url=the_url,
            files=files,
            data=params,
            headers=headers
        )

        if status == 503:
            time.sleep(self.config['sleep_time'])
            return self.process_text(input, method_name, params, headers)
        elif status != 200:
            print('Processing failed with error ' + str(status))
        else:
            return res.text

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

        the_url = self.get_grobid_url(method_name)

        if "?" in the_url:
            split = the_url.split("?")
            the_url = split[0]
            params = split[1]

            params = {param.split("=")[0]: param.split("=")[1] for param in params.split("&")}

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
            print('Processing failed with error ', status)
        elif status == 204:
            print('No content returned. Moving on. ')
        else:
            return res.text


    def process_json(self, text, method_name="processJson", params={}, headers={"Accept": "application/json"}):


        files = {
            'input': (
                None,
                text,
                'application/json',
                {'Expires': '0'}
            )
        }

        the_url = self.get_grobid_url(method_name)

        if "?" in the_url:
            split = the_url.split("?")
            the_url = split[0]
            params = split[1]

            params = {param.split("=")[0]: param.split("=")[1] for param in params.split("&")}

        res, status = self.post(
            url=the_url,
            files=files,
            data=params,
            headers=headers
        )

        if status == 503:
            time.sleep(self.config['sleep_time'])
            return self.process_json(text, method_name, params, headers)
        elif status != 200:
            print('Processing failed with error ', status)
        elif status == 204:
            print('No content returned. Moving on. ')
        else:
            return res.text
