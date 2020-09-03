# Script to extract superconductor and materials name from PDFs
import csv
import json
import os
import sys
from pathlib import Path

from grobid_client_generic import grobid_client_generic

grobid_client = grobid_client_generic(config_path='./config.json')


def decode(response_string):
    try:
        return json.loads(response_string)
    except ValueError as e:
        return "Value error: " + str(e)
    except TypeError as te:
        return "Type error: " + str(te)


def process_file(source_path):
    print("Processing file " + str(source_path))

    r = grobid_client.process_pdf(str(source_path), "processPDF", headers={"Accept": "text/csv"})
    if r is None:
        raise Exception("Response is None for " + str(source_path) + ". Moving on. ")
    output = []
    header = True
    for row in csv.reader(r.split("\n")):
        if header:
            header = False
            continue
        if len(row) > 0:
            output.append(row + [source_path] + [source_path.name])

    return output


def process_directory(source_directory, output_directory):
    # xdir = Path('/data/workspace/Suzuki/supercon_files_20190808/iop/data/')
    # xmlfiles = [x for x in xdir.glob('**/*.xml')]
    # pdffiles = [x for x in xdir.glob('**/*.pdf')]
    write_header(output_directory)
    for root, dirs, files in os.walk(source_directory):
        for file_ in files:
            if not file_.lower().endswith(".pdf"):
                continue

            abs_path = os.path.join(root, file_)
            try:
                output = process_file(Path(abs_path))
            except Exception as e:
                print("Something went wrong. Skipping. " + str(e))
                continue

            write_on_files(output, output_directory, append=True)



def write_header(output_directory):
    with open(output_directory + '/output.supercon.csv', 'w') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(['Raw material', 'name', 'formula', 'doping', 'shape', 'class', 'critical temperature', 'applied pressure', 'link type', 'sentence', 'path', 'filename'])


def write_on_files(output, output_directory, append=False):
    write_mode = 'a' if append else 'w'

    with open(output_directory + '/output.supercon.csv', write_mode) as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerows(output)


if __name__ == '__main__':
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Invalid parameters. Usage: python supercon_batch.py source output_directory. "
              "The source can be either a directory or a file. ")
        sys.exit(-1)

    # input directory
    input = sys.argv[1]
    output = None
    if len(sys.argv) == 3:
        output = sys.argv[2]

    if os.path.isdir(input):
        if output is None:
            print("When specified a source directory, is mandatory to specify an output directory too. ")
            exit(-1)
        input_path = Path(input)
        process_directory(input_path, output)

    elif os.path.isfile(input):
        input_path = Path(input)
        content = process_file(input_path)

        if output is None:
            print(content)
        else:
            write_header(output)
            write_on_files(content, output, append=True)
