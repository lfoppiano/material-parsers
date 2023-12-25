# transform XML Tei to JSONL
import argparse
import json
import os
from pathlib import Path

from material_parsers.commons.grobid_tokenizer import tokenizeAndFilterSimple
from material_parsers.commons.supermat_tei_parser import process_file_to_json

def tokenise(string):
    return tokenizeAndFilterSimple(string)


def write_on_file(fw, paragraphText, dic_token, i, item_length):
    # tsvText += f'#Text={paragraphText}\n'
    print(f'#Text={paragraphText}', file=fw)
    for k, v in dic_token.items():
        # print(v)
        if k[0] == i + 1 and v[2]:
            print('{}-{}\t{}-{}\t{}\t{}\t{}\t{}\t{}\t{}\t'.format(*k, *v), file=fw)

    # Avoid adding a line break too much at the end of the file
    if i != item_length - 1:
        print('', file=fw)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converter from XML (Grobid training data based on TEI) to JSONL format")

    parser.add_argument("--input", help="Input file or directory", required=True)
    parser.add_argument("--output", default=None,
                        help="Output directory (if omitted, the output will be the same directory/file with different extension)")
    parser.add_argument("--recursive", action="store_true", default=False,
                        help="Process input directory recursively. If input is a file, this parameter is ignored. ")

    parser.add_argument("--use-paragraphs", action="store_true", default=False, help="Use paragraphs instead of sentences.")

    args = parser.parse_args()

    input = args.input
    output = args.output
    recursive = args.recursive
    use_paragraphs = args.use_paragraphs

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

            output_document = process_file_to_json(str(path), use_paragraphs)
            with open(output_path, 'w') as fp:
                json.dump(output_document, fp)
                fp.write("\n")

    elif os.path.isfile(input):
        input_path = Path(input)
        output_filename = input_path.stem + ".json"
        output_document = process_file_to_json(input_path, use_paragraphs)
        with open(os.path.join(output, output_filename), 'w') as fp:
            json.dump(output_document, fp)
            fp.write("\n")
