import json

import bottle
import plac
from bottle import request, run

from materialNER import MaterialNER

bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024 * 1024


class Service(object):
    def __init__(self):
        self.materialNER = MaterialNER()

    def info(self):
        returnText = "Material NER service."
        return returnText

    def process(self):
        input_raw = request.forms.get("input")
        input_json = json.loads(input_raw)

        if 'texts' in input_json:
            texts = input_json['texts']
        elif 'text' in input_json:
            texts = [input_json['text']]
        else:
            bottle.response.status = 406
            return "The input JSON must contains either 'text' (single) or 'texts' (multiple) input paragraphs."

        output = self.materialNER.process(texts)

        bottle.response.content_type = "application/json"
        return json.dumps(output)


@plac.annotations(
    host=("Hostname where to run the service", "option", "host", str),
    port=("Port where to run the service", "option", "port", str),
)
def init(host='0.0.0.0', port='8080'):
    app = Service()

    bottle.route('/process/text', method="POST")(app.process)
    bottle.route('/info')(app.info)
    bottle.debug(False)
    run(host=host, port=port, debug=True)


if __name__ == "__main__":
    plac.call(init)
