import json
from tempfile import NamedTemporaryFile

from flask import Flask, render_template, request

from src.grobid_client_generic import grobid_client_generic
from src.linking.linkingModule import process_paragraph

app = Flask(__name__)


@app.route('/version')
def version():
    return '0.0.1'


@app.route('/')
def root():
    return render_template('index.html')


@app.route('/annotate', methods=['POST'])
def annotate_pdf():
    file = request.files['input']
    grobid = grobid_client_generic(config_path="./config.json")
    tf = NamedTemporaryFile()
    tf.write(file.read())
    return grobid.process_pdf(tf.name, 'annotatePDF', headers={'Accept': 'application/json'})


@app.route('/process', methods=['POST'])
def process_pdf():
    file = request.files['input']
    grobid = grobid_client_generic(config_path="./config.json")
    tf = NamedTemporaryFile()
    tf.write(file.read())
    result_text = grobid.process_pdf(tf.name, 'processPDF', headers={'Accept': 'application/json'})

    result_json = json.loads(result_text)
    new_paragraphs = []
    paragraphs = result_json['paragraphs']
    for index, paragraph in enumerate(paragraphs):
        if len(paragraph['spans']) > 0:
            extracted_data_from_paragraphs = process_paragraph(paragraph)

            if len(extracted_data_from_paragraphs) > 0:
                # here the data has been manipulated and it's a real mess...
                for sentence in extracted_data_from_paragraphs:
                    new_paragraphs.append(sentence)
            else:
                new_paragraphs.append(paragraph)
        else:
            new_paragraphs.append(paragraph)

    result_json['paragraphs'] = new_paragraphs

    return result_json


@app.route('/config', methods=['GET'])
def get_config(config_json='./config.json'):
    config = json.loads(open(config_json).read())
    return config


if __name__ == '__main__':
    app.run(host='0.0.0.0')
