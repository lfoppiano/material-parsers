import argparse
import json

import bottle
from bottle import request, run, route

from linking_module import RuleBasedLinker, CriticalTemperatureClassifier
from materialParserWrapper import MaterialParserWrapper

bottle.BaseRequest.MEMFILE_MAX = 1024 * 1024 * 1024

linker_material_tc = RuleBasedLinker(source="<tcValue>", destination="<material>")
linker_tc_pressure = RuleBasedLinker(source="<pressure>", destination="<tcValue>")
temperature_classifier = CriticalTemperatureClassifier()

@route('/info')
def info():
    returnText = "Python utilities wrapper as a micro-service."
    return returnText

@route('/process/tc', method="POST")
def mark_critical_temperature():
    input_raw = request.forms.get("input")

    return temperature_classifier.mark_temperatures_paragraph_json(input_raw)

@route('/process/links', method="POST")
def create_links():
    input_raw = request.forms.get("input")
    paragraph_input = json.loads(input_raw)

    material_tc_linked = linker_material_tc.process_paragraph(paragraph_input)
    tc_pressure_linked = linker_tc_pressure.process_paragraph(paragraph_input)

    spans_map = {}
    for paragraphs in tc_pressure_linked:
        for span in paragraphs['spans'] if 'spans' in paragraphs else []:
            if 'links' in span and span['id'] in spans_map and 'links' in spans_map[span['id']] \
                and len(list(filter(lambda w: w['type'] != "crf", spans_map[span['id']]['links']))) > 0:
                spans_map[span['id']] = span

    for paragraphs in material_tc_linked:
        for span in paragraphs['spans'] if 'spans' in paragraphs else []:
            if span['id'] in spans_map and 'links' in spans_map[span['id']]:
                links_list = list(filter(lambda w: w['type'] != "crf", spans_map[span['id']]['links']))
                if 'links' in span:
                    span['links'].extend(links_list)
                else:
                    span['links'] = links_list

    # for paragraphs in material_tc_linked:
    #     material_tc_linked['relationships'].extends(tc_pressure_linked['relationships'])

    return json.dumps(material_tc_linked)

@route('/process/formula', method="POST")
def resolve_class():
    formula_raw = request.forms.get("input")
    classes = MaterialParserWrapper().formula_to_classes(formula_raw)

    return json.dumps(list(classes.keys()))

@route('/process/all', method="POST")
def process():
    input_raw = request.forms.get("input")
    input_json = json.loads(input_raw)
    paragraph_with_marked_tc = linker_material_tc.mark_temperatures_paragraph(input_json)

    material_tc_linked = linker_material_tc.process_paragraph_json(paragraph_with_marked_tc)
    return linker_tc_pressure.process_paragraph_json(material_tc_linked)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Linking module API")
    parser.add_argument("--host", help="Hostname to be bound the service", type=str, required=False, default="0.0.0.0")
    parser.add_argument("--port", help="Port to be listening to", type=str, required=False, default="8090")

    args = parser.parse_args()

    host = args.host
    port = args.port

    run(host=host, port=port, debug=True)
