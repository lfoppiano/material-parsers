import json
from tempfile import NamedTemporaryFile

import gridfs
from flask import Flask, render_template, request, Response, Blueprint, url_for

from grobid_client_generic import grobid_client_generic
from linking_module import RuleBasedLinker
from process.supercon_batch_mongo_extraction import connect_mongo
from process.utils import json_serial

bp = Blueprint('supercon', __name__)

with open('./config.json', 'r') as fp:
    config = json.load(fp)
    db_name = config['mongo']['database']


@bp.route('/version')
def version():
    return '0.0.1'


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/<page>')
def render_page(page):
    return render_template(page)


@bp.route('/annotation/feedback', methods=['POST'])
def annotation_feedback():
    print("Received feedback request. id=" + str(request.form))
    return request.form


@bp.route('/publishers')
def get_publishers():
    connection = connect_mongo(config=config)
    db = connection[db_name]

    filtered_distinct_publishers = list(filter(lambda x: x is not None, db.tabular.distinct("publisher")))
    return {"publishers": filtered_distinct_publishers}


@bp.route('/years')
def get_years():
    connection = connect_mongo(config=config)
    db = connection[db_name]

    distinct_years = db.tabular.distinct("year")
    filtered_distinct_years = list(filter(lambda x: x is not None and 1900 < x < 3000, distinct_years))
    return {"years": filtered_distinct_years}


@bp.route('/process', methods=['POST'])
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

@bp.route("/stats", methods=["GET"])
def get_stats():
    connection = connect_mongo(config=config)
    db_supercon_dev = connection[db_name]
    tabular_collection = db_supercon_dev.get_collection("tabular")

    pipeline_group_by_publisher = [{"$group": {"_id": "$publisher", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    by_publisher = tabular_collection.aggregate(pipeline_group_by_publisher)

    pipeline_group_by_year = [{"$group": {"_id": "$year", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    by_year = tabular_collection.aggregate(pipeline_group_by_year)

    pipeline_group_by_journal = [{"$group": {"_id": "$journal", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    by_journal = tabular_collection.aggregate(pipeline_group_by_journal)

    return render_template("stats.html", by_publisher=by_publisher, by_year=by_year, by_journal=by_journal)

@bp.route("/tabular", methods=["GET"])
def get_tabular_from_form_data():
    type = request.args.get('type', default="automatic", type=str)
    publisher = request.args.get('publisher', default=None, type=str)
    year = request.args.get('year', default=None, type=str)

    return get_tabular(type, publisher, year)


@bp.route("/tabular/<type>", methods=["GET"])
def get_tabular_from_path_by_type(type):
    return get_tabular(type)


@bp.route("/tabular/<type>/<publisher>/<year>", methods=["GET"])
def get_tabular_from_path_by_type_publisher_year(type, publisher, year):
    return get_tabular(type, publisher, year)


@bp.route("/tabular/<type>/<year>", methods=["GET"])
def get_tabular_from_path_by_type_year(type, year):
    return get_tabular(type, publisher=None, year=year)


def get_tabular(type='automatic', publisher=None, year=None, start=None, length=None):
    connection = connect_mongo(config=config)
    db_supercon_dev = connection[db_name]

    # pipeline = [
    #     {"$group": {"_id": "$hash", "versions": {"$addToSet": "$timestamp"}, "count": {"$sum": 1}}},
    #     {"$sort": {"count": -1}}
    # ]
    entries = []
    tabular_collection = db_supercon_dev.get_collection("tabular")
    if type == "manual":
        for entry in tabular_collection.find({"type": "manual"}):
            del entry['_id']
            entry['section'] = entry['section'][1:-1] if 'section' in entry and entry['section'] is not None else ''
            entry['subsection'] = entry['subsection'][1:-1] if 'subsection' in entry and entry[
                'subsection'] is not None else ''
            entry['doc_url'] = None
            entries.append(entry)

    elif type == 'automatic':
        # document_collection = db_supercon_dev.get_collection("document")
        # documents = document_collection.aggregate(pipeline)
        # document_list = list(documents)
        # aggregation_query = [{"$sort": {"hash": 1, "timestamp": 1}}, {"$group": {"_id": "$hash", "lastDate": {"$last": "$timestamp"}}}]
        # aggregation_query = [{"$match": {"type": type}}] + aggregation_query
        # cursor_aggregation = document_collection.aggregate(aggregation_query)

        query = {"type": "automatic"}

        if publisher:
            query['publisher'] = publisher

        if year:
            query['year'] = int(year)

        for entry in tabular_collection.find(query):
            del entry['_id']
            entry['section'] = entry['section'][1:-1] if 'section' in entry and entry['section'] is not None else ''
            entry['subsection'] = entry['subsection'][1:-1] if 'subsection' in entry and entry[
                'subsection'] is not None else ''
            entry['title'] = entry['title'][1:-1] if 'title' in entry and entry[
                'title'] is not None else ''
            entry['doc_url'] = url_for('supercon.get_document', hash=entry['hash'])
            entries.append(entry)

    return json.dumps(entries, default=json_serial)


@bp.route("/automatic_database", methods=["GET"])
def get_automatic_database():
    return render_template("automatic_database.html")


@bp.route("/manual_database", methods=["GET"])
def get_manual_database():
    return render_template("manual_database.html")


@bp.route('/document/<hash>', methods=['GET'])
def get_document(hash):
    return render_template("document.html", hash=hash)


@bp.route('/annotation/<hash>', methods=['GET'])
def get_annotations(hash):
    '''Get annotations (latest version)'''
    connection = connect_mongo(config=config)
    db_supercon_dev = connection[db_name]
    annotations = db_supercon_dev.get_collection("document").find({"hash": hash}).sort("timestamp", -1)
    annotation = annotations[0]
    del annotation["_id"]
    return Response(json.dumps(annotation, default=json_serial), mimetype="application/json")


@bp.route('/pdf/<hash>', methods=['GET'])
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


@bp.route('/config', methods=['GET'])
def get_config(config_json='./config.json'):
    config = json.loads(open(config_json).read())
    return config


app = Flask(__name__, static_url_path='/supercon/static')
app.register_blueprint(bp, url_prefix='/supercon')
print(app.url_map)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
