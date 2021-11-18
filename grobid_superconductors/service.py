import json
import os

import bottle
import spacy
from bottle import request, response, run

from grobid_superconductors.linking.linking_module import RuleBasedLinker, CriticalTemperatureClassifier
from grobid_superconductors.material_parser.materialParserWrapper import MaterialParserWrapper

bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024 * 1024


class Service(object):

    def __init__(self):
        spacy_nlp = spacy.load("en_core_web_sm", disable=['ner', "textcat", "lemmatizer", "tokenizer"])
        self.linker_material_tcValue = RuleBasedLinker(source="<tcValue>", destination="<material>",
                                                       spacy_nlp=spacy_nlp)
        self.linker_tcValue_pressure = RuleBasedLinker(source="<pressure>", destination="<tcValue>",
                                                       spacy_nlp=spacy_nlp)
        self.linker_tcValue_me_method = RuleBasedLinker(source="<tcValue>", destination="<me_method>",
                                                        spacy_nlp=spacy_nlp)

        self.linker_material_crystal_structure = RuleBasedLinker(source="<material>", destination="<crystal-structure>",
                                                                 spacy_nlp=spacy_nlp)
        self.linker_material_space_groups = RuleBasedLinker(source="<material>", destination="<space-groups>",
                                                            spacy_nlp=spacy_nlp)

        self.temperature_classifier = CriticalTemperatureClassifier()
        self.linker_map = {
            'material-tcValue': self.linker_material_tcValue,
            'tcValue-pressure': self.linker_tcValue_pressure,
            'tcValue-me_method': self.linker_tcValue_me_method,
            'material-crystal_structure': self.linker_material_crystal_structure,
            'material-space_groups': self.linker_material_space_groups
        }

        self.label_link = {
            'material-tcValue': '<material>',
            'tcValue-pressure': '<pressure>',
            'tcValue-me_method': '<me_method>',
            'material-crystal_structure': '<material>',
            'material-space_groups': '<material>'
        }

        self.ner = None

        self.version = None

        self.material_parser_wrapper = MaterialParserWrapper()

    def version(self):
        if self.version is None:
            try:
                with open("resources/version.txt", 'r') as fv:
                    self.version = fv.readline() if self.version != "" else "unknown"
            except:
                self.version = "unknown"

        info_json = {"name": "grobid-superconductors-tools", "version": self.version}
        return info_json

    def classify_tc(self):
        input_raw = request.forms.get("input")

        if input_raw is None:
            response.status = 400
            return 'Required a parameter "input" as form-data.'

        try:
            passages_input = json.loads(input_raw)
        except:
            response.status = 400
            return 'Invalid JSON file provided in input.'

        single = False
        if type(passages_input) is dict:
            single = True
            passages_input = [passages_input]

        result = []
        for passage in passages_input:
            result.append(self.temperature_classifier.mark_temperatures_paragraph(passage))

        if single:
            result = result[0]

        return json.dumps(result)

    def process_link(self):
        """
            Process links from the input data using the type of link extractor that are provider, as a json list in the
            parameter 'types'.
            skip_classification = True will skip the classification of the linkable entities
        """
        input_raw = request.forms.get("input")
        passages_input = None
        try:
            passages_input = json.loads(input_raw)
        except:
            response.status = 400
            return 'Invalid JSON file provided in input.'

        link_types_as_list = json.loads(request.forms.get("types")) if request.forms.get(
            "types") is not None else self.linker_map.keys()
        skip_classification = request.forms.get("skip_classification") if request.forms.get(
            "skip_classification") is not None else "False"

        result = []
        single = False
        if type(passages_input) is dict:
            single = True
            passages_input = [passages_input]

        for sentence_input in passages_input:
            result.append(self.process_single_sentence(sentence_input, link_types_as_list, skip_classification))

        if single:
            result = result[0]

        return json.dumps(result)

    def process_single_sentence(self, paragraph_input, link_types_as_list, skip_classification):
        """Link entities in a single sentence"""
        if skip_classification.lower() == 'true':
            skip_classification = True
        else:
            skip_classification = False

        if paragraph_input is None or 'tokens' not in paragraph_input or 'text' not in paragraph_input:
            response.status = 400
            return 'Missing paragraphs, tokens or text.'

        if 'spans' not in paragraph_input:
            paragraph_input['spans'] = []

        if len(paragraph_input['spans']) == 0:
            return paragraph_input

        if not skip_classification:
            marked_tc_paragraph = self.temperature_classifier.mark_temperatures_paragraph(paragraph_input)
            if 'spans' not in marked_tc_paragraph or len(marked_tc_paragraph['spans']) == 0:
                return paragraph_input

            spans_map = {}
            spans_processed = marked_tc_paragraph['spans'] if 'spans' in marked_tc_paragraph else []
            tc_spans = list(filter(lambda w: w['type'] in ["<tcValue>", "tcValue"], spans_processed))

            for s in tc_spans:
                spans_map[s['id']] = s

            for span in paragraph_input['spans'] if 'spans' in paragraph_input else []:
                if 'id' in span and span['id'] in spans_map:
                    span['linkable'] = spans_map[span['id']]['linkable']

        processed_linked_map = {}
        for link_type in link_types_as_list:
            if not skip_classification:
                for span in filter(lambda w: w['type'] == self.label_link[link_type],
                                   paragraph_input['spans'] if 'spans' in paragraph_input else []):
                    span['linkable'] = True

            processed_linked_map[link_type] = self.linker_map[link_type].process_paragraph(paragraph_input)

        for link_type in link_types_as_list:
            processed_linked = processed_linked_map[link_type]

            spans_map = {}
            for paragraphs_processed in processed_linked:
                spans_processed = paragraphs_processed['spans'] if 'spans' in paragraphs_processed else []
                for span_processed in spans_processed:
                    if 'links' in span_processed:
                        non_crf_links = list(filter(lambda w: w['type'] != "crf", span_processed['links']))

                        if len(non_crf_links) > 0:
                            spans_map[span_processed['id']] = non_crf_links

            for span in paragraph_input['spans'] if 'spans' in paragraph_input else []:
                if 'id' in span and span['id'] in spans_map:
                    if 'links' in span:
                        span['links'].extend(spans_map[span['id']])
                    else:
                        span['links'] = spans_map[span['id']]

        return paragraph_input

    def name_to_formula(self):
        raw = request.forms.get("input")

        if raw is None:
            response.status = 400
            return 'Required a parameter "input" as form-data.'
        try:
            formula = self.material_parser_wrapper.name_to_formula(raw)
            if self.is_response_empty(formula):
                lemmatized_name = ''.join([token.lemma_ + token.whitespace_ for token in self.ner(raw)])

                formula = self.material_parser_wrapper.name_to_formula(lemmatized_name)
                if self.is_response_empty(formula):
                    response.status = 404
                    return "Could not find the formula corresponding to " + str(lemmatized_name)
        except ValueError as ve:
            response.status = 400
            return 'The parser was not able to process the provided input: ' + str(ve)

        return json.dumps(formula)

    def is_response_empty(self, formula):
        return ('name' in formula and formula['name'] == "") and ('formula' in formula and formula['formula'] == "")

    def formula_to_composition(self):
        raw = request.forms.get("input")

        if raw is None:
            response.status = 400
            return 'Required a parameter "input" as form-data.'

        try:
            composition = self.material_parser_wrapper.formula_to_composition(raw)
        except ValueError as ve:
            response.status = 400
            return 'The parser was not able to process the provided input: ValueError ' + str(ve)
        except KeyError as ke:
            response.status = 400
            return 'The parser was not able to process the provided input: KeyError ' + str(ke)

        return json.dumps(composition)

    def classify_formula(self):
        raw = request.forms.get("input")

        if raw is None:
            response.status = 400
            return 'Required a parameter "input" as form-data.'

        classes = self.material_parser_wrapper.formula_to_classes(raw)

        return json.dumps(list(classes.keys()))

    def process_structure_text(self):
        input_raw = request.forms.get("input")

        if input_raw is None:
            bottle.response.status = 400
            return 'Required a parameter "input" as form-data.'

        passages_input = None
        try:
            passages_input = json.loads(input_raw)
        except:
            bottle.response.status = 400
            return 'Invalid JSON file provided in input.'

        output = []
        for text in passages_input:
            text_doc = self.ner(text.lower())
            text_doc_original = self.ner(text)
            entities = [
                {"text": str(text_doc_original[ent.start:ent.end]), "label": "<" + ent.label_ + ">",
                 "start": ent.start_char,
                 "end": ent.end_char, "type": ent.ent_id_} for ent in text_doc.ents]

            output.append(entities)

        return json.dumps(output)


