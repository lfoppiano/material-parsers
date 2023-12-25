import argparse
import json
import os
from pathlib import Path

import requests

from material_data_commons import read_material_data

os.environ['NO_PROXY'] = "nims.go.jp"


# data = readMaterialData('evaluation/500papers.material.tei.xml')


class Evaluation:

    def evaluate(self, expected, predicted, log_errors=False):
        assert "The expected data should have the same cardinality as the input", len(expected) == len(
            predicted)

        total = 0
        tp = 0
        fp = 0
        fn = 0
        tn = 0
        for idx, predicted_item in enumerate(predicted):
            expected_item = expected[idx]
            # we ignore the blank items
            if predicted_item:
                if predicted_item == expected_item or predicted_item.replace(" ", "").replace("−",
                                                                                              "-") == expected_item.replace(
                    " ", "").replace("−", "-"):
                    tp += 1
                else:
                    if log_errors:
                        print("Mismatch (predicted/expected): ", predicted_item, "/", expected_item)
                    fp += 1
            else:
                if expected_item:
                    fn += 1
                else:
                    tn += 1

        return tp, fp, tn, fn

    def print_report(self, tp, fp, tn, fn):
        precision = tp / (tp + fp) if tp + fp > 0 else 0
        recall = tp / (tp + fn) if tp + fn > 0 else 0
        f1score = 2 * (precision * recall / (precision + recall)) if precision + recall > 0 else 0
        total = tp + fp + tn + fn

        print("Precision: ", precision)
        print("Recall: ", recall)
        print("F1-score: ", f1score)
        print("total: ", total)


class BaseRecogniser:
    @staticmethod
    def get_description():
        return "Generic recognised, this method should be overloaded by the super class"

    @staticmethod
    def get_name():
        return "base"

    @staticmethod
    def get_implementation_names():
        return [CederMaterialParserRecogniser_extract_formula_from_string.get_name(),
                CederMaterialParserRecogniser_parse_material_string.get_name(), MaterialParserCRF.get_name(),
                ChemDataExtraction.get_name()]

    @staticmethod
    def get_implementation(name):
        if name == ChemDataExtraction.get_name():
            return ChemDataExtraction()
        elif name == CederMaterialParserRecogniser_extract_formula_from_string.get_name():
            return CederMaterialParserRecogniser_extract_formula_from_string()
        elif name == MaterialParserCRF.get_name():
            return MaterialParserCRF()
        elif name == CederMaterialParserRecogniser_parse_material_string.get_name():
            return CederMaterialParserRecogniser_parse_material_string()

    def prepare_input_data(self, data):
        return data

    def prepare_output_data(self, data):
        return data

class MaterialParserCRF(BaseRecogniser):
    def __init__(self):
        from delft.sequenceLabelling import Sequence
        from delft.sequenceLabelling.models import BidLSTM_CRF

        self.model = Sequence("material-BidLSTM_CRF", BidLSTM_CRF.name)
        self.model.load(dir_path="./models")

    @staticmethod
    def get_description():
        return "test the MaterialParser with BidLSTM_CRF"

    @staticmethod
    def get_name():
        return "crf"

    def prepare_input_data(self, data):
        return [d['raw'] for d in data]

    def prepare_output_data(self, data):
        predicted = []
        for text in data['texts']:
            predicted.append(
                "".join([str(entity['text']) if entity['class'] == "<formula>" else "" for entity in text['entities']]))

        return predicted

    def process(self, input):
        input_prepared = self.prepare_input_data(input)
        results = self.model.tag(input_prepared, "json")
        predicted = self.prepare_output_data(results)

        return predicted

