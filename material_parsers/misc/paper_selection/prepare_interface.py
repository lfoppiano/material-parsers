# Script to extract superconductor and materials name from PDFs
import argparse
import csv
import json
import os
import traceback
from pathlib import Path

from grobid_client_generic import grobid_client_generic
from grobid_tokenizer import tokenizeAndFilterSimple

grobid_client = grobid_client_generic(config_path='./config.json')


def decode(response_string):
    try:
        return json.loads(response_string)
    except ValueError as e:
        return "Value error: " + str(e)
    except TypeError as te:
        return "Type error: " + str(te)


def process_file(source_path, type="pdf", force=False):
    output = {
        'sourcepath': str(source_path),
        'filename': source_path.name
    }

    print("Processing file " + str(source_path))

    response = '{}'
    if type == 'pdf':
        superconductors_json_file = str(source_path).replace(".pdf", ".superconductors.json")
        if os.path.exists(superconductors_json_file) and force is False:
            print("The file ", superconductors_json_file, "exists already. Skipping.")
            with open(superconductors_json_file, 'r') as f:
                jsonOut = json.load(f)
        else:
            response = grobid_client.process_pdf(str(source_path), "processPDF_noLinking")
            if response is None:
                raise Exception("Response is None for " + str(source_path) + ". Moving on. ")
            jsonOut = decode(response)

            with open(superconductors_json_file, 'w') as fff:
                json.dump(jsonOut, fff)

    else:
        with open(source_path, 'r') as f:
            jsonOut = json.load(f)

    if 'paragraphs' not in jsonOut:
        return

    output['title'] = ""
    output['abstract'] = ""
    output['keywords'] = ""
    output['nb_tokens'] = 0
    output['nb_spans'] = 0
    output['nb_paragraphs'] = len(jsonOut['paragraphs'])

    for sentence in jsonOut['paragraphs']:

        output['nb_spans'] += len(sentence['spans']) if 'spans' in sentence else 0

        if 'subSection' in sentence and sentence['subSection'] == '<abstract>':
            output['abstract'] += sentence['text']

        if 'subSection' in sentence and sentence['subSection'] == '<title>':
            output['title'] += sentence['text']

        if 'subSection' in sentence and sentence['subSection'] == '<keywords>':
            output['keywords'] += sentence['text']

        output['nb_tokens'] += len(tokenizeAndFilterSimple(sentence['text']))

    output['entity_per_paragraphs'] = output['nb_spans'] / output['nb_paragraphs'] if output['nb_paragraphs'] != 0 else 0
    output['entity_per_tokens'] = output['nb_tokens']/output['nb_spans']  if output['nb_spans'] != 0 else 0

    return output


def process_directory(source_directory, output_directory, type="pdf", force=False):
    output = []
    for root, dirs, files in os.walk(source_directory):
        for file_ in files:
            if not file_.lower().endswith("." + type):
                continue

            abs_path = os.path.join(root, file_)
            try:
                aggregated_data = process_file(Path(abs_path), type, force)
            except Exception as e:
                print("Something went wrong. Skipping " + str(abs_path) + ". ", e)
                traceback.print_exc()
                continue

            aggregated_data['sourcepath'] = os.path.relpath(aggregated_data['sourcepath'],
                                                            Path(output_directory).absolute()) \
                .replace(".json", ".pdf").replace("jsons/", "pdfs/")

            aggregated_data['link'] = "=HYPERLINK(\"http://falcon.nims.go.jp/paper_selection/" + aggregated_data['sourcepath'] + "\", \""+aggregated_data['filename']+"\")"

            aggregated_data['filename'] = aggregated_data['filename'].replace(".json", "")

            output.append(aggregated_data)
    return output


def write_header(output_directory):
    with open(output_directory + '/output.tsv', 'w') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(['filename', 'classes'])


def write_on_files(output, output_directory, append=False):
    write_mode = 'a' if append else 'w'
    with open(output_directory + '/output.tsv', write_mode) as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow([output['filename'], output['classes_dist']])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Prepare the interface to evaluate papers")

    parser.add_argument("--input", help="Input file or directory")
    parser.add_argument("--output", required=True,
                        help="Output directory (if omitted, the output will be the same directory/file with different extension)")
    parser.add_argument("--type", default="pdf", choices=['pdf', 'json'],
                        help="Type of processing: pdf through grobid-superconductors) or json pre-extracted files")
    parser.add_argument("--force", default=False, required=False,
                        help="Force reprocessing PDFS for which the JSON is already present.")

    args = parser.parse_args()

    input = args.input
    output = args.output
    type = args.type
    force = args.force

    # input directory
    if os.path.isdir(input):
        input_path = Path(input)
        content = process_directory(input_path, output, type, force)

        delimiter = '\t'
        fw = csv.writer(open(output + '/output.tsv', encoding='utf-8', mode='w'), delimiter=delimiter, quotechar='"')
        columns = ['filename', 'link', 'title', 'abstract', 'keywords', 'entity_per_paragraphs', 'entity_per_tokens']
        fw.writerow(columns)
        for d in content:
            fw.writerow([d[c] if c in d else '' for c in columns])

        with open(output + '/output.json', 'w') as f:
            json.dump(content, f)

    else:
        parser.print_help()
