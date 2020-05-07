import copy

import spacy
from gensim.summarization.textcleaner import split_sentences
from spacy.tokens import Span, Doc
from spacy.tokens.token import Token

from relationships_resolver import SimpleResolutionResolver, VicinityResolutionResolver, \
    DependencyParserResolutionResolver

nlp = spacy.load("en_core_sci_sm", disable=['ner'])

Span.set_extension('id', default=None, force=True)
Span.set_extension('links', default=[], force=True)
Span.set_extension('bounding_boxes', default=[], force=True)
Span.set_extension('formattedText', default="", force=True)

Token.set_extension('id', default=None, force=True)
Token.set_extension('links', default=[], force=True)
Token.set_extension('bounding_boxes', default=[], force=True)
Token.set_extension('formattedText', default="", force=True)


def decode(response):
    try:
        return response.json()
    except ValueError as e:
        return "Error: " + str(e)


def convert_to_spacy2(tokens):
    outputTokens = []
    outputSpaces = []

    for t in tokens:
        outputSpaces.append(False)
        outputTokens.append(t['text'])

    return outputTokens, outputSpaces


def convert_to_spacy(tokens: dict, spans):
    outputTokens = []
    outputSpaces = []
    outputSpans = []
    first = True
    skip = False

    newIndexOffset = 0
    entityOffset = 0
    inside = False
    if len(spans) > 0:
        span = copy.copy(spans[entityOffset])

    for index, s in enumerate(tokens):
        if len(spans) > 0:
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

    if len(spans) > 0 and not len(outputSpans) == len(spans):
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
    # boundaries = get_sentence_boundaries(words, spaces)
    boundaries = get_sentence_boundaries_spacy(words, spaces)

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
        temperatures = list(filter(lambda w: w['type'] in ['temperature', 'tcvalue'], spans_boundary))

        ## POST-PROCESS Material names
        # materials = post_process(materials)

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
    temps = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature', 'tcvalue'], doc)]
    tc_expressions = [entity for entity in filter(lambda w: w.ent_type_ in ['tc'], doc)]

    tc_expressions_standard = ["T c", "Tc", "tc", "t c"]

    non_tc_expressions_before = ["T N", "TN", "t n", "tn", "Curie", "curie", "Neel", "neel", "at T ", "at T =", "at T=",
                                 "is suppressed at ", "ΔT c", "ΔTc", "Δ T c", "T =", "T=", "T = ", "T= "]

    tc_expressions_before = ["superconducts at", "superconductive at around",
                             "superconducts around", "superconductivity at",
                             "superconductivity around", "exibits superconductivity at",
                             "T c =", "Tc ="]
    non_tc_expressions_after = ['higher', 'lower']

    marked_as_tc = []
    marked_as_non_tc = []

    for index_t, temp in enumerate(temps):
        if temp in marked_as_tc:
            continue

        ## Ignore any temperature in Celsius
        if not str.lower(str.rstrip(temp.text)).endswith("k"):
            continue

        ## search for nonTC espressions after the temperature
        for non_tc in non_tc_expressions_after:
            if temp.i + 1 < len(doc) and doc[temp.i + 1].text == non_tc:
                marked_as_non_tc.append(temp)
                break

        if temp in marked_as_non_tc:
            continue

        for non_tc in non_tc_expressions_before:
            if temp.i - len(non_tc.split(" ")) > 0 and doc[temp.i - len(non_tc.split(" ")):temp.i].text == non_tc:
                marked_as_non_tc.append(temp)
                break

        if temp in marked_as_non_tc:
            continue

        ## search for tc espressions just before the temperature

        for tc in tc_expressions_before:
            if temp.i - len(tc.split(" ")) > 0 and doc[temp.i - len(tc.split(" ")):temp.i].text == tc:
                marked_as_tc.append(temp)
                # temp.ent_type_ = "temperature-tc"
                break

            if temp.i - len(tc.split(" ")) - 1 > 0 and doc[temp.i - len(tc.split(" ")) - 1:temp.i - 1].text == tc:
                marked_as_tc.append(temp)
                # temp.ent_type_ = "temperature-tc"
                break

        if temp in marked_as_tc:
            continue

        ## search for dynamic tc expressions

        for tc in tc_expressions:
            # If it's found in the tc_expressions it was merged as a single expression
            expression_lenght = 1

            start = temp.i
            previous_temp_index = temps[index_t - 1].i if index_t > 0 else 0
            index = start - expression_lenght
            while index > max(0, previous_temp_index):

                if doc[index: start].text == tc.text:
                    marked_as_tc.append(temp)
                    # temp.ent_type_ = "temperature-tc"
                    break

                start -= 1
                index = start - expression_lenght

    for temp in marked_as_tc:
        temp.ent_type_ = "temperature-tc"
        # print(temp.text, temp.ent_type_)
    return doc


