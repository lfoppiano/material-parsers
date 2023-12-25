# transform XML Tei TEXT where each paragraph is on line
import argparse
import os
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

from material_parsers.commons.supermat_tei_parser import get_children_list


def get_paragraphs(finput):
    with open(finput, encoding='utf-8') as fp:
        doc = fp.read()

    mod_tags = re.finditer(r'(</\w+>) ', doc)
    for mod in mod_tags:
        doc = doc.replace(mod.group(), ' ' + mod.group(1))
    #     print(doc)
    soup = BeautifulSoup(doc, 'xml')

    children = get_children_list(soup)

    paragraphs = []

    for child in children:
        for pTag in child:
            paragraphText = ''
            for item in pTag.contents:
                if type(item) == NavigableString:
                    paragraphText += str(item)

                elif type(item) is Tag and item.name == 'rs':
                    paragraphText += item.text

            paragraphs.append(paragraphText)

    return paragraphs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converter XML (Grobid training data based on TEI) to Text files. ")

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
        path_list = []

        if recursive:
            for root, dirs, files in os.walk(input):
                for file_ in files:
                    if not file_.lower().endswith(".xml"):
                        continue

                    abs_path = os.path.join(root, file_)
                    path_list.append(abs_path)

        else:
            path_list = Path(input).glob('*.tei.xml')

        for path in path_list:
            print("Processing: ", path)
            output_filename = Path(path).stem
            output_filename = output_filename.replace(".tei", "").replace(".superconductors", "")
            parent_dir = Path(path).parent

            if os.path.isdir(str(output)):
                output_path = os.path.join(output, str(output_filename) + ".txt")
            else:
                output_path = os.path.join(parent_dir, output_filename + ".txt")

            paragraphs = get_paragraphs(str(path))
            with open(output_path, 'w') as fo:
                fo.write('\n'.join(paragraphs))


    elif os.path.isfile(input):
        input_path = Path(input)
        data = get_paragraphs(input_path)
        output_filename = input_path.stem
        paragraphs = get_paragraphs(str(input_path))

        with open(os.path.join(output, str(output_filename) + ".txt"), 'w') as fo:
            fo.writelines(paragraphs)
