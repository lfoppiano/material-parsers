# transform XML Tei to TSV for WebAnno
import argparse
import json
import os
import re
from collections import OrderedDict
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag
from grobid_tokenizer import tokenizeSimple
from supermat_tei_parser import getSection


def tokenise(string):
    return tokenizeSimple(string)


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


def process_file(finput):
    with open(finput, encoding='utf-8') as fp:
        doc = fp.read()

    mod_tags = re.finditer(r'(</\w+>) ', doc)
    for mod in mod_tags:
        doc = doc.replace(mod.group(), ' ' + mod.group(1))
    soup = BeautifulSoup(doc, 'xml')

    children = []
    for child in soup.tei.children:
        if child.name == 'teiHeader':
            children.append(child.find_all("title"))
            children.extend([subchild.find_all("p") for subchild in child.find_all("abstract")])
            children.append(child.find_all("ab", {"type": "keywords"}))
        elif child.name == 'text':
            children.append([subsubchild for subchild in child.find_all("body") for subsubchild in subchild.children if
                             type(subsubchild) is Tag])

    off_token = 0
    ient = 1

    # list containing text and the dictionary with all the annotations
    paragraphs = []
    dic_dest_relationships = {}
    dic_source_relationships = {}

    output_document = OrderedDict()
    output_document['lang'] = 'en'
    output_document['level'] = 'paragraph'
    output_document['paragraphs'] = paragraphs

    i = 0
    for child in children:
        for pTag in child:
            paragraph = OrderedDict()
            j = 0
            offset = 0
            section = getSection(pTag)
            paragraph['section'] = section
            paragraph_text = ''
            paragraph['text'] = paragraph_text
            spans = []
            paragraph['spans'] = spans
            tokens = []
            paragraph['tokens'] = tokens
            for item in pTag.contents:
                if type(item) == NavigableString:
                    local_text = str(item)
                    paragraph_text += local_text
                    offset += len(local_text)

                elif type(item) is Tag and item.name == 'rs':
                    local_text = item.text
                    paragraph_text += local_text

                    span = OrderedDict()
                    front_offset = 0
                    if local_text.startswith(" "):
                        front_offset = len(local_text) - len(local_text.lstrip(" "))

                    span['text'] = local_text.strip(" ")
                    span['offset_start'] = offset + front_offset
                    span['offset_end'] = offset + len(span['text']) + front_offset
                    spans.append(span)

                    offset += len(local_text)

                    assert paragraph_text[span['offset_start']:span['offset_end']] == span['text']

                    if 'type' not in item.attrs:
                        raise Exception("RS without type is invalid. Stopping")

                    entity_class = item.attrs['type']
                    span['type'] = entity_class

                    if len(item.attrs) > 0:
                        if 'xml:id' in item.attrs:
                            if item.attrs['xml:id'] not in dic_dest_relationships:
                                dic_dest_relationships[item.attrs['xml:id']] = [i + 1, j + 1, ient, entity_class]

                        if 'corresp' in item.attrs:
                            if (i + 1, j + 1) not in dic_source_relationships:
                                dic_source_relationships[i + 1, j + 1] = [item.attrs['corresp'].replace('#', ''), ient,
                                                                          entity_class]

                    ient += 1  # entity No.

            paragraph['text'] = paragraph_text
            off_token += 1  # return

            paragraphs.append(paragraph)
            i += 1

    return output_document


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converter from XML (Grobid training data based on TEI) to lossy JSON (CORD-19) format")

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
            output_filename = output_filename.replace(".tei", "")
            parent_dir = Path(path).parent

            if os.path.isdir(str(output)):
                output_path = os.path.join(output, str(output_filename) + ".json")
            else:
                output_path = os.path.join(parent_dir, output_filename + ".json")

            output_document = process_file(str(path))
            with open(output_path, 'w') as fp:
                json.dump(output_document, fp)

    elif os.path.isfile(input):
        input_path = Path(input)
        output_filename = input_path.stem + ".json"
        output_document = process_file(input_path)
        with open(output_filename, 'w') as fp:
            json.dump(output_document, fp)
