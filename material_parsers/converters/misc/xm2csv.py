import argparse
import csv
import os
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from material_parsers.commons.grobid_tokenizer import tokenizeAndFilterSimple
from material_parsers.commons.supermat_tei_parser import get_children_list, get_relationship_name, process_file, \
    process_file_to_json


def write_on_file(fw, filename, sentenceText, dic_token):
    links = len([token for token in dic_token if token[5] != '_'])
    has_links = 0 if links == 0 else 1
    fw.writerow([filename, sentenceText, has_links])


def tokenise(string):
    return tokenizeAndFilterSimple(string)


def write_output(data, output_path, format):
    delimiter = '\t' if format == 'tsv' else ','
    fw = csv.writer(open(output_path, encoding='utf-8', mode='w'), delimiter=delimiter, quotechar='"', quoting=csv.QUOTE_ALL)
    fw.writerows(data)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converter XML (Supermat) to a tabular values (CSV, TSV)")

    parser.add_argument("--input", help="Input file or directory", required=True)
    parser.add_argument("--output", help="Output directory", required=True)
    parser.add_argument("--recursive", action="store_true", default=False,
                        help="Process input directory recursively. If input is a file, this parameter is ignored.")
    parser.add_argument("--format", default='csv', choices=['tsv', 'csv'],
                        help="Output format.")
    parser.add_argument("--use-paragraphs", action="store_true", default=False, help="Use paragraphs instead of sentences.")

    args = parser.parse_args()

    input = args.input
    output = args.output
    recursive = args.recursive
    format = args.format
    use_paragraphs = args.use_paragraphs

    if os.path.isdir(input):
        path_list = []

        if recursive:
            for root, dirs, files in os.walk(input):
                for file_ in files:
                    if not file_.lower().endswith(".xml"):
                        continue

                    abs_path = os.path.join(root, file_)
                    path_list.append(abs_path)

        else:
            path_list = Path(input).glob('*.xml')

        data = []
        global_idx = 0
        for path in path_list:
            print("Processing: ", path)
            parsed_file = process_file_to_json(path, use_paragraphs=use_paragraphs)
            count_entities = [sum(1 for x in w if len(x)>0) for w in parsed_file['ner']]
            for i, paragraph in enumerate(parsed_file['sentences']):
                text = "".join(paragraph)
                is_relevant = "1" if count_entities[i] > 0 else "0"
                data.append([global_idx, text, is_relevant])
                global_idx+=1

        if os.path.isdir(str(output)):
            output_path = os.path.join(output, "output") + "." + format
        else:
            parent_dir = Path(output).parent
            output_path = os.path.join(parent_dir, "output." + format)

        write_output(data, output_path, format)

    elif os.path.isfile(input):
        input_path = Path(input)
        data = process_file_to_json(input_path, use_paragraphs=use_paragraphs)
        output_filename = input_path.stem

        write_output(data, os.path.join(output, str(output_filename) + "." + format), format)
