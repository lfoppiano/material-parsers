import json
import os
import re
import sys
from pathlib import Path
from sys import argv

from bs4 import BeautifulSoup, NavigableString, Tag

from grobid_tokenizer import tokenizeAndFilterSimple


def process_feature_file(finput):
    paragraphs = []
    featureSets = []
    tokens, features = [], []
    with open(finput, encoding='utf-8') as fp:
        for line in fp.readlines():
            line = line.strip(' \t')
            if len(line) == 0 or line == '\n':
                if len(tokens) != 0:
                    paragraphs.append(tokens)
                    featureSets.append(features)
                    tokens, features = [], []
            else:
                pieces = re.split(' |\t', line)
                token = pieces[0]
                localFeatures = pieces[1:len(pieces)]
                tokens.append(token)
                features.append(localFeatures)
            # last sequence
        if len(tokens) != 0:
            paragraphs.append(tokens)
            featureSets.append(features)
    return paragraphs, featureSets


def process_xml_file(finput, root_tag='p'):
    with open(finput, encoding='utf-8') as fp:
        doc = fp.read()

    # mod_tags = re.finditer(r'(</\w+>) ', doc)
    # for mod in mod_tags:
    #     doc = doc.replace(mod.group(), ' ' + mod.group(1))
    #     print(doc)
    soup = BeautifulSoup(doc, 'xml')

    root = None
    for child in soup.tei.children:
        if child.name == 'text':
            root = child

    # list containing text and the dictionary with all the annotations
    paragraphs = []
    texts = []

    for i, pTag in enumerate(root(root_tag)):
        tokens = []
        paragraph_text = ''
        for item in pTag.contents:
            token_list = []
            if type(item) == NavigableString:
                paragraph_text += str(item)
                token_list = tokenizeAndFilterSimple(str(item))

            elif type(item) is Tag:
                paragraph_text += item.text

                token_list = tokenizeAndFilterSimple(item.text)
            tokens.extend(token_list)
        paragraphs.append(tokens)
        texts.append(paragraph_text)

    return paragraphs


def process_dir(source_directory):
    output = {}
    for root, dirs, files in os.walk(source_directory):
        for file_ in files:
            if not file_.lower().endswith(".tei.xml"):
                continue

            skip_file = False

            abs_path = os.path.join(root, file_)

            print(abs_path)

            try:
                paragraphs_from_xml_file = process_xml_file(Path(abs_path))
            except Exception as e:
                print("Something went wrong. Skipping. " + str(e))
                continue

            feature_file_path = abs_path.replace(".tei.xml", ".features.txt")
            try:
                paragraphs_from_feature_file, features = process_feature_file(Path(feature_file_path))
            except Exception as e:
                print("Something went wrong. Skipping. " + str(e))
                continue

            if len(paragraphs_from_feature_file) != len(paragraphs_from_xml_file):
                print("XML " + str(len(paragraphs_from_xml_file)) + " and features " + str(
                    len(paragraphs_from_feature_file)) + " DO NOT have the same amount of paragraphs")

                raise Exception

            for paragraph_index in range(0, len(paragraphs_from_feature_file)):
                paragraph_xml = paragraphs_from_xml_file[paragraph_index]
                paragraph_features = paragraphs_from_feature_file[paragraph_index]

                if len(paragraph_xml) != len(paragraph_features):
                    print("Paragraph " + str(paragraph_index) + " mismatch: \n")
                    print("\t xml, length: " + str(len(paragraph_xml)) + ": " + str(paragraph_xml))
                    print("\t features, length: " + str(len(paragraph_features)) + ": " + str(paragraph_features))

                    for token_index in range(0, len(paragraph_features)):
                        if paragraph_xml[token_index] != paragraph_features[token_index]:
                            print("Token " + paragraph_xml[token_index] + " != " + paragraph_features[token_index])
                            break

    return output


if __name__ == "__main__":
    if len(argv) != 2:
        print("Invalid parameters. Usage: python grobid_training_consistency_check.py input_dir")
        sys.exit(-1)

    input = argv[1]

    output = process_dir(input)

    print(json.dumps(output, indent=4))