def process_sentence(words, spaces, spans):
    text = ''.join([words[i] + (' ' if spaces[i] else '') for i in range(0, len(words))])

    print("Processing: " + text)

    doc = init_doc(words, spaces, spans)

    extracted_entities = {}
    # svg = displacy.render(doc, style="dep")
    # filename = hashlib.sha224(b"Nobody inspects the spammish repetition").hexdigest()
    # output_path = Path(str(filename) + ".svg")
    # output_path.open("w", encoding="utf-8").write(svg)

    # extracted_entities['tokens'] = words

    ### TC VALUES CLASSIFICATION

    markCriticalTemperature(doc)

    ### RELATIONSHIP EXTRACTION
    extracted_entities['relationships'] = []

    ## 1 simple approach (when only one temperature and one material)
    resolver = SimpleResolutionResolver()

    materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
    tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature-tc'], doc)]

    relationships = resolver.find_relationships(materials, tcValues)

    if len(relationships) > 0:
        extracted_entities['relationships'].extend(collect_relationships(relationships, 'simple'))
        # print(" Simple relationships " + str(extracted_entities['relationships']['simple']))
    else:

        ## 2 vicinity matching

        resolver = VicinityResolutionResolver()
        relationships = resolver.find_relationships(doc, materials, tcValues)
        if len(relationships) > 0:
            extracted_entities['relationships'].extend(collect_relationships(relationships, 'vicinity'))
            # print(" Vicinity relationships " + str(extracted_entities['relationships']['vicinity']))
        else:

            ## 3 dependency parsing matching

            resolver = DependencyParserResolutionResolver()
            relationships = resolver.find_relationships(materials, tcValues)
            if len(relationships) > 0:
                extracted_entities['relationships'].extend(collect_relationships(relationships, 'dependency'))
                # print(" Dep relationships " + str(extracted_entities['relationships']['dependency']))

    converted_spans = [span_to_dict(entity) for entity in
                       filter(lambda w: w.ent_type_ in entities_classes(), doc)]

    extracted_entities['spans'] = converted_spans
    extracted_entities['text'] = text

    return extracted_entities


def init_doc(words, spaces, spans):
    ## Creating a new document with the text
    doc = Doc(nlp.vocab, words=words, spaces=spaces)

    ## Loading GROBID entities in the spaCY document
    entities = []
    for s in spans:
        span = Span(doc=doc, start=s['tokenStart'], end=s['tokenEnd'], label=s['type'])
        span._.set('id', str(s['id']))
        if 'boundingBoxes' in s:
            span._.set('bounding_boxes', s['boundingBoxes'])
        if 'formattedText' in s:
            span._.set('formattedText', s['formattedText'])

        entities.append(span)

    doc.ents = entities
    # print("Entities: " + str(doc.ents))
    for span in entities:
        # Iterate over all spans and merge them into one token. This is done
        # after setting the entities – otherwise, it would cause mismatched
        # indices!
        span.merge()
        for token in span:
            token._.id = span._.id
            token._.bounding_boxes = span._.bounding_boxes
            token._.formattedText = span._.formattedText
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

    return doc


def token_to_dict(token):
    converted_token = {
        "text": "",
        "formattedText": "",
        "font": "",
        "style": "",
        "offset": "",
        "fontSize": ""
    }
    converted_token['text'] = token.text
    converted_token['offset'] = token.idx
    converted_token['formattedText'] = token._.formattedText
    # converted_token['style']
    # converted_token['font'] = span.ent_type_
    # converted_token['fontSize'] = span.i

    return converted_token


def span_to_dict(span):
    converted_span = {
        "text": "",
        "formattedText": "",
        "type": "",
        "offsetStart": "",
        "offsetEnd": "",
        "tokenStart": "",
        "tokenEnd": "",
        "id": "",
        "boundingBoxes": [],
        "links": []
    }

    converted_span['text'] = span.text
    converted_span['formattedText'] = span._.formattedText
    converted_span['type'] = span.ent_type_
    converted_span['offsetStart'] = span.idx
    converted_span['offsetEnd'] = span.idx + len(span.text)
    converted_span['tokenStart'] = span.i
    converted_span['tokenEnd'] = span.i + len(span)
    converted_span['id'] = span._.id
    converted_span['boundingBoxes'] = span._.bounding_boxes
    converted_span['links'] = span._.links

    return converted_span


def entities_classes():
    return ['material', 'class', 'temperature', 'tc',
            'tcValue', 'tcvalue', 'pressure', 'me_method',
            'material-tc', 'temperature-tc']


def collect_relationships(relationships, type):
    return [(span_to_dict(re[0]), span_to_dict(re[1]), type) for re in relationships]


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


def get_sentence_boundaries_spacy(words, spaces):
    offset = 0
    reconstructed = ''
    sentence_offsetTokens = []
    text = ''.join([words[i] + (' ' if spaces[i] else '') for i in range(0, len(words))])
    doc = Doc(nlp.vocab, words=words, spaces=spaces)
    nlp.tagger(doc)
    nlp.parser(doc)

    sentences = list(doc.sents)
    if len(sentences) == 0:
        return sentence_offsetTokens

    if len(sentences) == 1:
        sentence_offsetTokens.append((0, len(str(sentences[0]))))
        return sentence_offsetTokens

    for sent in doc.sents:
        start = offset

        for id in range(offset, len(words)):
            token = words[id]
            reconstructed += token
            if spaces[id]:
                reconstructed += ' '
            if len(reconstructed.rstrip()) == len(str(sent)):
                offset += 1
                end = offset
                sentence_offsetTokens.append((start, end))
                reconstructed = ''
                break
            offset += 1

    return sentence_offsetTokens
