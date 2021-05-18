import argparse
import json
import math
import multiprocessing
import os
import sys
from datetime import datetime
from pathlib import Path

from supercon_batch_mongo_extraction import connect_mongo, MongoSuperconProcessor
from utils import json_serial


class MongoTabularProcessor(MongoSuperconProcessor):
    grobid_client = None
    config = {}

    def __init__(self, config_path, force=False):
        super(MongoTabularProcessor, self).__init__(config_path)
        self.force = force

    def prepare_document(self, document):
        del document['pages']
        del document['_id']
        for para in document['paragraphs'] if 'paragraphs' in document else []:
            for span in para['spans'] if 'spans' in para else []:
                if 'boundingBoxes' in span:
                    del span['boundingBoxes']
            if 'tokens' in para:
                del para['tokens']
        return document

    def process_json_single(self):
        connection = connect_mongo(config=self.config)
        db = connection[self.db_name]
        tabular_collection = db.get_collection("tabular")

        while True:
            data = self.queue_input.get(block=True)
            if data is None:
                print("Got termination. Shutdown processor.")
                self.queue_input.put(None)
                break

            raw_json = data[0]
            hash = data[1]
            timestamp = data[2]

            preprocessed_json = self.prepare_document(raw_json)
            biblio_data = preprocessed_json['biblio'] if 'biblio' in preprocessed_json else {}

            r, status = self.grobid_client.process_json(json.dumps(preprocessed_json, default=json_serial),
                                                        "processJson")
            if r is not None:
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

            self.queue_status.put(
                {'hash': hash, 'timestamp_doc': timestamp, 'status': status, 'timestamp': datetime.utcnow()},
                block=True)

    def process_json_batch(self):
        connection = connect_mongo(config=self.config)
        db_supercon_dev = connection[self.db_name]
        document_collection = db_supercon_dev.get_collection("document")
        tabular_collection = db_supercon_dev.get_collection("tabular")

        total_documents = len(document_collection.distinct("hash"))
        processed_documents = len(tabular_collection.distinct("hash"))

        print("Document to process:", (total_documents - processed_documents))

        # cursor = db_supercon_dev.find({}, {"hash": 1}).distinct()
        cursor_aggregation = document_collection.aggregate(
            [{"$sort": {"hash": 1, "timestamp": 1}}, {"$group": {"_id": "$hash", "lastDate": {"$last": "$timestamp"}}}])

        for item in cursor_aggregation:
            # We skip data that has been already extracted
            if not self.force:
                tabular_entry = tabular_collection.find_one({"hash": item['_id']}, {"hash": 1})
                if tabular_entry:
                    continue

            document = document_collection.find_one({"hash": item['_id'], "timestamp": item['lastDate']})
            if 'paragraphs' not in document:
                continue
            self.queue_input.put((document, item['_id'], item['lastDate']))

        self.tear_down_batch_processes()

    def setup_batch_processes(self, db_name=None, num_threads=os.cpu_count() - 1, only_failed=False):
        if db_name is None:
            self.db_name = self.config["mongo"]["database"]
            print(self.config)

        num_threads_process = num_threads
        num_threads_store = math.ceil(num_threads / 2) if num_threads > 1 else 1
        self.queue_input = self.m.Queue(maxsize=num_threads_process)
        self.queue_status = self.m.Queue(maxsize=num_threads_store)

        print("Processing files using ", num_threads_process, "/", num_threads_store,
              "for process/store on mongodb.")

        self.pool_process = multiprocessing.Pool(num_threads_process, self.process_json_single, ())
        self.pool_status = multiprocessing.Pool(num_threads_process, self.write_mongo_status,
                                                (self.db_name, 'table_compute',))

        self.process_only_failed = only_failed

        return self.pool_process, self.queue_status, self.pool_status

    def tear_down_batch_processes(self):
        self.queue_input.put(None)
        self.pool_process.close()
        self.pool_process.join()

        self.queue_status.put(None)
        self.pool_logger.close()
        self.pool_logger.join()

    def get_queue_input(self):
        return self.queue_input


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Process extracted documents and compute the tabular format.")
    parser.add_argument("--config", help="Configuration file", type=Path, required=True)
    parser.add_argument("--num-threads", "-n", help="Number of concurrent processes", type=int, default=2,
                        required=False)
    parser.add_argument("--database", "-db",
                        help="Set the database name which is normally read from the configuration file", type=str,
                        required=False)
    parser.add_argument("--force", "-f", help="Re-process all the records and replace existing one. ", default=False)

    args = parser.parse_args()
    config_path = args.config
    num_threads = args.num_threads
    db_name = args.database
    force = args.force

    if not os.path.exists(config_path):
        print("The config file does not exists. ")
        parser.print_help()
        sys.exit(-1)

    processor = MongoTabularProcessor(config_path=config_path, force=force)
    processor.setup_batch_processes(num_threads=num_threads, db_name=db_name)

    processor.process_json_batch()
