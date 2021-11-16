import re

from bs4 import BeautifulSoup, Tag, NavigableString

from .grobid_tokenizer import tokenizeSimple


def tokenise(string):
    return tokenizeSimple(string)


def get_section(pTag):
    section = None
    if pTag.name == 'p':
        section = pTag.parent.name
    elif pTag.name == 'ab':
        if 'type' in pTag.attrs:
            type = pTag.attrs['type']
            if type == 'keywords':
                section = "keywords"
            elif type == 'figureCaption':
                section = 'figureCaption'
            elif type == 'tableCaption':
                section = 'tableCaption'
    elif pTag.name == 'title':
        section = 'title'

    return section


def process_file(input_document):
    with open(input_document, encoding='utf-8') as fp:
        doc = fp.read()

    mod_tags = re.finditer(r'(</\w+>) ', doc)
    for mod in mod_tags:
        doc = doc.replace(mod.group(), ' ' + mod.group(1))
    soup = BeautifulSoup(doc, 'xml')

    children = get_children_list(soup, verbose=False)

    off_token = 0
    dic_token = {}
    ient = 1

    # list containing text and the dictionary with all the annotations
    paragraphs = []
    dic_dest_relationships = {}
    dic_source_relationships = {}

    i = 0
    for child in children:
        for pTag in child:
            j = 0
            section = get_section(pTag)
            if not section:
                section = get_section(pTag.parent)
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
                                s, e, token.rstrip(' '), section + f'[{i + 10000}]', entity_class, entity_class,
                                entity_class, entity_class, entity_class]
                            #                     print((i+1, j+1), s, e, [token], len(token.rstrip(' ')), off_token)
                            j += 1
                        if len(token) > 0 and token[-1] == ' ':
                            off_token += 1  #
                elif type(item) is Tag and item.name == 'rs':
                    paragraphText += item.text

                    token_list = tokenise(item.string)
                    #                 token_list[-1] += ' ' # add space the end of tag contents
                    if 'type' not in item.attrs:
                        raise Exception("RS without type is invalid. Stopping")

                    entity_class = item.attrs['type']
                    link_name = '_'
                    link_location = '_'

                    if len(item.attrs) > 0:
                        if 'xml:id' in item.attrs:
                            if item.attrs['xml:id'] not in dic_dest_relationships:
                                dic_dest_relationships[item.attrs['xml:id']] = [i + 1, j + 1, ient, entity_class]

                        if 'corresp' in item.attrs:
                            if (i + 1, j + 1) not in dic_source_relationships:
                                dic_source_relationships[i + 1, j + 1] = [item.attrs['corresp'].replace('#', ''),
                                                                          ient,
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
                            dic_token[(i + 1, j + 1)] = [s, e, token.rstrip(' '), section + f'[{i + 10000}]',
                                                         f'*[{ient}]',
                                                         entity_class + f'[{ient}]', link_name, link_location]
                            #                     print((i+1, j+1), s, e, [token], len(token.rstrip(' ')), off_token)
                            j += 1
                        if len(token) > 0 and token[-1] == ' ':
                            off_token += 1  #
                    ient += 1  # entity No.

            off_token += 1  # return

            paragraphs.append((i, paragraphText))
            i += 1

    for par_num, token_num in dic_source_relationships:
        destination_xml_id = dic_source_relationships[par_num, token_num][0]
        source_entity_id = dic_source_relationships[par_num, token_num][1]
        label = dic_source_relationships[par_num, token_num][2]

        # destination_xml_id: Use this to pick up information from dic_dest_relationship

        for des in destination_xml_id.split(","):
            destination_item = dic_dest_relationships[str(des)]
            destination_paragraph_tsv = destination_item[0]
            destination_token_tsv = destination_item[1]
            destination_entity_id = destination_item[2]
            destination_type = destination_item[3]

            if str.lower(label) == 'tcvalue':
                if destination_type == 'material':
                    relationship_name = 'tcValue-material'
                elif str.lower(destination_type) == 'me_method':
                    relationship_name = 'tcValue-me_method'
                else:
                    raise Exception("Something is wrong in the links. "
                                    "The origin label " + str(label) + ", or the destination " + str(
                        destination_type) + " is not recognised. ")
            elif str.lower(label) == 'pressure':
                relationship_name = 'tcValue-pressure'
            else:
                raise Exception("Something is wrong in the links. "
                                "The origin label " + str(label) + ", or the destination " + str(
                    destination_type) + " is not recognised. ")

            dict_coordinates = (destination_paragraph_tsv, destination_token_tsv)

            dic_token_entry = dic_token[dict_coordinates]
            if dic_token_entry[6] == 'link_name' and dic_token_entry[7] == 'link_location':
                dic_token_entry[6] = relationship_name
                dic_token_entry[7] = str(par_num) + '-' + str(token_num) + "[" + str(
                    source_entity_id) + '_' + str(destination_entity_id) + ']'
            else:
                dic_token_entry[6] += '|' + relationship_name
                dic_token_entry[7] += '|' + str(par_num) + '-' + str(token_num) + "[" + str(
                    source_entity_id) + '_' + str(destination_entity_id) + ']'

    # Cleaning up the dictionary token
    for k, v in dic_token.items():
        v[6] = v[6].replace('link_name', '_')
        v[7] = v[7].replace('link_location', '_')

    return paragraphs, dic_token


def get_children_list(soup, verbose=False):

    children = []

    for child in soup.tei.children:
        if child.name == 'teiHeader':
            pass
            children.append(child.find_all("title"))
            children.extend([subchild.find_all("s") for subchild in child.find_all("abstract")])
            children.extend([subchild.find_all("s") for subchild in child.find_all("ab", {"type": "keywords"})])
        elif child.name == 'text':
            children.extend([subchild.find_all("s") for subchild in child.find_all("body")])

    if verbose:
        print(str(children))

    return children
