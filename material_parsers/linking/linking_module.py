import copy
import json

import spacy
from blingfire import text_to_sentences
from spacy.tokens import Span, Doc
from spacy.tokens.token import Token

from material_parsers.linking.data_model import span_to_dict
from material_parsers.linking.relationships_resolver import SimpleResolutionResolver, \
    VicinityResolutionResolver

Span.set_extension('id', default=None, force=True)
Span.set_extension('links', default=[], force=True)
Span.set_extension('linkable', default=False, force=True)
Span.set_extension('bounding_boxes', default=[], force=True)
Span.set_extension('formattedText', default="", force=True)

Token.set_extension('id', default=None, force=True)
Token.set_extension('links', default=[], force=True)
Token.set_extension('linkable', default=False, force=True)
Token.set_extension('bounding_boxes', default=[], force=True)
Token.set_extension('formattedText', default="", force=True)


def decode(response):
    try:
        return response.json()
    except ValueError as e:
        return "Error: " + str(e)


def entities_classes():
    return ['<material>', '<class>', '<temperature>', '<tc>',
            '<tcValue>', '<tcvalue>', '<pressure>', '<me_method>',
            '<material-tc>', '<temperature-tc>', '<crystal-structure>', '<space-groups>']


class SpacyPipeline:
    def __init__(self, spacy_nlp_library=None):
        if spacy_nlp_library is not None:
            self.nlp = spacy_nlp_library
        else:
            self.nlp = spacy.load("en_core_web_sm", disable=['ner', "textcat", "lemmatizer", "tokenizer"])

    def filter_spans(self, spans):
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

    def init_doc(self, words, spaces, spans):
        ## Creating a new document with the text
        doc = Doc(self.nlp.vocab, words=words, spaces=spaces)

        ## Loading GROBID entities in the spaCY document
        entities = []
        for s in spans:
            span = Span(doc=doc, start=s['token_start'], end=s['token_end'], label=s['type'])
            span._.set('id', str(s['id']))
            if 'boundingBoxes' in s:
                span._.set('bounding_boxes', s['boundingBoxes'])
            if 'formattedText' in s:
                span._.set('formattedText', s['formattedText'])
            if 'links' in s:
                span._.set('links', s['links'])
            if 'linkable' in s:
                span._.set('linkable', s['linkable'])

            entities.append(span)

        doc.ents = entities
        # print("Entities: " + str(doc.ents))
        with doc.retokenize() as retokenizer:
            for span in entities:
                # Iterate over all spans and merge them into one token. This is done
                # after setting the entities – otherwise, it would cause mismatched
                # indices!
                retokenizer.merge(span)
                for token in span:
                    token._.id = span._.id
                    token._.bounding_boxes = span._.bounding_boxes
                    token._.formattedText = span._.formattedText
                    token._.links = span._.links
                    token._.linkable = span._.linkable
            self.nlp.get_pipe("tagger")(doc)
            self.nlp.get_pipe("parser")(doc)
            ## Merge entities and phrase nouns, but only when they are not overlapping,
            # to avoid loosing the entity type information
            phrases_ents = self.extract_phrases_ents(doc)
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

                # Entities and phrase noun are not overlapping
                if not overlapping:
                    retokenizer.merge(span)
        # self.nlp.tagger(doc)
        # self.nlp.parser(doc)

        return doc

    def get_sentence_boundaries(self, words, spaces):
        offset = 0
        reconstructed = ''
        sentence_offsetTokens = []
        text = ''.join([words[i] + (' ' if spaces[i] else '') for i in range(0, len(words))])

        for sent in text_to_sentences(text).split('\n'):
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

    def convert_to_spacy_simple(self, tokens):
        outputTokens = []
        outputSpaces = []

        for t in tokens:
            outputSpaces.append(False)
            outputTokens.append(t['text'])

        return outputTokens, outputSpaces

    @staticmethod
    def convert_to_spacy(tokens, spans):
        """
        Converts the list of tokens and spans into Spacy made Tokens, Spaces and Spans that can be used to 
        build the Spacy document.
        """
        outputTokens = []
        outputSpaces = []
        outputSpans = []
        first = True
        skip = False

        newIndexOffset = 0
        entityOffset = 0
        inside = False
        if len(spans) > 0:
            span = spans[entityOffset]

        for index, s in enumerate(tokens):
            if len(spans) > 0:
                if index == span['token_start']:
                    span['token_start'] = newIndexOffset
                    inside = True
                elif index == span['token_end']:
                    span['token_end'] = newIndexOffset
                    outputSpans.append(span)
                    inside = False
                    if entityOffset + 1 < len(spans):
                        entityOffset += 1
                        span = spans[entityOffset]
                        if index == span['token_start']:
                            span['token_start'] = newIndexOffset
                            inside = True
                    # else:
                    #     print("finish entities")
                elif index + 1 == len(tokens) and inside:
                    ## I'm at the last token and haven't closed the entity
                    span['token_end'] = newIndexOffset
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
                                # if tokens[index + 1]['text'] and tokens[index + 1]['text'].isalpha():
                                #     outputTokens[-1] = outputTokens[-1] + tokens[index + 1]['text']
                                #     if tokens[index + 1]['text'] == ' ':
                                #         outputSpaces.append(True)
                                #         skip = True
                                #     else:
                                #         outputSpaces.append(False)
                                #         skip = True
                                # 
                                # else:
                                #     outputSpaces.append(False)
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

        if inside and not len(outputSpans) == len(spans):
            span['token_end'] = newIndexOffset
            outputSpans.append(span)
            inside = False

        if not len(outputTokens) == len(outputSpaces):
            print("Something wrong in the final length check! len(outputTokens) = " + str(
                len(outputTokens)) + ", len(outputSpaces) = " + str(len(outputSpaces)))

        if len(spans) > 0 and not len(outputSpans) == len(spans):
            print("Something wrong in spans: len(outputSpans) = " + str(len(outputSpans)) + ", len(spans) = " + str(
                len(spans)))

        reconstructed_tokens = []
        reconstructed_index = 0
        for x in range(0, len(outputTokens)):
            reconstructed_tokens.append(outputTokens[x])
            if tokens[reconstructed_index]['text'] != reconstructed_tokens[reconstructed_index]:
                print("Mismatch between", tokens[reconstructed_index]['text'], "and",
                      reconstructed_tokens[reconstructed_index])
            reconstructed_index += 1

            if outputSpaces[x]:
                reconstructed_tokens.append(" ")
                if tokens[reconstructed_index]['text'] != " ":
                    print("Mismatch space, got instead", tokens[reconstructed_index]['text'])
                reconstructed_index += 1

        return outputTokens, outputSpaces, outputSpans

    def extract_phrases_ents(self, doc):
        phrases_ents = []
        for chunk in doc.noun_chunks:
            phrases_ents.append(Span(doc=doc, start=chunk.start, end=chunk.end, label='phrase'))

        return phrases_ents


