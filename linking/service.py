import json

import bottle
import plac
from bottle import request, run

from linking_module import RuleBasedLinker, CriticalTemperatureClassifier
from materialParserWrapper import MaterialParserWrapper

bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024 * 1024

class Service(object):
    def __init__(self):
        self.linker_material_tc = RuleBasedLinker(source="<tcValue>", destination="<material>")
        self.linker_tc_pressure = RuleBasedLinker(source="<pressure>", destination="<tcValue>")
        self.temperature_classifier = CriticalTemperatureClassifier()

    def info(self):
        returnText = "Python utilities wrapper as a micro-service."
        return returnText

    def mark_critical_temperature(self):
        input_raw = request.forms.get("input")

        return self.temperature_classifier.mark_temperatures_paragraph_json(input_raw)

    def create_links(self):
        input_raw = request.forms.get("input")
        paragraph_input = json.loads(input_raw)

        material_tc_linked = self.linker_material_tc.process_paragraph(paragraph_input)
        tc_pressure_linked = self.linker_tc_pressure.process_paragraph(paragraph_input)

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

    def resolve_class(self):
        formula_raw = request.forms.get("input")
        classes = MaterialParserWrapper().formula_to_classes(formula_raw)

        return json.dumps(list(classes.keys()))

    def process(self):
        input_raw = request.forms.get("input")
        input_json = json.loads(input_raw)
        paragraph_with_marked_tc = self.linker_material_tc.mark_temperatures_paragraph(input_json)

        material_tc_linked = self.linker_material_tc.process_paragraph_json(paragraph_with_marked_tc)
        return self.linker_tc_pressure.process_paragraph_json(material_tc_linked)


@plac.annotations(
    host=("Hostname where to run the service", "option", "host", str),
    port=("Port where to run the service", "option", "port", str),
)
def init(host='0.0.0.0', port='8080'):
    app = Service()

    bottle.route('/process/links', method="POST")(app.create_links)
    bottle.route('/process/all', method="POST")(app.process)
    bottle.route('/process/tc', method="POST")(app.mark_critical_temperature)
    bottle.route('/process/formula', method="POST")(app.resolve_class)
    bottle.route('/info')(app.info)
    bottle.debug(False)
    run(host=host, port=port, debug=True)


if __name__ == "__main__":
    plac.call(init)
