import argparse
import json
import multiprocessing
import os
import sys
from multiprocessing import Manager
from pathlib import Path

from grobid_client_generic import grobid_client_generic

from supercon.controller import json_serial
from supercon.process.supercon_batch_mongo_extraction import connect_mongo, MongoSuperconProcessor


class MongoTabularProcessor():
    grobid_client = None
    config = {}

    def __init__(self, config_path):
        config_json = open(config_path).read()
        self.config = json.loads(config_json)
        self.grobid_client = grobid_client_generic(config=self.config)
        self.grobid_client.ping_grobid()

    def prepare_document(self, document):
        del document['pages']
        del document['_id']
        for para in document['paragraphs']:
            for span in para['spans'] if 'spans' in para else []:
                if 'boundingBoxes' in span:
                    del span['boundingBoxes']
            if 'tokens' in para:
                del para['tokens']
        return document

    def process_json_single(self, queue_json, queue_status, db_name):
        connection = connect_mongo(config=self.config)
        db = connection[db_name]
        tabular_collection = db.get_collection("tabular")

        while True:
            data = queue_json.get(block=True)
            if data is None:
                print("Got termination. Shutdown processor.")
                queue_json.put(None)
                break

            raw_json = data[0]
            hash = data[1]
            timestamp = data[2]

            preprocessed_json = self.prepare_document(raw_json)
            biblio_data = preprocessed_json['biblio'] if 'biblio' in preprocessed_json else {}

            r, status = self.grobid_client.process_json(json.dumps(preprocessed_json, default=json_serial), "processJson")
            if r is None:
                print("Response is empty or without content for TBD. Moving on. ")
            else:
                aggregated_entries = r
                json_aggregated_entries = json.loads(aggregated_entries)
                for ag_e in json_aggregated_entries:
                    ag_e['hash'] = hash
                    ag_e['timestamp'] = timestamp
                    ag_e['type'] = 'automatic'
                    for item in ['doi', 'authors', 'publisher', 'journal', 'year']:
                        ag_e[item] = biblio_data[item] if item in biblio_data else ""

                # We remove the previous version of the same data
                tabular_collection.delete_many({"hash": hash})
                tabular_collection.insert_many(json_aggregated_entries)
            queue_status.put({'hash': hash, 'timestamp': timestamp, 'status': status}, block=True)

    def process_json_batch(self):
        connection = connect_mongo(config=self.config)
        db_name = self.config['mongo']['database']
        db_supercon_dev = connection[db_name]
        document_collection = db_supercon_dev.get_collection("document")

        m = Manager()
        num_threads_process = num_threads - 1
        queue_input = m.Queue(maxsize=num_threads_process)
        queue_status = m.Queue(maxsize=num_threads_process)
        print("Processing documents using", num_threads_process, "processes. ")

        pool_process = multiprocessing.Pool(num_threads_process, self.process_json_single, (queue_input, queue_status, db_name,))
        pool_status = multiprocessing.Pool(num_threads_process, MongoSuperconProcessor(config_path=config_path).write_mongo_status, (queue_status, db_name, 'aggregation', ))

        # cursor = db_supercon_dev.find({}, {"hash": 1}).distinct()
        cursor_aggregation = document_collection.aggregate(
            [{"$sort": {"hash": 1, "timestamp": 1}}, {"$group": {"_id": "$hash", "lastDate": {"$last": "$timestamp"}}}])

        for item in cursor_aggregation:
            document = document_collection.find_one({"hash": item['_id'], "timestamp": item['lastDate']})
            queue_input.put((document, item['_id'], item['lastDate']))

        queue_input.put(None)
        pool_process.close()
        pool_process.join()

        queue_status.put(None)
        pool_status.close()
        pool_status.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract superconductor materials and properties and save them on mongodb - extraction")
    parser.add_argument("--config", help="Configuration file", type=Path, required=True)
    parser.add_argument("--num-threads", "-n", help="Number of concurrent processes", type=int, default=2,
                        required=False)

    args = parser.parse_args()
    config_path = args.config
    num_threads = args.num_threads

    if not os.path.exists(config_path):
        print("The config file does not exists. ")
        parser.print_help()
        sys.exit(-1)

    MongoTabularProcessor(config_path=config_path).process_json_batch()
