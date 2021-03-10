import argparse
import json
import os
import sys
from datetime import datetime
from hashlib import blake2b
from pathlib import Path

import gridfs
from pymongo import MongoClient

from supercon.process.supercon_batch import process_file


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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract superconductor materials and properties and save them on mongodb - extraction")
    parser.add_argument("--input", help="Input directory", type=Path, required=True)
    parser.add_argument("--config", help="Configuration file", type=Path, required=True)

    args = parser.parse_args()

    input_path = args.input
    config_path = args.config

    if not os.path.exists(config_path):
        print("The config file does not exists. ")
        parser.print_help()
        sys.exit(-1)

    if not os.path.isdir(input_path):
        print("The input should be a directory")
        parser.print_help()
        sys.exit(-1)

    connection = connect_mongo(config_path)
    db_supercon_dev = connection['supercon_dev']
    fs_binary = gridfs.GridFS(db_supercon_dev, collection='binary')

    for root, dirs, files in os.walk(input_path):
        for file_ in files:
            if not file_.lower().endswith(".pdf"):
                continue

            abs_path = os.path.join(root, file_)
            extracted_data = process_file(abs_path, "json")
            extracted_json = json.loads(extracted_data)
            hash_full = get_file_hash(abs_path)
            hash = hash_full[:10]
            extracted_json['hash'] = hash
            timestamp = datetime.utcnow()
            extracted_json['timestamp'] = timestamp

            print("Storing annotations in mongodb, hash: ", hash)
            document_id = db_supercon_dev.document.insert_one(extracted_json).inserted_id

            print("Storing binary ", hash)
            file = fs_binary.find_one({"hash": hash})
            if not file:
                with open(abs_path, 'rb') as f:
                    fs_binary.put(f, hash=hash, timestamp=timestamp)
            else:
                print("Binary already there, skipping")

            print("Inserted document ", document_id)
