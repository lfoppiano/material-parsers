# Script to extract superconductor and materials name from PDFs
import argparse
import csv
import json
import os
import sys
from pathlib import Path

from grobid_client_generic import grobid_client_generic

header_row = ["Raw material", "Name", "Formula", "Doping", "Shape", "Class", "Fabrication", "Substrate",
              "Critical temperature", "Applied pressure", "Link type", "Section", "Subsection", "Sentence",
              'path', 'filename']


def decode(response_string):
    try:
        return json.loads(response_string)
    except ValueError as e:
        return "Value error: " + str(e)
    except TypeError as te:
        return "Type error: " + str(te)


def process_file(grobid_client, source_path, format: str, task="processPDF"):
    print("Processing file " + str(source_path))
    accept_header_value = "application/json" if format == 'json' else "text/csv"

    r, error_code = grobid_client.process_pdf(str(source_path), task, headers={"Accept": accept_header_value})
    if r is None:
        print("Response is empty or without content for " + str(source_path) + ". Moving on. ")
        return []
        # raise Exception("Response is None for " + str(source_path) + ". Moving on. ")
    else:
        if format == 'json':
            output = json.loads(r)
        else:
            output = [row for row in csv.reader(r.split("\n")) if len(row) > 0]

    return output


def write_data(output_path, data, format):
    with open(output_path, 'w') as f:
        if format == 'json':
            json.dump(data, f)
        else:
            delimiter = ',' if format == 'csv' else '\t'
            writer = csv.writer(f, delimiter=delimiter, quotechar='"', quoting=csv.QUOTE_ALL)
            for row in data:
                writer.writerow(row)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract superconductor materials and properties in CSV/TSV/JSON")

    parser.add_argument("--input", help="Input file or directory", type=Path, required=True)
    parser.add_argument("--output", help="Output directory", type=Path, required=True)
    parser.add_argument("--config", help="Config file", type=Path, required=False, default='./config.json')
    parser.add_argument("--recursive", action="store_true", default=False,
                        help="Process input directory recursively. If input is a file, this parameter is ignored.")
    parser.add_argument("--format", default='csv', choices=['tsv', 'csv', 'json'],
                        help="Output format.")
    parser.add_argument("--task", default='processPDF', choices=['processPDF', 'processPDF_disableLinking'],
                        help="Tasks to be executed.")

    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    recursive = args.recursive
    format = args.format
    config = args.config
    task = args.task

    grobid_client = grobid_client_generic(config_path=config)

    if os.path.isdir(input_path):
        if not os.path.isdir(output_path):
            print("--output should specify always a directory")
            sys.exit(-1)
        path_list = []

        if recursive:
            for root, dirs, files in os.walk(input_path):
                # Manage to create the directories
                for dir in dirs:
                    abs_path_dir = os.path.join(root, dir)
                    abs_output_path = abs_path_dir.replace(str(input_path), str(output_path))
                    if not os.path.exists(abs_output_path):
                        os.makedirs(abs_output_path)

                for file_ in files:
                    if not file_.lower().endswith(".pdf"):
                        continue

                    abs_path = os.path.join(root, file_)
                    output_filename = Path(abs_path).stem
                    parent_dir = Path(abs_path).parent
                    if os.path.isdir(output_path):
                        output_ = Path(str(parent_dir).replace(str(input_path), str(output_path)))
                        output_filename_with_extension = str(output_filename) + '.' + format
                        output_path_with_filename_and_extension = os.path.join(output_, output_filename_with_extension)
                        # else:
                        #     output_path = os.path.join(parent_dir, output_filename + ".tei.xml")

                        path_list.append((Path(abs_path), output_path_with_filename_and_extension))

        else:
            path_list = Path(input_path).glob('*.pdf')

        # output_data = []
        for input_file_path, output_file_path in path_list:
            extracted_data = process_file(grobid_client, input_file_path, format, task=task)
            # output_data.extend(file_data)
            # write_rows(output_file_path, header_row)
            if len(extracted_data) > 0:
                write_data(output_file_path, extracted_data, format)

    elif os.path.isfile(input_path):
        extracted_data = process_file(grobid_client, input_path, format, task=task)
        output_filename = os.path.join(output_path, input_path.stem + "." + format)

        # write_rows(output_filename, header_row)
        write_data(output_filename, extracted_data, format)
