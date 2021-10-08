import json
from pathlib import Path

import bottle
import plac
import spacy
from bottle import request, run
from flask import abort

from linking_module import RuleBasedLinker, CriticalTemperatureClassifier
from materialParserWrapper import MaterialParserWrapper

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

        self.temperature_classifier = CriticalTemperatureClassifier()
        self.linker_map = {
            'material-tcValue': self.linker_material_tcValue,
            'tcValue-pressure': self.linker_tcValue_pressure,
            'tcValue-me_method': self.linker_tcValue_me_method
        }

        self.label_link = {
            'material-tcValue': '<material>',
            'tcValue-pressure': '<pressure>',
            'tcValue-me_method': '<me_method>'
        }

        self.space_group_nlp = None

    def info(self):
        info_json = {"name": "Linking module", "version": "0.2.0"}
        return info_json

    def classify_tc(self):
        input_raw = request.forms.get("input")

        if input_raw is None:
            abort(400)

        try:
            passages_input = json.loads(input_raw)
        except:
            abort(400)

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
            abort(400)

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
        if skip_classification.lower() == 'true':
            skip_classification = True
        else:
            skip_classification = False

        if paragraph_input is None or 'tokens' not in paragraph_input or 'text' not in paragraph_input:
            abort(400)

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

    # def create_links(self):
    #     input_raw = request.forms.get("input")
    #
    #     if input_raw is None:
    #         abort(400)
    #
    #     paragraph_input = json.loads(input_raw)
    #
    #     material_tc_linked = self.linker_material_tcValue.process_paragraph(paragraph_input)
    #     tc_pressure_linked = self.linker_tcValue_pressure.process_paragraph(paragraph_input)
    #
    #     spans_map = {}
    #     for paragraphs in tc_pressure_linked:
    #         spans = paragraphs['spans'] if 'spans' in paragraphs else []
    #         for span in spans:
    #             if 'links' in span:
    #                 non_crf_links = list(filter(lambda w: w['type'] != "crf", span['links']))
    #
    #                 if len(non_crf_links) > 0:
    #                     span['links'] = non_crf_links
    #                     spans_map[span['id']] = span
    #
    #     # for span in paragraphs['spans'] if 'spans' in paragraphs else []:
    #     #     if 'links' in span and len(span['links']) > 0:
    #     #         links = span['links']
    #     #         if span['id'] in spans_map:
    #     #             spans_map[span['id']].extend(list(filter(lambda w: w['type'] != "crf", links)))
    #     #         else:
    #     #             spans_map[span['id']] = list(filter(lambda w: w['type'] != "crf", links))
    #     # span['id'] in spans_map and 'links' in spans_map[span['id']]
    #
    #     for paragraphs in material_tc_linked:
    #         for span in paragraphs['spans'] if 'spans' in paragraphs else []:
    #             if span['id'] in spans_map and 'links' in spans_map[span['id']]:
    #                 links_list = spans_map[span['id']]['links']
    #                 if 'links' in span:
    #                     span['links'].extend(links_list)
    #                 else:
    #                     span['links'] = links_list
    #
    #     # for paragraphs in material_tc_linked:
    #     #     for span in paragraphs['spans'] if 'spans' in paragraphs else []:
    #     #         if span['id'] in spans_map:
    #     #             if 'links' in span:
    #     #                 span['links'].extend(spans_map[span['id']])
    #     #             else:
    #     #                 span['links'] = spans_map[span['id']]
    #     # for paragraphs in material_tc_linked:
    #     #     material_tc_linked['relationships'].extends(tc_pressure_linked['relationships'])
    #
    #     return json.dumps(material_tc_linked)

    def classify_formula(self):
        raw = request.forms.get("input")

        if raw is None:
            abort(400)

        # raw_parsed = None
        # try:
        #     raw_parsed = json.loads(raw)
        # except JSONDecodeError as e:
        #     abort(400, e)

        # single = False
        # if type(raw_parsed) is dict:
        #     single = True
        #     formulas_raw = [raw_parsed]
        # else:
        #     formulas_raw = raw_parsed

        # result = []
        # for formula in formulas_raw:
        classes = MaterialParserWrapper().formula_to_classes(raw)
        # result.append(list(classes.keys()))

        # if single:
        #     result = result[0]

        return json.dumps(list(classes.keys()))

    # def process(self):
    #     input_raw = request.forms.get("input")
    #     input_json = json.loads(input_raw)
    #     paragraph_with_marked_tc = self.temperature_classifier.mark_temperatures_paragraph(input_json)
    #     material_tc_linked = self.linker_material_tcValue.process_paragraph_json(paragraph_with_marked_tc)
    #
    #     return self.linker_tcValue_pressure.process_paragraph_json(material_tc_linked)


    def process_space_group_text(self):
        text = request.forms.get("text")
        text_doc = self.space_group_nlp(text.lower())
        text_doc_original = self.space_group_nlp(text)
        entities = [
            {"text": str(text_doc_original[ent.start:ent.end]), "type": ent.label_, "offsetStart": ent.start_char,
             "offsetEnd": ent.end_char, "id": ent.ent_id_} for ent in text_doc.ents]

        return json.dumps(entities)


@plac.annotations(
    host=("Hostname where to run the service", "option", "host", str),
    port=("Port where to run the service", "option", "port", str),
    space_groups_patterns=("Directory containing configuration and patterns for the EntityRuler", "option", 
                           "space_groups_patterns", Path)
)
def init(host='0.0.0.0', port='8080', space_groups_patterns=None):
    app = Service()

    bottle.route('/process/link', method="POST")(app.process_link)
    bottle.route('/classify/tc', method="POST")(app.classify_tc)
    bottle.route('/classify/formula', method="POST")(app.classify_formula)

    if space_groups_patterns:
        print("Loading space group patterns...")
        space_group_nlp = spacy.load("en_core_web_sm", disable=["parser", "textcat", "ner"])
        ruler = space_group_nlp.add_pipe("entity_ruler")
        ruler.from_disk(space_groups_patterns)
        app.space_group_nlp = space_group_nlp
        bottle.route('/process/spacegroup/text', method="POST")(app.process_space_group_text)

    bottle.route('/info')(app.info)
    bottle.debug(False)
    run(host=host, port=port, debug=True)


if __name__ == "__main__":
    plac.call(init)