class RuleBasedLinker(SpacyPipeline):
    def __init__(self, source="<tcValue>", destination="<material>", spacy_nlp=None):
        super(RuleBasedLinker, self).__init__(spacy_nlp)
        self.source = source
        self.destination = destination

    MATERIAL_TC_TYPE = "<material-tcValue>"
    TC_PRESSURE_TYPE = "<tcValue-pressure>"
    TC_ME_METHOD_TYPE = "<tcValue-me_method>"
    MATERIAL_SPACE_GROUPS = "<material-space_groups>"
    MATERIAL_CRYSTAL_STRUCTURE = "<material-crystal_structure>"

    @staticmethod
    def collect_relationships(relationships, type):
        return [{"type": type, "left": span_to_dict(re[0]), "right": span_to_dict(re[1])} for re in relationships]

    @staticmethod
    def get_link_type(type1, type2):
        if (type2 == "<material>" and type1 == "<tcValue>") or (type1 == "<material>" and type2 == "<tcValue>"):
            return RuleBasedLinker.MATERIAL_TC_TYPE
        elif (type1 == "<pressure>" and type2 == "<tcValue>") or (type2 == "<pressure>" and type1 == "<tcValue>"):
            return RuleBasedLinker.TC_PRESSURE_TYPE
        elif (type1 == "<me_method>" and type2 == "<tcValue>") or (type2 == "<me_method>" and type1 == "<tcValue>"):
            return RuleBasedLinker.TC_ME_METHOD_TYPE
        elif (type1 == "<material>" and type2 == "<space-groups>") or (
            type2 == "<material>" and type1 == "<space-groups>"):
            return RuleBasedLinker.MATERIAL_SPACE_GROUPS
        elif (type1 == "<material>" and type2 == "<crystal-structure>") or (
            type2 == "<material>" and type1 == "<crystal-structure>"):
            return RuleBasedLinker.MATERIAL_CRYSTAL_STRUCTURE
        else:
            raise Exception("The provided type are invalid. " + type1 + ", " + type2)

    def process(self, text_, spans_, tokens_):
        ## Convert tokens from GROBID tokenisation
        words, spaces, spans_remapped = self.convert_to_spacy(tokens_, spans_)

        output_data = []

        # material
        destination_entities = list(filter(lambda w: w['type'] in [self.destination], spans_remapped))
        # tcValue
        source_entities = list(filter(lambda w: w['type'] in [self.source], spans_remapped))

        ## POST-PROCESS Material names
        # materials = post_process(materials)

        if len(destination_entities) > 0 and len(source_entities) > 0:
            data_return = self.process_sentence(words, spaces, spans_remapped)

            if len(data_return) > 0:
                output_data.append(data_return)
        else:
            data_return = {
                "spans": [entity for entity in
                          filter(lambda w: w['type'] in entities_classes(), spans_remapped)],
                "text": ''.join(
                    [words[i] + (' ' if spaces[i] else '') for i in range(0, len(words))])
            }
            output_data.append(data_return)

        return output_data

    def process_paragraph(self, paragraph):
        text_ = copy.deepcopy(paragraph['text'])
        spans_ = copy.deepcopy(paragraph['spans'])
        tokens_ = copy.deepcopy(paragraph['tokens'])

        return self.process(text_, spans_, tokens_)

    def process_paragraph_json(self, paragraph_json):
        paragraph = json.loads(paragraph_json)
        return json.dumps(self.process_paragraph(paragraph))

    def process_sentence(self, words, spaces, spans):
        text = ''.join([words[i] + (' ' if spaces[i] else '') for i in range(0, len(words))])

        # print("Processing: " + text)

        doc = self.init_doc(words, spaces, spans)

        extracted_entities = {}
        # svg = displacy.render(doc, style="dep")
        # filename = hashlib.sha224(b"Nobody inspects the spammish repetition").hexdigest()
        # output_path = Path(str(filename) + ".svg")
        # output_path.open("w", encoding="utf-8").write(svg)

        ### RELATIONSHIP EXTRACTION
        extracted_entities['relationships'] = []

        destination_entities = [entity for entity in
                                filter(lambda w: w.ent_type_ in [self.destination] and w._.linkable is True, doc)]

        source_entities = [entity for entity in
                           filter(lambda w: w.ent_type_ in [self.source] and w._.linkable is True, doc)]

        ## 1 simple approach (when only one temperature and one material)
        resolver = SimpleResolutionResolver()
        relationships = resolver.find_relationships(destination_entities, source_entities)

        if len(relationships) > 0:
            extracted_entities['relationships'].extend(RuleBasedLinker.collect_relationships(relationships, 'simple'))
            # print(" Simple relationships " + str(extracted_entities['relationships']['simple']))
        else:
            ## 2 vicinity matching

            resolver = VicinityResolutionResolver()
            relationships = resolver.find_relationships(doc, destination_entities, source_entities)
            if len(relationships) > 0:
                extracted_entities['relationships'].extend(
                    RuleBasedLinker.collect_relationships(relationships, 'vicinity'))
                # print(" Vicinity relationships " + str(extracted_entities['relationships']['vicinity']))
            # else:

            ## 3 dependency parsing matching

            # resolver = DependencyParserResolutionResolver()
            # relationships = resolver.find_relationships(destination_entities, source_entities)
            # if len(relationships) > 0:
            #     extracted_entities['relationships'].extend(
            #         RuleBasedLinker.collect_relationships(relationships, 'dependency'))
            # print(" Dep relationships " + str(extracted_entities['relationships']['dependency']))

        converted_spans = [span_to_dict(entity) for entity in
                           filter(lambda w: w.ent_type_ in entities_classes(), doc)]

        extracted_entities['spans'] = converted_spans
        extracted_entities['text'] = text

        return extracted_entities


