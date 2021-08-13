import json

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

    def info(self):
        info_json = {"name": "Linking module", "version": "0.2.0"}
        return info_json

    def classify_tc(self):
        input_raw = request.forms.get("input")

        if input_raw is None:
            abort(400)

        return self.temperature_classifier.mark_temperatures_paragraph_json(input_raw)

    def process_link_single(self):
        '''
        Process links from the input data using the type of link extractor that are provider, as a json list in the
        parameter 'types'.
        skip_classification = True will skip the classification of the linkable entities
        '''
        input_raw = request.forms.get("input")
        paragraph_input = None
        try:
            paragraph_input = json.loads(input_raw)
        except:
            abort(400)

        link_types_as_list = json.loads(request.forms.get("types")) if request.forms.get(
            "types") is not None else self.linker_map.keys()
        skip_classification = request.forms.get("skip_classification") if request.forms.get(
            "skip_classification") is not None else False

        if skip_classification.lower() == 'true':
            skip_classification = True
        else:
            skip_classification = False

        if paragraph_input is None or 'spans' not in paragraph_input or 'tokens' not in paragraph_input or 'text' not in paragraph_input:
            abort(400)

        if not skip_classification:
            marked_tc_paragraph = self.temperature_classifier.mark_temperatures_paragraph(paragraph_input)

            spans_map = {}
            spans_processed = marked_tc_paragraph['spans'] if 'spans' in marked_tc_paragraph else []
            tc_spans = list(filter(lambda w: w['type'] == "<tcValue>", spans_processed))

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

        return json.dumps(paragraph_input)

    def process_link_bulk(self):
        input_raws = request.forms.get("input")
        link_type = request.forms.get("type")

        paragraph_input = json.loads(input_raws)

        processed_linked = self.linker_map[link_type].process_paragraph(paragraph_input)

        return json.dumps(processed_linked)

    def create_links(self):
        input_raw = request.forms.get("input")

        if input_raw is None:
            abort(400)

        paragraph_input = json.loads(input_raw)

        material_tc_linked = self.linker_material_tcValue.process_paragraph(paragraph_input)
        tc_pressure_linked = self.linker_tcValue_pressure.process_paragraph(paragraph_input)

        spans_map = {}
        for paragraphs in tc_pressure_linked:
            spans = paragraphs['spans'] if 'spans' in paragraphs else []
            for span in spans:
                if 'links' in span:
                    non_crf_links = list(filter(lambda w: w['type'] != "crf", span['links']))

                    if len(non_crf_links) > 0:
                        span['links'] = non_crf_links
                        spans_map[span['id']] = span

        # for span in paragraphs['spans'] if 'spans' in paragraphs else []:
        #     if 'links' in span and len(span['links']) > 0:
        #         links = span['links']
        #         if span['id'] in spans_map:
        #             spans_map[span['id']].extend(list(filter(lambda w: w['type'] != "crf", links)))
        #         else:
        #             spans_map[span['id']] = list(filter(lambda w: w['type'] != "crf", links))
        # span['id'] in spans_map and 'links' in spans_map[span['id']]

        for paragraphs in material_tc_linked:
            for span in paragraphs['spans'] if 'spans' in paragraphs else []:
                if span['id'] in spans_map and 'links' in spans_map[span['id']]:
                    links_list = spans_map[span['id']]['links']
                    if 'links' in span:
                        span['links'].extend(links_list)
                    else:
                        span['links'] = links_list

        # for paragraphs in material_tc_linked:
        #     for span in paragraphs['spans'] if 'spans' in paragraphs else []:
        #         if span['id'] in spans_map:
        #             if 'links' in span:
        #                 span['links'].extend(spans_map[span['id']])
        #             else:
        #                 span['links'] = spans_map[span['id']]
        # for paragraphs in material_tc_linked:
        #     material_tc_linked['relationships'].extends(tc_pressure_linked['relationships'])

        return json.dumps(material_tc_linked)

    def classify_formula(self):
        formula_raw = request.forms.get("input")
        classes = MaterialParserWrapper().formula_to_classes(formula_raw)

        return json.dumps(list(classes.keys()))

    def process(self):
        input_raw = request.forms.get("input")
        input_json = json.loads(input_raw)
        paragraph_with_marked_tc = self.temperature_classifier.mark_temperatures_paragraph(input_json)
        material_tc_linked = self.linker_material_tcValue.process_paragraph_json(paragraph_with_marked_tc)

        return self.linker_tcValue_pressure.process_paragraph_json(material_tc_linked)


@plac.annotations(
    host=("Hostname where to run the service", "option", "host", str),
    port=("Port where to run the service", "option", "port", str),
)
def init(host='0.0.0.0', port='8080'):
    app = Service()

    bottle.route('/process/link/single', method="POST")(app.process_link_single)
    bottle.route('/process/link/bulk', method="POST")(app.process_link_bulk)
    bottle.route('/classify/tc', method="POST")(app.classify_tc)
    bottle.route('/classify/formula', method="POST")(app.classify_formula)
    bottle.route('/info')(app.info)
    bottle.debug(False)
    run(host=host, port=port, debug=True)


if __name__ == "__main__":
    plac.call(init)