def init(host='0.0.0.0', port='8080', config="config.json"):
    app = Service()

    bottle.route('/process/link', method="POST")(app.process_link)

    bottle.route('/convert/name/formula', method="POST")(app.name_to_formula)
    bottle.route('/convert/formula/composition', method="POST")(app.formula_to_composition)

    bottle.route('/classify/tc', method="POST")(app.classify_tc)
    bottle.route('/classify/formula', method="POST")(app.classify_formula)

    bottle.route('/version', method="GET")(app.version)

    if config and os.path.exists(config):

        print("Loading configuration...")
        configuration = {}
        with open(config, 'r') as fp:
            configuration = json.load(fp)

        ner = spacy.load("en_core_web_sm", disable=["parser", "textcat", "ner"])

        print("Loading space groups patterns...")
        entity_ruler_space_groups = ner.add_pipe("entity_ruler", "entity_ruler_space_groups")
        entity_ruler_space_groups.from_disk(configuration['space-groups'])

        print("Loading crystal structure patterns...")
        entity_ruler_crystal_structure = ner.add_pipe("entity_ruler", "crystal_structure")
        entity_ruler_crystal_structure.from_disk(configuration['crystal-structure'])

        bottle.route('/process/structure/text', method="POST")(app.process_structure_text)
        app.ner = ner
    else:
        print("No space groups patterns... ignoring... ")

    bottle.debug(False)
    run(host=host, port=port, debug=True)
