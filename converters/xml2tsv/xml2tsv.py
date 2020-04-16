# transform XML Tei to TSV for WebAnno
import os
import re
import sys
from pathlib import Path
from sys import argv

from bs4 import BeautifulSoup, NavigableString, Tag

from commons.GrobidTokenizer import tokenizeSimple


def tokenise(string):
    return tokenizeSimple(string)

def write_on_file(fw, paragraphText, dic_token, i, len_root):
    # tsvText += f'#Text={paragraphText}\n'
    print(f'#Text={paragraphText}', file=fw)
    for k, v in dic_token.items():
        # print(v)
        if k[0] == i + 1 and v[2]:
            print('{}-{}\t{}-{}\t{}\t{}\t{}\t{}\t{}\t'.format(*k, *v), file=fw)
    if i != len_root - 1:
        print('', file=fw)


def processFile(finput, foutput):
    with open(finput, encoding='utf-8') as fp:
        doc = fp.read()

    mod_tags = re.finditer(r'(</\w+>) ', doc)
    for mod in mod_tags:
        doc = doc.replace(mod.group(), ' ' + mod.group(1))
    #     print(doc)
    soup = BeautifulSoup(doc, 'xml')

    fw = open(foutput, 'w', encoding='utf-8')
    print('#FORMAT=WebAnno TSV 3.2', file=fw)
    print('#T_SP=webanno.custom.Supercon|extra_tag|supercon_tag', file=fw)
    print('#T_RL=webanno.custom.Supercon_link|relationships|BT_webanno.custom.Supercon\n\n', file=fw)

    root = None
    for child in soup.tei.children:
        if child.name == 'text':
            root = child

    off_token = 0
    tsvText = ''
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
                    if len(token) > 0 and token[-1] == ' ':
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

                        # link_to = dic_relationships[item.attrs['ptr'].replace("#", '')]
                        # relationship_name = link_to[2] + '-' + entity
                        # relationship_references = str(link_to[0]) + '-' + str(link_to[1]) + '[' + str(
                        #     i + 1) + '-' + str(j + 1) + ']'
                        # print(dic_token[link_to[0], link_to[1]])
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
                    if len(token) > 0 and token[-1] == ' ':
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

    # Cleaning up the dictionary token
    for k, v in dic_token.items():
        v[5] = v[5].replace('link_name', '_')
        v[6] = v[6].replace('link_location', '_')

    for paragraph in paragraphs:
        write_on_file(fw, paragraph[1], dic_token, paragraph[0], len(root('p')))


if __name__ == '__main__':
    if len(argv) != 3:
        print("Invalid parameters. Usage: python xml2tsv_webanno.py input_dir output_dir")
        sys.exit(-1)

    input = argv[1]
    output = argv[2]

    if os.path.isdir(input):
        path_list = Path(input).glob('*.tei.xml')
        for path in path_list:
            print("Processing: ", path)
            processFile(str(path), os.path.join(output, str(path.name) + ".tsv"))
    elif os.path.isfile(input):
        input_path = Path(input)
        processFile(str(input_path), os.path.join(output, str(input_path.name) + ".tsv"))
