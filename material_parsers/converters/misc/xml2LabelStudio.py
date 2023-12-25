# transform XML Tei to TSV for WebAnno
import argparse
import json
import os
from collections import OrderedDict
from pathlib import Path

from material_parsers.commons.grobid_tokenizer import tokenizeSimple
from material_parsers.converters.misc.xml2LossyJSON import process_file


def tokenise(string):
    return tokenizeSimple(string)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converter from XML (Grobid training data based on TEI) to the Label Studio JSON format")

    parser.add_argument("--input", help="Input file or directory", required=True)
    parser.add_argument("--output", default=None,
                        help="Output directory (if omitted, the output will be the same directory/file with different extension)")
    parser.add_argument("--recursive", action="store_true", default=False,
                        help="Process input directory recursively. If input is a file, this parameter is ignored. ")

    args = parser.parse_args()

    input = args.input
    output = args.output
    recursive = args.recursive

    if os.path.isdir(input):
        input_path_list = []
        output_path_list = []

        if recursive:
            for root, dirs, files in os.walk(input):
                for dir in dirs:
                    abs_path_dir = os.path.join(root, dir)
                    output_path = abs_path_dir.replace(str(input), str(output))
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)

                    for file_ in files:
                        if not file_.lower().endswith(".xml"):
                            continue

                        abs_path = os.path.join(root, file_)
                        input_path_list.append(abs_path)
                        output_path_list.append(os.path.join(output_path, file_.replace(".xml", ".json")))

        else:
            input_path_list = list(Path(input).glob('*.tei.xml'))
            output_path_list = [str(input_path).replace(str(input), str(output)).replace(".xml", ".json") for input_path
                                in input_path_list]

        for path in input_path_list:
            print("Processing: ", path)
            output_filename = Path(path).stem
            output_filename = output_filename.replace(".tei", "")
            parent_dir = Path(path).parent

            if os.path.isdir(str(output)):
                output_path = os.path.join(output, str(output_filename) + ".json")
            else:
                output_path = os.path.join(parent_dir, output_filename + ".json")

            output_document = process_file(str(path))

            new_format = []

            for sentence in output_document['paragraphs']:
                sentence_structure = OrderedDict()
                sentence_structure['data'] = {
                    "text": sentence['text']
                }
                sentence_structure['predictions'] = [
                    {
                        'model_version': '1',
                        'result': [
                            {'id': id_,
                             'from_name': 'label',
                             'to_name': 'text',
                             'type': 'labels',
                             'value': {'start': spans['offset_start'], 'end': spans['offset_end'],
                                       'text': spans['text'],
                                       'labels': [spans['type'].replace('<', '').replace('>', '')]}
                             } for id_, spans in enumerate(sentence['spans'] if 'spans' in sentence else [])
                        ]
                    }
                ]

                new_format.append(sentence_structure)

            with open(output_path, 'w') as fp:
                json.dump(new_format, fp)

    elif os.path.isfile(input):
        input_path = Path(input)
        output_filename = input_path.stem + ".json"
        output_document = process_file(input_path)
        with open(output_filename, 'w') as fp:
            json.dump(output_document, fp)
