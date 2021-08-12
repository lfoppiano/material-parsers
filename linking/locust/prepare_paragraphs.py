import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from data_model import to_dict_token
from src.materialparserwrapper.linking.data_model import to_dict_span
from supermat_tei_parser import tokenise


def generate_tokens(text, spans):
    off_token = 0
    token_list = tokenise(text)
    tokens = []
    updated_spans = []
    for token in token_list:
        token_as_json = to_dict_token(token, off_token)
        off_token += len(token)
        tokens.append(token_as_json)

    for span in spans:
        span_tokens = list(filter(lambda t: span['offset_start'] <= t['offset'] < span['offset_end'], tokens))
        new_span = to_dict_span(span['text'], span['type'], span['id'], span['offset_start'], span['offset_end'],
                                tokens.index(span_tokens[0]), tokens.index(span_tokens[-1]))

        updated_spans.append(new_span)

    return tokens, updated_spans


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract superconductor materials and properties in JSON")

    parser.add_argument("--input", help="Input file or directory", type=Path, required=True)
    parser.add_argument("--output", help="Output directory", type=Path, required=True)
    parser.add_argument("--recursive", action="store_true", default=False,
                        help="Process input directory recursively. If input is a file, this parameter is ignored.")

    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    recursive = args.recursive

    if not os.path.isdir(input_path):
        print("--input should specify always a directory")
        sys.exit(-1)

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
                if not file_.lower().endswith(".json"):
                    continue

                abs_path = os.path.join(root, file_)
                output_filename = Path(abs_path).stem
                parent_dir = Path(abs_path).parent
                if os.path.isdir(output_path):
                    output_ = Path(str(parent_dir).replace(str(input_path), str(output_path)))
                    output_filename_with_extension = str(output_filename) + '.json'
                    output_path_with_filename_and_extension = os.path.join(output_, output_filename_with_extension)
                    path_list.append((Path(abs_path), output_path_with_filename_and_extension))

    else:
        path_list = Path(input_path).glob('*.json')

    # output_data = []
    for input_file_path, output_file_path in path_list:
        print(input_file_path)
        with open(input_file_path, 'r') as f:
            input_data_json = json.load(f)

            paragraphs = input_data_json['paragraphs'] if 'paragraphs' in input_data_json else []

            paragraphs_with_spans = list(filter(lambda p: 'spans' in p, paragraphs))
            for para in paragraphs_with_spans:

                for span in para['spans']:
                    if 'links' in span:
                        del span['links']
                    if 'boundingBoxes' in span:
                        del span['boundingBoxes']
                    if 'id' not in span:
                        span['id'] = uuid.uuid4().hex

                tokens, spans = generate_tokens(para['text'], para['spans'])
                para['spans'] = spans
                para['tokens'] = tokens

            with open(output_file_path, 'w') as fo:
                json.dump(paragraphs_with_spans, fo)
