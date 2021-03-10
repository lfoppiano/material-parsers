import json
from datetime import date, datetime
from tempfile import NamedTemporaryFile

import gridfs
from flask import Flask, render_template, request, Response
from grobid_client_generic import grobid_client_generic
from linking_module import RuleBasedLinker

from supercon.process.supercon_batch_mongo_extraction import connect_mongo

app = Flask(__name__)


@app.route('/version')
def version():
    return '0.0.1'


@app.route('/')
def root():
    return render_template('index.html')


@app.route('/<page>')
def render_page(page):
    return render_template(page)


@app.route('/annotation/feedback', methods=['POST'])
def annotation_feedback():
    # print("Received feedback request. id=" + str(request.form['pk']) + ", name= " + str(
    #     request.form['name']) + ", value=" + str(request.form['value']))
    print("Received feedback request. id=" + str(request.form))
    return request.form


@app.route('/process', methods=['POST'])
def process_pdf():
    file = request.files['input']
    grobid = grobid_client_generic(config_path="./config.json")
    tf = NamedTemporaryFile()
    tf.write(file.read())
    result_text = grobid.process_pdf(tf.name, 'processPDF', params={'disableLinking': 'true'},
                                     headers={'Accept': 'application/json'})

    result_json = json.loads(result_text)
    new_paragraphs = []
    paragraphs = result_json['paragraphs']
    for index, paragraph in enumerate(paragraphs):
        if 'spans' not in paragraph:
            new_paragraphs.append(paragraph)
            continue

        extracted_data_from_paragraphs = RuleBasedLinker().process_paragraph(paragraph)
        for sentence in extracted_data_from_paragraphs:
            new_paragraphs.append(sentence)

    result_json['paragraphs'] = new_paragraphs

    return result_json


@app.route("/documents", methods=["GET"])
def get_documents():
    connection = connect_mongo("config.json")
    db_supercon_dev = connection['supercon_dev']

    pipeline = [
        {"$group": {"_id": "$hash", "versions": {"$addToSet": "$timestamp"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]

    documents = db_supercon_dev.get_collection("document").aggregate(pipeline)
    document_list = list(documents)
    return render_template("documents.html", documents=document_list)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


@app.route('/document/<hash>', methods=['GET'])
def get_document(hash):
    # connection = connect_mongo("config.json")
    # db_supercon_dev = connection['supercon_dev']
    # fs_binary = gridfs.GridFS(db_supercon_dev, collection='binary')
    # file = fs_binary.find_one({"hash": hash})
    # if file is None:
    #     return 404
    # else:
    #     binary_pdf = fs_binary.get(file._id).read()
    #     annotations = db_supercon_dev.get_collection("document").find({"hash": hash}).sort("timestamp", -1)
    #     annotation = annotations[0]
    #     del annotation["_id"]
    #     json_annotation = json.dumps(annotation, default=json_serial)

    return render_template("document.html", hash=hash)


@app.route('/annotation/<hash>', methods=['GET'])
def get_annotations(hash):
    '''Get annotations (latest version)'''
    connection = connect_mongo("config.json")
    db_supercon_dev = connection['supercon_dev']
    annotations = db_supercon_dev.get_collection("document").find({"hash": hash}).sort("timestamp", -1)
    annotation = annotations[0]
    del annotation["_id"]
    return Response(json.dumps(annotation, default=json_serial), mimetype="application/json")


@app.route('/pdf/<hash>', methods=['GET'])
def get_binary(hash):
    '''GET PDF / binary file '''
    connection = connect_mongo("config.json")
    db_supercon_dev = connection['supercon_dev']
    fs_binary = gridfs.GridFS(db_supercon_dev, collection='binary')

    file = fs_binary.find_one({"hash": hash})
    if file is None:
        return 404
    else:
        return Response(fs_binary.get(file._id).read(), mimetype='application/pdf')


@app.route('/config', methods=['GET'])
def get_config(config_json='./config.json'):
    config = json.loads(open(config_json).read())
    return config


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
