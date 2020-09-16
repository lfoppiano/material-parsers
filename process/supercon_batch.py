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
    output_materials = []
    output_links = []
    output = {
        'sourcepath': str(source_path),
        'filename': source_path.name,

        # material, material formatted
        'materials': output_materials,

        # material, tc, sentence
        'links': output_links
    }

    print("Processing file " + str(source_path))

    r = grobid_client.process_pdf(str(source_path), "processPDF")
    if r is None:
        raise Exception("Response is None for " + str(source_path) + ". Moving on. ")
    jsonOut = decode(r)

    if 'paragraphs' not in jsonOut:
        return

    for sentence in jsonOut['paragraphs']:

        if 'spans' not in sentence:
            continue

        materials_spans = [item['text'] for item in sentence['spans'] if
                           'type' in item and (item['type'] == '<material>')]
        if len(materials_spans) > 0:
            output_materials.extend(materials_spans)

        output_rows = []
        sentence_text = sentence['text']

        for relationship in sentence['relationships'] if 'relationships' in sentence else []:
            # collect relationships

            materials = [item for item in relationship if
                         'type' in item and (item['type'] == 'material-tc')]

            material = materials[0] if len(materials) > 0 else None

            tcValues = [item for item in relationship if
                        'type' in item and (item['type'] == 'temperature-tc')]

            tcValue = tcValues[0] if len(tcValues) > 0 else None

            output_rows.append([material['text'], tcValue['text'], sentence_text])
        if len(output_rows) > 0:
            output_links.extend(output_rows)

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

    write_footer(output_directory)


def write_header(output_directory):
    with open(output_directory + "/output.complete.json", 'w') as f:
        f.write('[\n')

    with open(output_directory + '/output.materials.csv', 'w') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(['material'])

    with open(output_directory + '/output.supercon.csv', 'w') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(['material', 'tc', 'sentence', 'path', 'filename'])


def write_footer(output_directory):
    with open(output_directory + "/output.complete.json", 'a') as f:
        f.write("]")


def write_on_files(output, output_directory, append=False):
    write_mode = 'a' if append else 'w'
    with open(output_directory + "/output.complete.json", write_mode) as f:
        f.write(json.dumps(output))

    with open(output_directory + '/output.materials.csv', write_mode) as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        for material in output['materials']:
            writer.writerow([material])

    with open(output_directory + '/output.supercon.csv', write_mode) as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        for links in output['links']:
            writer.writerow(links + [output['sourcepath']] + [output['filename']])


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