class CederMaterialParserRecogniser_parse_material_string(BaseRecogniser):
    def __init__(self):
        from material_parser.material_parser import MaterialParser

        self.mp = MaterialParser(pubchem_lookup=False, verbose=False)

    @staticmethod
    def get_description():
        return "test the method parse_material_string() from the Ceder Material Parser"

    @staticmethod
    def get_name():
        return "ceder-parse"

    def prepare_input_data(self, data):
        return [d['raw'] for d in data]

    def prepare_output_data(self, data):
        predicted = []
        for item in data:
            formula = item['material_formula'] if 'material_formula' in item else ""
            if formula.startswith("M") and 'elements_vars' in item and len(item['elements_vars']) > 0:
                element_var_replacement = "(" + ", ".join(item['elements_vars']["M"]) + ")"
                formula = formula.replace("M", element_var_replacement, 1)

            predicted.append(formula)

        return predicted

    def process(self, input):
        from sympy import SympifyError
        results = []
        input_prepared = self.prepare_input_data(input)

        for item in input_prepared:
            try:
                results.append(self.mp.parse_material_string(str(item)))
            except Exception as e:
                print("Exception for " + item + " -> " + str(e))
                results.append("")
            except SympifyError as e:
                print("Syntax error for " + item + " -> " + str(e))
                results.append("")

        predicted = self.prepare_output_data(results)

        return predicted


class CederMaterialParserRecogniser_extract_formula_from_string(BaseRecogniser):
    def __init__(self):
        from material_parser.material_parser import MaterialParser

        self.mp = MaterialParser(pubchem_lookup=False, verbose=False)

    @staticmethod
    def get_description():
        return "test the method extract_formula_from_string() from the Ceder Material Parser"

    @staticmethod
    def get_name():
        return "ceder-extract"

    def prepare_input_data(self, data):
        return [d['raw'] for d in data]

    def prepare_output_data(self, data):
        predicted = [str(formula) for formula, name in data]
        return predicted

    def process(self, input):
        from sympy import SympifyError
        results = []
        input_prepared = self.prepare_input_data(input)
        for item in input_prepared:
            try:
                results.append(self.mp.extract_formula_from_string(str(item)))
            except Exception as e:
                print("Exception for " + item + " -> " + str(e))
                results.append("")
            except SympifyError as e:
                print("Syntax error for " + item + " -> " + str(e))
                results.append("")

        predicted = self.prepare_output_data(results)

        return predicted


class ChemDataExtraction(BaseRecogniser):
    url = 'http://falcon.nims.go.jp/cde/process'

    def __init__(self):
        pass

    @staticmethod
    def get_description():
        return "test the parse with chemdata extractor"

    @staticmethod
    def get_name():
        return "cde"

    def prepare_input_data(self, data):
        return [d['raw'] for d in data]

    def prepare_output_data(self, data):
        predicted = []
        for response_json in data:
            parsed_response_content = json.loads(response_json)
            text_response = parsed_response_content[0]['label'] if len(
                parsed_response_content) > 0 and 'label' in parsed_response_content[0] else ""
            predicted.append(text_response)

        return predicted

    def process(self, input):
        results = []
        input_prepared = self.prepare_input_data(input)
        for item in input_prepared:
            try:
                data = {'text': item}

                response = requests.post(self.url, data=data)
                if response.status_code == 200:
                    results.append(response.text)
                else:
                    results.append("")

            except Exception as e:
                print("Exception for " + item + " -> " + str(e))
                results.append("")

        predicted = self.prepare_output_data(results)

        return predicted


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Material parser tests and evaluation")

    parser.add_argument("--input", help="Input file or directory in pseudo-XML", required=True, type=Path)
    parser.add_argument("--log-errors", help="Log mismatches", required=False, action="store_true", default=False)
    parser.add_argument("--experiment", help="Run single experiment", required=False,
                        choices=BaseRecogniser.get_implementation_names() + ['all'],
                        type=str, default="all")

    args = parser.parse_args()
    input_path = args.input
    log_errors = args.log_errors
    experiment = args.experiment

    data = read_material_data(input_path)

    expected = [d['entities']['formula'] if 'entities' in d and 'formula' in d['entities'] else "" for d in data]

    evaluation = Evaluation()

    experiment_keys = BaseRecogniser.get_implementation_names() if experiment == "all" else [experiment]

    for experiment_name in experiment_keys:
        recogniser = BaseRecogniser.get_implementation(experiment_name)
        predicted = recogniser.process(data)
        print("Report ", recogniser.get_description())
        evaluation.print_report(*evaluation.evaluate(expected, predicted, log_errors=log_errors))
