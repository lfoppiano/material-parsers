# transform XML Tei to JSONL
import argparse
import json
import os
import re
from collections import OrderedDict
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

from grobid_superconductors.commons.grobid_tokenizer import tokenizeSimple, tokenizeAndFilterSimple
from grobid_superconductors.commons.supermat_tei_parser import get_children_list, get_section
from grobid_superconductors.converters.misc.xmlSupermat2csv import get_relationship_name


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


def process_file(finput):
    with open(finput, encoding='utf-8') as fp:
        doc = fp.read()

    mod_tags = re.finditer(r'(</\w+>) ', doc)
    for mod in mod_tags:
        doc = doc.replace(mod.group(), ' ' + mod.group(1))
    soup = BeautifulSoup(doc, 'xml')

    children = get_children_list(soup)

    token_offset_sentence = 0
    ient = 1

    # list containing text and the dictionary with all the annotations
    sentences = []
    ner = []
    relations = []

    output_document = OrderedDict()
    output_document['doc_key'] = Path(str(finput)).name
    output_document['dataset'] = 'SuperMat'
    output_document['sentences'] = sentences
    output_document['ner'] = ner
    output_document['relations'] = relations


    i = 0
    for child in children:
        for pTag in child:
            j = 0
            text_sentence = ''
            tokens_sentence = []
            ner_sentence = []
            relations_sentence = []
            dic_dest_relationships = {}
            dic_source_relationships = {}
            linked_entity_registry = {}

            for item in pTag.contents:
                if type(item) == NavigableString:
                    local_text = str(item)
                    text_sentence += local_text

                    token_list = tokenise(item.string)
                    if len(token_list) > 0 and token_list[0] == ' ':  # remove space after tags
                        del token_list[0]

                    tokens_sentence.extend(token_list)
                    token_offset_sentence += len(token_list)

                elif type(item) is Tag and item.name == 'rs':
                    local_text = item.text
                    text_sentence += local_text
                    if 'type' not in item.attrs:
                        raise Exception("RS without type is invalid. Stopping")
                    label = item.attrs['type']
                    token_list = tokenise(local_text)
                    tokens_sentence.extend(token_list)

                    ner_entity = [token_offset_sentence, token_offset_sentence + len(token_list) - 1, label]
                    ner_sentence.append(ner_entity)

                    if len(item.attrs) > 0:
                        ## multiple entities can point ot the same one, so "corresp" value can be duplicated
                        allow_duplicates = False
                        span_id = None
                        if 'xml:id' in item.attrs:
                            span_id = item['xml:id']
                            if item.attrs['xml:id'] not in dic_dest_relationships:
                                dic_dest_relationships[item.attrs['xml:id']] = [i + 1, j + 1, ient, label]

                        if 'corresp' in item.attrs:
                            if span_id is None or span_id == "":
                                id_str = str(i + 1) + "," + str(j + 1)
                                span_id = get_hash(id_str)
                                if span_id not in dic_source_relationships:
                                    dic_source_relationships[span_id] = [item.attrs['corresp'].replace('#', ''),
                                                                         ient,
                                                                         label]
                            else:
                                if span_id not in dic_source_relationships:
                                    dic_source_relationships[span_id] = [item.attrs['corresp'].replace('#', ''),
                                                                         ient,
                                                                         label]

                            allow_duplicates = True

                        if span_id is not None:
                            if span_id not in linked_entity_registry.keys():
                                linked_entity_registry[span_id] = ner_entity
                            else:
                                if not allow_duplicates:
                                    print("The same key exists... something's wrong: ", span_id)

                    token_offset_sentence += len(token_list)

                    j += 1

                ient += 1  # entity No.

            # token_offset_sentence += 1  # return

            sentences.append(tokens_sentence)
            ner.append(ner_sentence)
            i += 1

            for id__ in dic_source_relationships:
                destination_xml_id = dic_source_relationships[id__][0]

                for des in destination_xml_id.split(","):
                    dict_coordinates = get_hash(id__)
                    if des in linked_entity_registry:
                        span_destination = linked_entity_registry[des]
                        span_source = linked_entity_registry[dict_coordinates]

                        relations_sentence.append(
                            [span_destination[0], span_destination[1], span_source[0], span_source[1],
                             get_relationship_name(span_source[2], span_destination[2])])

            relations.append(relations_sentence)

    return output_document


def get_hash(dict_coordinates_str):
    return dict_coordinates_str
    # return hashlib.md5(dict_coordinates_str.encode('utf-8')).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converter from XML (Grobid training data based on TEI) to JSONL format")

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
            with open(output_path, 'w') as fp:
                json.dump(output_document, fp)
                fp.write("\n")

    elif os.path.isfile(input):
        input_path = Path(input)
        output_filename = input_path.stem + ".json"
        output_document = process_file(input_path)
        with open(os.path.join(output, output_filename), 'w') as fp:
            json.dump(output_document, fp)
            fp.write("\n")
