# Sparse code to fetch tsv files directly from Webanno / Inception and convert it to XML


import os
import sys
from base64 import b64encode
from sys import argv
from xml.sax.saxutils import escape

import requests

os.environ['NO_PROXY'] = 'falcon.nims.go.jp'

webanno_url = "http://falcon.nims.go.jp/webanno"
webanno_prefix = "/api/aero/v1"

userAndPass = b64encode(b"username:password").decode("ascii")
headers = {'Authorization': 'Basic %s' % userAndPass}


def get_file_list(project_id):
    ids = []

    url = webanno_url + webanno_prefix + "/projects/" + project_id + "/documents"

    print(url)

    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        content = r.json()

        if 'body' in content:
            for document in content['body']:
                ids.append((document['id'], document['name']))

    else:
        print("Error: ", r)

    return ids


# http://falcon.nims.go.jp/webanno/api/aero/v1/projects/3/documents/142/annotations/lfoppiano
def download(project_id, document_id, user_id):
    url = webanno_url + webanno_prefix + "/projects/" + str(project_id) + "/documents/" + str(
        document_id) + "/annotations/" + user_id

    print(url)
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        return r.text
    else:
        print(r)

# Example: 
# tsv = download(project_id, file_id, user_id)
# l = transform(tsv.split("\n"))
# writeOutput(l, output + "/" + file_name.replace("tsv", "tei.xml"))
