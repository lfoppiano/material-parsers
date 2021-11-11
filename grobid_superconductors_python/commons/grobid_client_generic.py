import json
import time
import os

import requests

from .client import ApiClient

'''
This client is a generic client for any Grobid application and sub-modules.
At the moment, it supports only single document processing.    

Source: https://github.com/kermitt2/grobid-client-python 
'''
class grobid_client_generic(ApiClient):


    def __init__(self, config_path=None, ping=False):
        self.config = None
        if config_path:
            self._load_config_from_file(path=config_path, ping=ping)
        os.environ['NO_PROXY'] = "nims.go.jp"

    def _load_config_from_file(self, path='./config.json', ping=False):
        """
        Load the json configuration 
        """
        config_json = open(path).read()
        self.config = json.loads(config_json)
        if ping:
            result = self.ping_grobid()
            if not result:
                raise Exception("Grobid is down.")

    def set_config(self, config, ping=False):
        self.config = config
        if ping:
            try:
                result = self.ping_grobid()
                if not result:
                    raise Exception("Grobid is down.")
            except Exception:
                raise Exception("Grobid is down")

    def ping_grobid(self):
        # test if the server is up and running...
        ping_url = self.get_grobid_url("ping")

        r = requests.get(ping_url)
        status = r.status_code

        if status != 200:
            print('GROBID server does not appear up and running ' + str(status))
            return False
        else:
            print("GROBID server is up and running")
            return True

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
            # print('Processing failed with error ', status)
            return None, status
        elif status == 204:
            # print('No content returned. Moving on. ')
            return None, status
        else:
            return res.text, status

    def process_json(self, text, method_name="processJson", params={}, headers={"Accept": "application/json"}, verbose=False):
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
            return self.process_json(text, method_name, params, headers), status
        elif status != 200:
            if verbose:
                print('Processing failed with error ', status)
            return None, status
        elif status == 204:
            if verbose:
                print('No content returned. Moving on. ')
            return None, status
        else:
            return res.text, status
