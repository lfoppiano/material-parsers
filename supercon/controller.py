import json
from datetime import date, datetime
from tempfile import NamedTemporaryFile

import gridfs
from flask import Flask, render_template, request, Response
from grobid_client_generic import grobid_client_generic
from linking_module import RuleBasedLinker

from supercon.process.supercon_batch_mongo_extraction import connect_mongo

app = Flask(__name__)

with open('./config.json', 'r') as fp:
    config = json.load(fp)
    db_name = config['mongo']['database']

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


@app.route("/tabular", methods=["GET"])
def get_tabular():
    connection = connect_mongo(config=config)
    db_supercon_dev = connection[db_name]

    # pipeline = [
    #     {"$group": {"_id": "$hash", "versions": {"$addToSet": "$timestamp"}, "count": {"$sum": 1}}},
    #     {"$sort": {"count": -1}}
    # ]

    document_collection = db_supercon_dev.get_collection("document")
    # documents = document_collection.aggregate(pipeline)
    # document_list = list(documents)
    cursor_aggregation = document_collection.aggregate(
        [{"$sort": {"hash": 1, "timestamp": 1}}, {"$group": {"_id": "$hash", "lastDate": {"$last": "$timestamp"}}}])

    tabular_collection = db_supercon_dev.get_collection("tabular")
    entries = []
    for document in cursor_aggregation:
        hash = document['_id']
        timestamp = document['lastDate']

        for entry in tabular_collection.find({"hash": hash, "timestamp": timestamp}):
            del entry['_id']
            entry['section'] = entry['section'][1:-1] if 'section' in entry and entry['section'] is not None else ''
            entry['subsection'] = entry['subsection'][1:-1] if 'subsection' in entry and entry['subsection'] is not None else ''
            entries.append(entry)

    return json.dumps(entries, default=json_serial)


@app.route("/documents", methods=["GET"])
def get_documents():
    return render_template("database.html")


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


@app.route('/document/<hash>', methods=['GET'])
def get_document(hash):
    return render_template("document.html", hash=hash)


@app.route('/annotation/<hash>', methods=['GET'])
def get_annotations(hash):
    '''Get annotations (latest version)'''
    connection = connect_mongo(config=config)
    db_supercon_dev = connection[db_name]
    annotations = db_supercon_dev.get_collection("document").find({"hash": hash}).sort("timestamp", -1)
    annotation = annotations[0]
    del annotation["_id"]
    return Response(json.dumps(annotation, default=json_serial), mimetype="application/json")


@app.route('/pdf/<hash>', methods=['GET'])
def get_binary(hash):
    '''GET PDF / binary file '''
    connection = connect_mongo(config=config)
    db_supercon_dev = connection[db_name]
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
