import argparse
import json
import os
import sys
from hashlib import blake2b
from pathlib import Path

from pymongo import MongoClient

from supercon.controller import json_serial
from supercon.process.supercon_batch import grobid_client


def connect_mongo(config_path):
    with open(config_path, 'r') as fp:
        configuration = json.load(fp)
    mongo_client_url = configuration['mongo']['server']
    c = MongoClient(mongo_client_url)

    return c


def get_file_hash(fname):
    hash_md5 = blake2b()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def process_json(json_text):
    r = grobid_client.process_json(json.dumps(json_text, default=json_serial), "processJson")
    if r is None:
        print("Response is empty or without content for " + str(json_text) + ". Moving on. ")
        return []
        # raise Exception("Response is None for " + str(source_path) + ". Moving on. ")
    else:
        output = r

    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract superconductor materials and properties and save them on mongodb - extraction")
    parser.add_argument("--config", help="Configuration file", type=Path, required=True)

    args = parser.parse_args()

    config_path = args.config

    if not os.path.exists(config_path):
        print("The config file does not exists. ")
        parser.print_help()
        sys.exit(-1)

    connection = connect_mongo(config_path)
    db_supercon_dev = connection['supercon_dev']

    document_collection = db_supercon_dev.get_collection("document")

    # cursor = db_supercon_dev.find({}, {"hash": 1}).distinct()
    cursor_aggregation = document_collection.aggregate([{"$sort": {"hash": 1, "timestamp": 1}}, {"$group": {"_id": "$hash", "lastDate": {"$last": "$timestamp"}}}])

    for item in cursor_aggregation:
        document = document_collection.find_one({"hash": item['_id'], "timestamp": item['lastDate']})
        del document['pages']
        del document['_id']
        for para in document['paragraphs']:
            for span in para['spans'] if 'spans' in para else []:
                if 'boundingBoxes' in span:
                    del span['boundingBoxes']
            if 'tokens' in para:
                del para['tokens']
        aggregated_entries = process_json(document)

        if aggregated_entries:
            json_aggregated_entries = json.loads(aggregated_entries)
            for ag_e in json_aggregated_entries:
                ag_e['hash'] = item['_id']
                ag_e['timestamp'] = item['lastDate']

            tabular_collection = db_supercon_dev.get_collection("tabular")
            tabular_collection.delete_many({"hash": item['_id']})
            tabular_collection.insert_many(json_aggregated_entries)
