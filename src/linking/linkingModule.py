import copy
import csv
import json
import ntpath
import os
import sys
from pathlib import Path
from sys import argv

import requests
import spacy
from gensim.summarization.textcleaner import split_sentences
from src.linking.relationships_resolver import SimpleResolutionResolver, VicinityResolutionResolver, \
    DependencyParserResolutionResolver
# from material_parser.material_parser import MaterialParser
from spacy.tokens import Span, Doc

nlp = spacy.load("en_core_web_sm", disable=['ner'])

# mp = MaterialParser(verbose=False, pubchem_lookup=False, fails_log=False)


def process_dir(path, out_path):
    # xdir = Path('/data/workspace/Suzuki/supercon_files_20190808/iop/data/')
    # xmlfiles = [x for x in xdir.glob('**/*.xml')]
    # pdffiles = [x for x in xdir.glob('**/*.pdf')]
    first = True
    with open(out_path.joinpath('output_complete.json'), 'a') as f:
        f.write("[\n")
        for root, dirs, files in os.walk(path):
            for file_ in files:
                if not file_.lower().endswith(".pdf"):
                    continue
                abs_path = os.path.join(root, file_)

                try:
                    output_data = process_file(abs_path)
                    if output_data['paragraphs']:
                        if first:
                            first = False
                        else:
                            f.write(",")
                        f.write(json.dumps(output_data) + "\n")
                        f.flush()

                        for para in output_data['paragraphs']:
                            for sent in para:
                                relationship = list(set(sent.keys()) &
                                                    set(['simple_relationship',
                                                         'dep_relationship',
                                                         'vicinity_relationship']))
                                if len(relationship) > 0:
                                    with open(out_path.joinpath('output_supercon.csv'), 'a') as csv_f:
                                        writer = csv.writer(csv_f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
                                        if 'dep_relationship' in sent.keys():
                                            for rel in sent['dep_relationship']:
                                                writer.writerow([rel[0], rel[1], abs_path])
                                        elif 'vicinity_relationship' in sent.keys():
                                            for rel in sent['vicinity_relationship']:
                                                writer.writerow([rel[0], rel[1], abs_path])
                                        elif 'simple_relationship' in sent.keys():
                                            for rel in sent['simple_relationship']:
                                                writer.writerow([rel[0], rel[1], abs_path])

                                if 'entities' in sent:
                                    materials = [entity[0] for entity in sent['entities'] if
                                                 entity[1] == 'material']

                                    for material in materials:
                                        with open(out_path.joinpath('output_materials.csv'), 'a') as csv_materials_f:
                                            writer = csv.writer(csv_materials_f, delimiter=',', quotechar='"',
                                                                quoting=csv.QUOTE_ALL)
                                            writer.writerow([material])

                                    temperatures = [entity[0] for entity in sent['entities'] if
                                                    entity[1].startswith('temperature')]

                                    for temperature in temperatures:
                                        with open(out_path.joinpath('output_temperatures.csv'),
                                                  'a') as csv_temperatures_f:
                                            writer = csv.writer(csv_temperatures_f, delimiter=',', quotechar='"',
                                                                quoting=csv.QUOTE_ALL)
                                            writer.writerow([temperature])


                except KeyboardInterrupt:
                    print("Stop it.")
                    if not first:
                        f.write("]\n")
                    sys.exit(-1)
                except:
                    print("Skipping file " + str(abs_path) + ", Exception: " + str(sys.exc_info()))

        if not first:
            f.write("]\n")


def post(file_, abs_path):
    files = {
        'input': (
            file_,
            open(abs_path, 'rb'),
            'application/pdf'
        )
    }

    # grobid_url = "http://localhost:8072/service/processSuperconductorsPDF"
    grobid_url = "http://falcon.nims.go.jp/superconductors/service/processSuperconductorsPDF"
    if not grobid_url.startswith("http://localhost"):
        os.environ['NO_PROXY'] = 'falcon.nims.go.jp'

    r = requests.request(
        "POST",
        grobid_url,
        headers={'Accept': 'application/json'},
        params=None,
        files=files,
        data=None,
        timeout=None
    )
    return r


def decode(response):
    try:
        return response.json()
    except ValueError as e:
        return "Error: " + str(e)


def extract_from_pdf(file_, abs_path):
    print("Processing file " + abs_path)

    r = post(file_, abs_path)

    if r.status_code != 200:
        print("Error when calling the service on file " + str(abs_path) + ", status code: " + str(r.status_code))
        return []

    jsonOut = decode(r)

    return jsonOut['paragraphs']


def convert_to_spacy2(tokens):
    outputTokens = []
    outputSpaces = []

    for t in tokens:
        outputSpaces.append(False)
        outputTokens.append(t['text'])

    return outputTokens, outputSpaces


def convert_to_spacy(tokens, spans):
    outputTokens = []
    outputSpaces = []
    outputSpans = []
    first = True
    skip = False

    newIndexOffset = 0
    entityOffset = 0
    span = copy.copy(spans[entityOffset])
    inside = False

    for index, s in enumerate(tokens):
        if index == span['tokenStart']:
            span['tokenStart'] = newIndexOffset
            inside = True
        elif index == span['tokenEnd']:
            span['tokenEnd'] = newIndexOffset
            outputSpans.append(span)
            inside = False
            if entityOffset + 1 < len(spans):
                entityOffset += 1
                span = copy.copy(spans[entityOffset])
                if index == span['tokenStart']:
                    span['tokenStart'] = newIndexOffset
                    inside = True
            # else:
            #     print("finish entities")
        elif index + 1 == len(tokens) and inside:
            ## I'm at the last token and haven't closed the entity
            span['tokenEnd'] = newIndexOffset
            outputSpans.append(span)
            inside = False

        if skip:
            skip = False
            continue
        if first:
            if not s['text'] == ' ':
                outputTokens.append(s['text'])
                if index + 1 < len(tokens):
                    if tokens[index + 1]['text'] == ' ':
                        outputSpaces.append(True)
                        skip = True
                    else:
                        outputSpaces.append(False)
                else:
                    outputSpaces.append(False)
            else:
                outputTokens.append(' ')
                outputSpaces.append(False)
            first = False
        else:
            if not s['text'] == ' ':
                if s['text'].isalpha():
                    outputTokens.append(s['text'])
                    if index + 1 < len(tokens):
                        if tokens[index + 1]['text'] == ' ':
                            outputSpaces.append(True)
                            skip = True
                        else:
                            if tokens[index + 1]['text'] and tokens[index + 1]['text'].isalpha():
                                outputTokens[-1] = outputTokens[-1] + tokens[index + 1]['text']
                                if tokens[index + 1]['text'] == ' ':
                                    outputSpaces.append(True)
                                    skip = True
                                else:
                                    outputSpaces.append(False)
                                    skip = True

                            else:
                                outputSpaces.append(False)
                    else:
                        outputSpaces.append(False)
                else:
                    outputTokens.append(s['text'])
                    if index + 1 < len(tokens):
                        if tokens[index + 1]['text'] == ' ':
                            outputSpaces.append(True)
                            skip = True
                        else:
                            outputSpaces.append(False)
                    else:
                        outputSpaces.append(False)
            else:
                outputTokens.append(s['text'])
                if index + 1 < len(tokens):
                    if tokens[index + 1]['text'] == ' ':
                        outputSpaces.append(True)
                        skip = True
                    else:
                        outputSpaces.append(False)
                else:
                    outputSpaces.append(False)

        newIndexOffset += 1

    if not len(outputTokens) == len(outputSpaces):
        print("Something wrong in the final length check! len(outputTokens) = " + str(
            len(outputTokens)) + ", len(outputSpaces) = " + str(len(outputSpaces)))

    if not len(outputSpans) == len(spans):
        print("Something wrong in spans: len(outputSpans) = " + str(len(outputSpans)) + ", len(spans) = " + str(
            len(spans)))

    return outputTokens, outputSpaces, outputSpans


def extract_phrases_ents(doc):
    phrases_ents = []
    for chunk in doc.noun_chunks:
        phrases_ents.append(Span(doc=doc, start=chunk.start, end=chunk.end, label='phrase'))

    return phrases_ents


def filter_spans(spans):
    # Filter a sequence of spans so they don't contain overlaps
    # For spaCy 2.1.4+: this function is available as spacy.util.filter_spans()
    get_sort_key = lambda span: (span.end - span.start, -span.start)
    sorted_spans = sorted(spans, key=get_sort_key, reverse=True)
    result = []
    seen_tokens = set()
    for span in sorted_spans:
        # Check for end - 1 here because boundaries are inclusive
        if span.start not in seen_tokens and span.end - 1 not in seen_tokens:
            result.append(span)
        seen_tokens.update(range(span.start, span.end))
    result = sorted(result, key=lambda span: span.start)
    return result


def process_paragraph(paragraph):
    text_ = paragraph['text']
    spans_ = paragraph['spans']
    tokens_ = paragraph['tokens']

    ## Convert tokens from GROBID tokenisation
    words, spaces, spans_remapped = convert_to_spacy(tokens_, spans_)
    # print(spans_remapped)

    ## Sentence segmentation
    boundaries = get_sentence_boundaries(words, spaces)

    output_data = []

    cumulatedIndex = 0
    cumulatedOffset = 0
    for index, boundary in enumerate(boundaries):
        words_boundary = words[boundary[0]: boundary[1]]
        spaces_boundary = spaces[boundary[0]: boundary[1]]
        text = ''.join([words_boundary[i] + (' ' if spaces_boundary[i] else '') for i in range(0, len(words_boundary))])

        spans_boundary = []

        for s in spans_remapped:
            if s['tokenStart'] >= boundary[0] and s['tokenEnd'] <= boundary[1]:
                copied_span = copy.copy(s)
                copied_span['tokenStart'] = s['tokenStart'] - cumulatedIndex
                copied_span['tokenEnd'] = s['tokenEnd'] - cumulatedIndex
                copied_span['offsetStart'] = s['offsetStart'] - cumulatedOffset
                copied_span['offsetEnd'] = s['offsetEnd'] - cumulatedOffset

                spans_boundary.append(copied_span)

        cumulatedIndex += len(words_boundary)
        cumulatedOffset += len(text)

        materials = list(filter(lambda w: w['type'] in ['material'], spans_boundary))
        temperatures = list(filter(lambda w: w['type'] in ['temperature'], spans_boundary))

        if len(materials) > 0 and len(temperatures) > 0:
            data_return = process_sentence(words_boundary, spaces_boundary, spans_boundary)

            if len(data_return) > 0:
                output_data.append(data_return)
        else:
            data_return = {
                "spans": [entity for entity in filter(lambda w: w['type'] in entities_classes(), spans_boundary)],
                "text": ''.join(
                    [words_boundary[i] + (' ' if spaces_boundary[i] else '') for i in range(0, len(words_boundary))])
            }
            output_data.append(data_return)

    return output_data


def markCriticalTemperature(doc):
    temps = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature'], doc)]
    tc_expressions = [entity for entity in filter(lambda w: w.ent_type_ in ['tc'], doc)]

    tc_expressions_standard = ["T c", "Tc", "tc", "t c"]

    non_tc_expressions_before = ["T N", "TN", "t n", "tn", "Curie", "curie", "Neel", "neel"]

    tc_expressions_before = ["superconducts at", "superconductive at around",
                             "superconducts around", "superconductivity at",
                             "superconductivity around", "exibits superconductivity at",
                             "T c =", "Tc ="]
    non_tc_expressions_after = ['higher', 'lower']

    marked = []

    for index_t, temp in enumerate(temps):
        if temp in marked:
            continue

        ## Ignore any temperature in Celsius
        if not str.lower(str.rstrip(temp.text)).endswith("k"):
            continue

        ## search for nonTC espressions after the temperature
        for non_tc in non_tc_expressions_after:
            if doc[temp.i + 1].text == non_tc:
                marked.append(temp)
                break

        for non_tc in non_tc_expressions_before:
            if doc[temp.i - len(non_tc.split(" ")):temp.i].text == non_tc:
                marked.append(temp)
                break

        ## search for tc espressions just before the temperature

        for tc in tc_expressions_before:
            if temp.i - len(tc.split(" ")) > 0 and doc[temp.i - len(tc.split(" ")):temp.i].text == tc:
                marked.append(temp)
                temp.ent_type_ = "temperature-tc"
                break

            if temp.i - len(tc.split(" ")) - 1 > 0 and doc[temp.i - len(tc.split(" ")) - 1:temp.i - 1].text == tc:
                marked.append(temp)
                temp.ent_type_ = "temperature-tc"
                break

        ## search for dynamic tc expressions

        for tc in tc_expressions:
            # If it's found in the tc_expressions it was merged as a single expression
            expression_lenght = 1

            start = temp.i
            previous_temp_index = temps[index_t - 1].i if index_t > 0 else 0
            index = start - expression_lenght
            while index > max(0, previous_temp_index):

                if doc[index: start].text == tc.text:
                    marked.append(temp)
                    temp.ent_type_ = "temperature-tc"
                    break

                start -= 1
                index = start - expression_lenght

    # for temp in temps:
    #     print(temp.text, temp.ent_type_)
    return doc


def process_sentence(words, spaces, spans_remapped):
    text = ''.join([words[i] + (' ' if spaces[i] else '') for i in range(0, len(words))])

    print("Processing: " + text)

    ## Creating a new document with the text
    doc = Doc(nlp.vocab, words=words, spaces=spaces)

    ## Loading GROBID entities in the spaCY document
    # entities = [Span(doc=doc, start=s['tokenStart'], end=s['tokenEnd'], label=s['type']) for s in spans_remapped]
    entities = []
    mapping_span_to_entity = {}
    mapping_entity_to_span = {}
    mapping_id_to_coordinates = {}
    for s in spans_remapped:
        span_id = str(s['id'])
        span = Span(doc=doc, start=s['tokenStart'], end=s['tokenEnd'], label=s['type'], kb_id=span_id)
        # span.kb_id=s['id']
        entities.append(span)
        mapping_id_to_coordinates[span_id] = s['boundingBoxes']

        # mapping_entity_to_span = {v: k for k, v in mapping_span_to_entity.items()}
        # if len(mapping_entity_to_span.keys()) != len(mapping_span_to_entity):
        #     raise Exception("There is a duplicated span identifier. " + str(mapping_span_to_entity))

    doc.ents = entities
    print("Entities: " + str(doc.ents))

    for span in entities:
        # Iterate over all spans and merge them into one token. This is done
        # after setting the entities – otherwise, it would cause mismatched
        # indices!
        span.merge()

    nlp.tagger(doc)
    nlp.parser(doc)

    ## Merge entities and phrase nouns, but only when they are not overlapping,
    # to avoid loosing the entity type information
    phrases_ents = extract_phrases_ents(doc)
    # print(phrases_ents)
    for span in phrases_ents:
        # print("Span " + str(span))
        overlapping = False
        for ent in entities:
            # print(ent)
            if (
                    (span.start <= ent.start <= span.end) or
                    (span.start <= ent.end >= span.end) or
                    (span.start >= ent.start and span.end <= ent.end) or
                    (span.start <= ent.start and span.end >= ent.end)
            ):
                overlapping = True
                break

        # Entities and phrase noun are not Overlapping
        if not overlapping:
            span.merge()

    nlp.tagger(doc)
    nlp.parser(doc)

    extracted_entities = {}

    # svg = displacy.render(doc, style="dep")
    # filename = hashlib.sha224(b"Nobody inspects the spammish repetition").hexdigest()
    # output_path = Path(str(filename) + ".svg")
    # output_path.open("w", encoding="utf-8").write(svg)

    # extracted_entities['tokens'] = words

    ## MATERIAL NAME RESOLUTION

    ### TC VALUES CLASSIFICATION

    markCriticalTemperature(doc)

    ### RELATIONSHIP EXTRACTION
    extracted_entities['relationships'] = {}

    ## 1 simple approach (when only one temperature and one material)
    resolver = SimpleResolutionResolver()
    relationship = resolver.find_relationship(doc)

    if len(relationship) > 0:
        extracted_entities['relationships']['simple'] = collect_relationships(relationship, mapping_id_to_coordinates)
        print(" Simple relationships " + str(extracted_entities['relationships']['simple']))

    ## 2 vicinity matching

    resolver = VicinityResolutionResolver()
    relationship = resolver.find_relationship(doc)
    if len(relationship) > 0:
        extracted_entities['relationships']['vicinity'] = collect_relationships(relationship, mapping_id_to_coordinates)
        print(" Vicinity relationships " + str(extracted_entities['relationships']['vicinity']))

    ## 3 dependency parsing matching

    resolver = DependencyParserResolutionResolver()
    relationship = resolver.find_relationship(doc)
    if len(relationship) > 0:
        extracted_entities['relationships']['dependency'] = collect_relationships(relationship,
                                                                                  mapping_id_to_coordinates)
        print(" Dep relationships " + str(extracted_entities['relationships']['dependency']))


    spans_not_yet_as_dict = [entity for entity in
                                   filter(lambda w: w.ent_type_ in entities_classes(), doc)]

    converted_spans = [span_to_dict(span_to_be_converted, mapping_id_to_coordinates) for span_to_be_converted in spans_not_yet_as_dict]

    extracted_entities['spans'] = converted_spans
    extracted_entities['text'] = text

    return extracted_entities


def token_to_dict(token):
    converted_token = {
        "text": "",
        "font": "",
        "style": "",
        "offset": "",
        "fontSize": ""
    }
    converted_token['text'] = span.text
    converted_token['offset'] = span.idx
    # converted_token['style']
    # converted_token['font'] = span.ent_type_
    # converted_token['fontSize'] = span.i

    return converted_token


def span_to_dict(span, mapping_id_to_coordinates):
    converted_span = {
        "text": "",
        "type": "",
        "offsetStart": "",
        "offsetEnd": "",
        "tokenStart": "",
        "tokenEnd": "",
        "id": "",
        "boundingBoxes": []
    }

    converted_span['text'] = span.text
    converted_span['type'] = span.ent_type_
    converted_span['offsetStart'] = span.idx
    converted_span['offsetEnd'] = span.idx + len(span.text)
    converted_span['tokenStart'] = span.i
    converted_span['tokenEnd'] = span.i + len(span)
    converted_span['id'] = span.ent_kb_id_
    converted_span['boundingBoxes'] = mapping_id_to_coordinates[converted_span['id']]

    return converted_span


def entities_classes():
    return ['material', 'class', 'temperature', 'tc',
            'tcValue', 'me_method', 'material-tc', 'temperature-tc']


def collect_relationships(relationships, mapping_id_to_coordinates):
    return [
        (span_to_dict(re[0], mapping_id_to_coordinates),
         span_to_dict(re[1], mapping_id_to_coordinates)) for re
        in relationships]

def get_sentence_boundaries(words, spaces):
    offset = 0
    reconstructed = ''
    sentence_offsetTokens = []
    text = ''.join([words[i] + (' ' if spaces[i] else '') for i in range(0, len(words))])
    for sent in split_sentences(text):
        start = offset

        for id in range(offset, len(words)):
            token = words[id]
            reconstructed += token
            if spaces[id]:
                reconstructed += ' '
            if len(reconstructed.rstrip()) == len(sent):
                offset += 1
                end = offset
                sentence_offsetTokens.append((start, end))
                reconstructed = ''
                break
            offset += 1

    return sentence_offsetTokens


def process_file(input_path):
    input_filename = ntpath.basename(input_path)
    extracted_data = extract_from_pdf(input_filename, input_path)

    output_data = {"filename": input_path, "paragraphs": []}
    for index, paragraph in enumerate(extracted_data):
        if len(paragraph['spans']) > 0:
            extracted_data_from_paragraphs = process_paragraph(paragraph)
            if len(extracted_data_from_paragraphs) > 0:
                output_data['paragraphs'].append(extracted_data_from_paragraphs)

    return output_data
    # processText(output[14])
    # processText(output[17])


if __name__ == '__main__':

    if len(argv) != 3:
        print("Invalid parameters. Usage: python linkingModule.py input output")
        print("if input is a directory will process every PDF file recursively.")

        # print("Meanwhile we are processing the default hardcoded documents :-) ")

        # process_file("/Users/lfoppiano/development/superconductors/supercon_papers/supercon_files_20190308/aip/data/fy2005/JAP/97/7/10.1063_1.1871335/10.1063_1.1871335_fulltext.pdf")
        # process_file("/Users/lfoppiano/development/superconductors/supercon_papers/supercon_files_20190308/aip/data/fy2018/JCP/v149/i7/074101_1/vor_1.5031202.pdf")
        # process_file("/Users/lfoppiano/development/superconductors/supercon_papers/supercon_files_20190308/aip/data/fy2005/JAP/98/3/10.1063_1.1997288/10.1063_1.1997288_fulltext.pdf")
        # process_file("/Users/lfoppiano/development/superconductors/supercon_papers/supercon_files_20190308/aps/data/fy2018/PRB/2017/PhysRevB.95.224501/online.pdf")
        # process_dir(
        #     "/Users/lfoppiano/development/superconductors/supercon_papers/supercon_files_20190308/aip/data/fy2018/JCP/v148/i19/194701_1/",
        #     "output")
        # process_dir(
        #     "/Users/lfoppiano/development/superconductors/supercon_papers/supercon_files_20190308/aip/data/fy2018/JAP/v123/i5/053301_1/",
        #     "output")
        # process_dir(
        #     "/Users/lfoppiano/development/superconductors/supercon_papers/supercon_files_20190308/aip/data/fy2018/JAP/v123/i5/053301_1/",
        #     "output")
        sys.exit(-1)

    input = argv[1]
    output = argv[2]

    if os.path.isdir(input):
        input_path = Path(input)
        output_path = Path(output)
        if os.path.isdir(output):
            output_path = Path(output)

        process_dir(input_path, output_path)

    elif os.path.isfile(input):
        input_path = Path(input)
        output_data = process_file(str(input_path))
        with open(Path(output + '/output_single.json'), 'w') as f:
            f.write(json.dumps(output_data) + "\n")

    # for token in doc:
    #     print(token.text, token.dep_, token.head.text, token.head.pos_,
    #           [child for child in token.children])