class CriticalTemperatureClassifier(SpacyPipeline):
    def __init__(self, spacy_nlp=None):
        super(CriticalTemperatureClassifier, self).__init__(spacy_nlp)

    def process_doc(self, doc):
        temps = list(filter(
            lambda w: w.ent_type_ in ['temperature', 'tcvalue', 'tcValue', '<temperature>', '<tcvalue>', '<tcValue>'],
            doc))

        if len(temps) == 0:
            return doc

        tc_expressions = list(filter(lambda w: w.ent_type_ in ['<tc>', 'tc'], doc))

        # This is case sensitive 
        non_tc_expressions_before = ["T N", "TN", "t n", "tn", "Curie", "curie", "Neel", "neel", "at T ", "at T =",
                                     "at T=",
                                     "is suppressed at ", "ΔT c", "ΔTc", "Δ T c", "T =", "T=", "T = ", "T= "]
        # This is case insensitive 
        tc_expressions_before = ["superconducts at", "superconductive at around",
                                 "superconducts around", "superconductivity at",
                                 "superconductivity around", "exibits superconductivity at",
                                 "T c =", "Tc ="]
        
        # This is case insensitive
        non_tc_expressions_after = ['higher', 'lower']

        marked_as_tc = []
        marked_as_non_tc = []

        if 'respectively' in str(doc):
            if len(tc_expressions) > 0:
                respectively_tokens = [token for token in doc if str(token) == 'respectively']
                if len(respectively_tokens) == 1:
                    temps_before_respectively = [token for token in temps if respectively_tokens[0].i > token.i]
                    marked_as_tc.extend(temps_before_respectively)
                else:
                    temps_before_respectively = [token for token in temps if
                                                 respectively_tokens[len(respectively_tokens) - 1].i > token.i]

                    marked_as_tc.extend(temps_before_respectively)
        else:
            for index_t, temp in enumerate(temps):
                if temp in marked_as_tc:
                    continue

                ## Ignore any temperature in Celsius
                if not str.lower(str.rstrip(temp.text)).endswith("k"):
                    continue

                ## search for nonTC espressions after the temperature
                for non_tc in non_tc_expressions_after:
                    if temp.i + 1 < len(doc) and str.lower(doc[temp.i + 1].text) == non_tc:
                        marked_as_non_tc.append(temp)
                        break

                if temp in marked_as_non_tc:
                    continue

                for non_tc in non_tc_expressions_before:
                    if temp.i - len(non_tc.split(" ")) >= 0 and doc[
                                                               temp.i - len(non_tc.split(" ")):temp.i].text == non_tc:
                        marked_as_non_tc.append(temp)
                        break

                if temp in marked_as_non_tc:
                    continue

                ## search for tc espressions just before the temperature

                for tc in tc_expressions_before:
                    if temp.i - len(tc.split(" ")) >= 0 and str.lower(doc[temp.i - len(tc.split(" ")):temp.i].text) == tc:
                        marked_as_tc.append(temp)
                        # temp.ent_type_ = "temperature-tc"
                        break

                    if temp.i - len(tc.split(" ")) - 1 >= 0 and str.lower(doc[
                                                               temp.i - len(tc.split(" ")) - 1:temp.i - 1].text) == tc:
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
                    while index >= max(0, previous_temp_index):

                        if doc[index: start].text == tc.text:
                            marked_as_tc.append(temp)
                            # temp.ent_type_ = "temperature-tc"
                            break

                        start -= 1
                        index = start - expression_lenght

        for temp in marked_as_tc:
            temp._.set('linkable', True)
            # print(temp.text, temp.ent_type_)
        return doc

    def mark_temperatures(self, text_, tokens_, spans_):
        words, spaces, spans_remapped = self.convert_to_spacy(tokens_, spans_)
        doc = self.init_doc(words, spaces, spans_remapped)
        doc = self.process_doc(doc)

        extracted_entities = {}

        converted_spans = [span_to_dict(entity) for entity in
                           filter(lambda w: w.ent_type_ in entities_classes(), doc)]

        extracted_entities['spans'] = converted_spans
        extracted_entities['text'] = text_

        return extracted_entities

    def mark_temperatures_paragraph(self, paragraph):
        text_ = copy.deepcopy(paragraph['text'])
        spans_ = copy.deepcopy(paragraph['spans'])
        tokens_ = copy.deepcopy(paragraph['tokens'])

        return self.mark_temperatures(text_, tokens_, spans_)

    def mark_temperatures_paragraph_json(self, paragraph_json):
        paragraph = json.loads(paragraph_json)
        return json.dumps(self.mark_temperatures_paragraph(paragraph))
