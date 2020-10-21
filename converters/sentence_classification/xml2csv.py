# transform tei to csv for classification
import csv
import os
import re
import sys
from pathlib import Path
from sys import argv

import spacy
from bs4 import BeautifulSoup, NavigableString, Tag

from grobid_tokenizer import tokenizeAndFilterSimple

nlp = spacy.load("en_core_sci_sm", disable=['ner', 'tagger'])


def write_on_file(fw, filename, sentenceText, dic_token):
    links = len([token for token in dic_token if token[5] != '_'])
    has_links = 0 if links == 0 else 1
    fw.writerow([filename, sentenceText, has_links])


def tokenise(string):
    return tokenizeAndFilterSimple(string)


def processFile(finput):
    with open(finput, encoding='utf-8') as fp:
        doc = fp.read()

    mod_tags = re.finditer(r'(</\w+>) ', doc)
    for mod in mod_tags:
        doc = doc.replace(mod.group(), ' ' + mod.group(1))
    #     print(doc)
    soup = BeautifulSoup(doc, 'xml')

    root = None
    for child in soup.tei.children:
        if child.name == 'text':
            root = child

    off_token = 0
    dic_token = {}
    ient = 1

    # list containing text and the dictionary with all the annotations
    paragraphs = []
    dic_dest_relationships = {}
    dic_source_relationships = {}

    for i, pTag in enumerate(root('p')):
        j = 0
        paragraphText = ''
        for item in pTag.contents:
            if type(item) == NavigableString:
                paragraphText += str(item)

                token_list = tokenise(item.string)
                if token_list[0] == ' ':  # remove space after tags
                    del token_list[0]

                entity_class = '_'

                for token in token_list:
                    s = off_token
                    off_token += len(token.rstrip(' '))
                    e = off_token
                    if token.rstrip(' '):
                        dic_token[(i + 1, j + 1)] = [
                            s, e, token.rstrip(' '), entity_class, entity_class, entity_class, entity_class,
                            entity_class]
                        #                     print((i+1, j+1), s, e, [token], len(token.rstrip(' ')), off_token)
                        j += 1
                    if token[-1] == ' ':
                        off_token += 1  #
            elif type(item) is Tag:
                paragraphText += item.text

                token_list = tokenise(item.string)
                #                 token_list[-1] += ' ' # add space the end of tag contents
                entity_class = item.name
                link_name = '_'
                link_location = '_'

                if len(item.attrs) > 0:
                    if 'id' in item.attrs:
                        if item.attrs['id'] not in dic_dest_relationships:
                            dic_dest_relationships[item.attrs['id']] = [i + 1, j + 1, ient, entity_class]

                    if 'ptr' in item.attrs:
                        if (i + 1, j + 1) not in dic_source_relationships:
                            dic_source_relationships[i + 1, j + 1] = [item.attrs['ptr'].replace('#', ''), ient,
                                                                      entity_class]

                    link_name = 'link_name'
                    link_location = 'link_location'

                entity_class = entity_class.replace("_", "\_")

                for token in token_list:
                    s = off_token
                    off_token += len(token.rstrip(' '))
                    e = off_token
                    if token.rstrip(' '):
                        dic_token[(i + 1, j + 1)] = [s, e, token.rstrip(' '), f'*[{ient}]', entity_class + f'[{ient}]',
                                                     link_name, link_location]
                        #                     print((i+1, j+1), s, e, [token], len(token.rstrip(' ')), off_token)
                        j += 1
                    if token[-1] == ' ':
                        off_token += 1  #
                ient += 1  # entity No.

        off_token += 1  # return

        paragraphs.append((i, paragraphText))

    for par_num, token_num in dic_source_relationships:
        destination_xml_id = dic_source_relationships[par_num, token_num][0]
        source_entity_id = dic_source_relationships[par_num, token_num][1]
        label = dic_source_relationships[par_num, token_num][2]

        if str.lower(label) == 'tcvalue':
            relationship_name = 'material-tc'
        elif str.lower(label) == 'pressure':
            relationship_name = 'pressure-tc'
        else:
            raise Exception("Something is wrong in the links. "
                            "The origin label is not recognised: " + label)

        # destination_xml_id: Use this to pick up information from dic_dest_relationship

        for des in destination_xml_id.split(","):
            destination_item = dic_dest_relationships[str(des)]
            destination_paragraph_tsv = destination_item[0]
            destination_token_tsv = destination_item[1]
            destination_entity_id = destination_item[2]

            dict_coordinates = (destination_paragraph_tsv, destination_token_tsv)

            dic_token_entry = dic_token[dict_coordinates]
            if dic_token_entry[5] == 'link_name' and dic_token_entry[6] == 'link_location':
                dic_token_entry[5] = relationship_name
                dic_token_entry[
                    6] = str(par_num) + '-' + str(token_num) + "[" + str(
                    source_entity_id) + '_' + str(destination_entity_id) + ']'
            else:
                dic_token_entry[5] += '|' + relationship_name
                dic_token_entry[6] += '|' + str(par_num) + '-' + str(token_num) + "[" + str(
                    source_entity_id) + '_' + str(destination_entity_id) + ']'

    # Cleaning up the token dictionary
    for k, v in dic_token.items():
        v[5] = v[5].replace('link_name', '_')
        v[6] = v[6].replace('link_location', '_')

    # split in sentences
    output_paragraphs = []
    for paragraph in paragraphs:
        paragraph_id = paragraph[0]
        paragraph_text = paragraph[1]
        sentence_offset = 0
        para_tokens = []

        # print(paragraph_text)

        # Spacy
        doc = nlp(paragraph_text)
        for sent in doc.sents:
            sent = str(sent)

            # Gensim
            # for sent in split_sentences(paragraph_text):

            # print(sent)
            tokens = tokenise(sent)
            sent_tokens = []

            tokens_without_spaces = [token for token in tokens if token != ' ']

            for id in range(0, len(tokens_without_spaces)):
                id_token_in_paragraph = sentence_offset + id
                token = dic_token[(paragraph_id + 1, id_token_in_paragraph + 1)]
                sent_tokens.append(token)
            sentence_offset += len(tokens_without_spaces)

            para_tokens.append((sent, sent_tokens))
        output_paragraphs.append(para_tokens)

    return output_paragraphs


if __name__ == '__main__':
    if len(argv) != 3:
        print("Invalid parameters. Usage: python xml2csv.py input_dir output_dir")
        sys.exit(-1)

    input = argv[1]
    output = argv[2]

    foutput = os.path.join(output, "output.tsv")
    fw = csv.writer(open(foutput, encoding='utf-8', mode='w'), delimiter='\t', quotechar='"')
    fw.writerow(['filename', 'sentence', 'link'])

    if os.path.isdir(input):
        for root, dirs, files in os.walk(input):
            for file_ in files:
                if not file_.lower().endswith(".xml"):
                    continue
                abs_path = os.path.join(root, file_)
                print("Processing: " + str(abs_path))
                paragraphs = processFile(str(abs_path))

                for sentences in paragraphs:
                    for sentence in sentences:
                        write_on_file(fw, file_, sentence[0], sentence[1])

    elif os.path.isfile(input):
        input_path = Path(input)
        paragraphs = processFile(str(input_path))

        for sentences in paragraphs:
            for sentence in sentences:
                write_on_file(fw, input_path.name, sentence[0], sentence[1])
