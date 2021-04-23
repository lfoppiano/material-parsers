import argparse
import json
import math
import multiprocessing
import os
import sys
from datetime import datetime
from hashlib import blake2b
from multiprocessing import Manager
from pathlib import Path

import gridfs
from grobid_client_generic import grobid_client_generic
from pymongo import MongoClient


def connect_mongo(config_path):
    with open(config_path, 'r') as fp:
        configuration = json.load(fp)
    mongo_client_url = configuration['mongo']['server']
    c = MongoClient(mongo_client_url)

    return c


def connect_mongo(config=None):
    if config is None:
        raise Exception("Config is None")
    mongo_client_url = config['mongo']['server'] if 'mongo' in config and 'server' in config['mongo'] else ''
    c = MongoClient(mongo_client_url)

    return c


def get_file_hash(fname):
    hash_md5 = blake2b()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class MongoSuperconProcessor:
    grobid_client = None
    config = {}

    def __init__(self, config_path):
        config_json = open(config_path).read()
        self.config = json.loads(config_json)
        self.grobid_client = grobid_client_generic(config=self.config, ping=True)

    def write_mongo_status(self, queue_status, db_name, service):
        '''Writed the status of the document being processed'''
        connection = connect_mongo(config=self.config)
        db = connection[db_name]
        while True:
            status_info = queue_status.get(block=True)
            if status_info is None:
                print("Got termination. Shutdown processor.")
                queue_status.put(None)
                break

            status_info['service'] = service
            db.logger.insert_one(status_info)
        pass

    def write_mongo_single(self, queue_output, db_name):
        '''Write the result of the document being processed'''

        connection = connect_mongo(config=self.config)
        db = connection[db_name]
        fs_binary = gridfs.GridFS(db, collection='binary')
        while True:
            output = queue_output.get(block=True)
            if output is None:
                print("Got termination. Shutdown processor.")
                queue_output.put(None)
                break

            output_json = output[0]
            output_original_path = output[1]
            hash = output_json['hash']
            timestamp = output_json['timestamp']

            print("Storing annotations in mongodb, hash: ", hash)
            document_id = db.document.insert_one(output_json).inserted_id
            print("Storing binary ", hash)
            file = fs_binary.find_one({"hash": hash})
            if not file:
                with open(output_original_path, 'rb') as f:
                    fs_binary.put(f, hash=hash, timestamp=timestamp)
            else:
                print("Binary already there, skipping")
            print("Inserted document ", document_id)

    def process_batch_single(self, queue_input, queue_output, queue_status):
        while True:
            source_path = queue_input.get(block=True)
            if source_path is None:
                print("Got termination. Shutdown processor.")
                queue_input.put(source_path)
                break

            print("Processing file " + str(source_path))

            r, status = self.grobid_client.process_pdf(str(source_path), "processPDF",
                                                       headers={"Accept": "application/json"})
            if r is None:
                print("Response is empty or without content for " + str(source_path) + ". Moving on. ")
            else:
                extracted_json = self.prepare_data(r, source_path)
                extracted_json['type'] = 'automatic'
                queue_output.put((extracted_json, source_path), block=True)

            status_info = {'path': str(source_path), 'status': status}
            queue_status.put(status_info, block=True)

    def prepare_data(self, extracted_data, abs_path):
        extracted_json = json.loads(extracted_data)
        hash_full = get_file_hash(abs_path)
        hash = hash_full[:10]
        extracted_json['hash'] = hash
        timestamp = datetime.utcnow()
        extracted_json['timestamp'] = timestamp

        return extracted_json

    def process_batch(self, source_paths, db_name=None, num_threads=os.cpu_count() - 1):
        if db_name is None:
            db_name = self.config["mongo"]["database"]

        m = Manager()
        num_threads_process = num_threads
        num_threads_store = math.ceil(num_threads / 2)
        queue_input = m.Queue(maxsize=num_threads_process)
        queue_output = m.Queue(maxsize=num_threads_store)
        queue_status = m.Queue(maxsize=num_threads_store)
        print("Processing ", len(source_paths), " files using ", num_threads_process, "/", num_threads_store,
              "for process/store on mongodb.")

        pool_write = multiprocessing.Pool(num_threads_store, self.write_mongo_single, (queue_output, db_name,))
        pool_logger = multiprocessing.Pool(num_threads_store, self.write_mongo_status,
                                           (queue_status, db_name, 'extraction',))
        pool_process = multiprocessing.Pool(num_threads_process, self.process_batch_single,
                                            (queue_input, queue_output, queue_status,))

        for source_path in source_paths:
            queue_input.put(source_path, block=True)

        queue_input.put(None)
        pool_process.close()
        pool_process.join()

        queue_output.put(None)
        pool_write.close()
        pool_write.join()

        queue_status.put(None)
        pool_logger.close()
        pool_logger.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract superconductor materials and properties and save them on MongoDB - extraction")
    parser.add_argument("--input", help="Input directory", type=Path, required=True)
    parser.add_argument("--config", help="Configuration file", type=Path, required=True)
    parser.add_argument("--num-threads", "-n", help="Number of concurrent processes", type=int, default=2,
                        required=False)
    parser.add_argument("--database", "-db",
                        help="Force the database name which is normally read from the configuration file", type=str,
                        default="supercon_dev")

    args = parser.parse_args()

    input_path = args.input
    num_threads = args.num_threads
    config_path = args.config
    db_name = args.database

    if not os.path.exists(config_path):
        print("The config file does not exists. ")
        parser.print_help()
        sys.exit(-1)

    if not os.path.isdir(input_path):
        print("The input should be a directory")
        parser.print_help()
        sys.exit(-1)

    processor_ = MongoSuperconProcessor(config_path)
    pdf_files = []
    for root, dirs, files in os.walk(input_path):
        for file_ in files:
            if not file_.lower().endswith(".pdf"):
                continue

            abs_path = os.path.join(root, file_)
            pdf_files.append(abs_path)

    processor_.process_batch(pdf_files, num_threads=num_threads)

    # print("Finishing!")
