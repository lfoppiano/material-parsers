import re
from collections import defaultdict
from typing import Union

from delft.sequenceLabelling import Sequence
from delft.sequenceLabelling.models import BidLSTM_CRF

from material_parsers.commons.grobid_tokenizer import tokenizeSimple
from material_parsers.commons.utils import rewrite_comparison_symbol
from material_parsers.material_parser.material_parser_formulas import MaterialParserFormulas

COMPARE_SIGNS = ["≤", "<", "⩽"]
REPLACEMENT_SYMBOLS_VARIABLES = [(" ͑", "")]
REPLACEMENT_SYMBOLS_VALUES = [
    (" ͑", ""),
    ("¼", ""),
    ("et al", ""),
    ("etc\\.?", ""),
    ("≃", "=")
]

REPLACEMENT_SYMBOLS = [
    ("À", "-"),
    ("Ϸ", "≈"),
    ("¼", "-"),
    (" ͑", "")
]

ENGLISH_ALPHABETH = "xyzabcdefghijklmnopqrstuvw"

PATTERN_NAMES_TO_AVOID = r"[A-Z][a-z]{1,3}[- ]*\\d{3,5}"

REPLACEMENT_FORMULA = [
    ()
]


class MaterialParserML:
    def __init__(self,
                 formula_parser: MaterialParserFormulas = None,
                 model_path: Union[str, None] = "resources/data/models"
                 ) -> None:
        if model_path:
            self.model = Sequence("material-parsers-BidLSTM_CRF", BidLSTM_CRF.name)
            # self.model = Sequence("material-BERT_CRF", BERT_CRF.name)
            self.model.load(dir_path=model_path)
        self.material_parser_wrapper = formula_parser

    def process(self, input_data: Union[str, list]):
        if type(input_data) is str:
            input_data = [input_data]

        tokenizer_input = [tokenizeSimple(t) for t in input_data]
        results = self.model.tag(tokenizer_input, "text")
        if len(input_data) == 1 and len(results) > 1:
            results = results[:-1]

        for example in results:
            for i, item in enumerate(example):
                if item[1].startswith('I'):
                    if i == 0:
                        item[1].replace("I-", "B-")
                    else:
                        if example[i - 1][2:] != example[i][2:]:
                            item[1] = item[1].replace("I-", "B-")

        clusters = cluster_by_label(results)

        parsed_results = [
            [
                {key: value for key, value in dict(material).items() if value is not None and value != ""} for material in
                materials
            ] for materials in self.extract_results(clusters)
        ]

        return parsed_results

    def extract_results(self, output):
        results = []
        for example in output:
            shapes = []
            dopings = []
            fabrications = []
            substrates = []
            prefixed_values = []

            materials = []
            material = defaultdict(lambda: None, {})

            processing_variable = None
            other_properties = False

            for entity in example:
                label = entity['class'].replace(">", "").replace("<", "")
                text = entity['text']

                if label == 'doping':
                    dopings.append(text)
                    other_properties = True
                elif label == 'fabrication':
                    fabrications.append(text)
                    other_properties = True
                elif label == 'shape':
                    shapes.append(text)
                    other_properties = True
                elif label == 'substrate':
                    substrates.append(text)
                    other_properties = True
                elif label == 'variable':
                    variable = post_process_variable(text)
                    other_properties = True
                    if processing_variable:
                        if variable != processing_variable and str.strip(variable) != "":
                            processing_variable = variable
                    else:
                        processing_variable = variable

                elif label == 'value':
                    other_properties = True
                    if processing_variable:
                        values = extract_and_filter_variable_values(text)
                        if 'variables' in material and processing_variable in material['variables']:
                            material['variables'][processing_variable].extend(values)
                        else:
                            material['variables'] = {
                                processing_variable: values
                            }

                        if prefixed_values:
                            material['variables'][processing_variable].extend(prefixed_values)
                            prefixed_values = []
                    else:
                        if any(map(lambda x: x in text, COMPARE_SIGNS)):
                            prefixed_values.append(rewrite_comparison_symbol(text))
                        elif "=" in text:
                            split = text.split("=")
                            processing_variable = split[0]
                            prefixed_values.append(split[1])
                        # elif any(map(lambda x: x in text, ["≥", ">"])):
                        else:
                            print(f"Got a value but the processing variable is empty. Value: {text}, {example}")


                elif label in material:
                    materials.append(material)
                    material = defaultdict(lambda: None, {label: text})
                else:
                    material[label] = text

            if len(material.keys()) > 0:
                if len(fabrications) > 0:
                    material['fabrication'] = " ".join(fabrications)
                materials.append(material)
            elif len(material.keys()) == 0 and not other_properties:
                print(f"Empty material in example {example}")
                results.append({})
                continue

            materials = process_property(materials, 'doping', dopings)
            materials = process_property(materials, 'substrate', substrates)
            materials = process_property(materials, 'shape', shapes)

            for material in materials:
                if 'formula' in material and material['formula']:
                    material['formula'] = {'rawValue': material['formula']}

                resolved_formulas = resolve_variables(material)

                # If there are no resolved formulas (no variable), but there is a raw formula, add it
                if not resolved_formulas and 'formula' in material and material['formula'] and (
                    material['formula']['rawValue'] is not None and material['formula']['rawValue'].strip()):
                    resolved_formulas.append(material['formula']['rawValue'])

                # Expand formulas of type (A, B)blabla
                if resolved_formulas:
                    resolved_and_expanded_formulas = []
                    for f in resolved_formulas:
                        for exp_f in expand_formula(f):
                            new_f = {
                                "rawValue": exp_f,
                            }
                            if self.material_parser_wrapper:
                                try:
                                    compo = self.material_parser_wrapper.formula_to_composition(exp_f)
                                    if compo and 'composition' in compo:
                                        new_f["formulaComposition"] = compo['composition']
                                except ValueError:
                                    print(f"Cannot parse (formula to composition) {exp_f} with the material parser")
                                except IndexError as ie:
                                    print(f"Cannot parse (formula to composition) {exp_f}, index error: {ie}")

                            resolved_and_expanded_formulas.append(new_f)

                    material['resolvedFormulas'] = resolved_and_expanded_formulas

                # If we don't have any formula but a name, let's try to calculate the formula from the name...
                if self.material_parser_wrapper:
                    if (material['formula'] is None or (material['formula'] and not material['formula'][
                        'rawValue'].strip())) and material['name'] and not re.match(PATTERN_NAMES_TO_AVOID,
                                                                                    material['name'].replace("  ",
                                                                                                             " ")):
                        converted_formula = {}
                        try:
                            converted_formula = self.material_parser_wrapper.name_to_formula(material['name'])
                        except ValueError:
                            print(f"Cannot parse (name to formula) {material['name']} with material parser")

                        formula = None

                        if 'formula' in converted_formula and converted_formula['formula']:
                            formula = {'rawValue': converted_formula['formula']}
                            material['formula'] = formula

                        if 'composition' in converted_formula and converted_formula['composition']:
                            if formula is None:
                                formula = {}
                            formula['formulaComposition'] = converted_formula['composition']
                            material['formula'] = formula

            results.append(materials)

        return results


def process_property(materials, property_name, property_values_list):
    if len(property_values_list) > 1:
        # Multiple doping AND single material -> create multiple materials
        if len(materials) == 1:
            for doping in property_values_list:
                new_material = defaultdict(lambda: None, materials[0])
                new_material[property_name] = doping
                # Substrate and fabrication will be added later as single or joined information
                materials.append(new_material)
            # materials = []
        else:
            # Multiple doping AND multiple materials -> merge doping ratio and assign to each material
            single_doping = ", ".join(property_values_list)
            for mat in materials:
                mat[property_name] = single_doping

    elif len(property_values_list) == 1:
        assign_single_property(materials, property_name, property_values_list[0])
    return materials


def assign_single_property(materials, property_name, property_value):
    if len(materials) == 1:
        materials[0][property_name] = property_value
    elif len(materials) > 1:
        for mat in materials:
            mat[property_name] = property_value

    return materials


def post_process_value(value: str) -> str:
    temp = value
    for replacement_symbol in REPLACEMENT_SYMBOLS_VALUES:
        temp = temp.replace(replacement_symbol[0], replacement_symbol[1])
    return temp


def extract_and_filter_variable_values(value):
    split = re.split(r',|;|or|and', value)
    return list(filter(str.strip, map(post_process_value, map(str.strip, split))))


def post_process_variable(variable: str) -> str:
    temp = variable
    for replacement_symbol in REPLACEMENT_SYMBOLS_VARIABLES:
        temp = temp.replace(replacement_symbol[0], replacement_symbol[1])
    return temp


def resolve_variables(material):
    if not ('variables' in material and material['variables']) or not ('formula' in material and material[
        'formula']) or not ('rawValue' in material['formula'] and material['formula']['rawValue']):
        return []

    formula_raw_value = material['formula']['rawValue']

    if not any(variable in formula_raw_value for variable in material['variables']):
        return []

    variables = set(material['variables'].keys())
    contained_variables = {var for var in variables if var in formula_raw_value}

    output_formulas_string = []

    if not contained_variables:
        return output_formulas_string

    if len(contained_variables) != len(variables):
        print("While processing the variables, some are not present in the material formula and "
              "won't be substituted: " + str(variables - contained_variables))

    map_of_contained_variables = {variable: material['variables'][variable] for variable in contained_variables}

    try:
        generate_permutations(map_of_contained_variables, list(contained_variables), output_formulas_string,
                              (0, 0), formula_raw_value)
    except ValueError:
        cleaned_map_of_contained_variables = {}
        for variable in map_of_contained_variables:
            cleaned_list = [re.sub("[^\\-0-9.]+", "", value) for value in map_of_contained_variables[variable]]
            cleaned_map_of_contained_variables[variable] = cleaned_list

        try:
            generate_permutations(cleaned_map_of_contained_variables, list(contained_variables),
                                  output_formulas_string, (0, 0), formula_raw_value)
        except ValueError:
            print("Cannot replace variables " + str(list(variables)))

    return output_formulas_string


def generate_permutations(input_dict, key_list, result, depth, formula):
    variable_index, value_index = depth

    variable = key_list[variable_index]
    value = input_dict[variable][value_index]

    if value_index == len(input_dict[variable]) - 1 and variable_index == len(key_list) - 1:
        result.append(replace_variable(formula, variable, value))
        return

    if variable_index == len(key_list) - 1:
        result.append(replace_variable(formula, variable, value))
        generate_permutations(input_dict, key_list, result, (variable_index, value_index + 1), formula)
        return

    for i in range(len(input_dict[variable])):
        generate_permutations(input_dict, key_list, result, (variable_index + 1, 0),
                              replace_variable(formula, variable, input_dict[variable][i]))


def replace_variable(formula, variable, value):
    return_formula = formula
    start_searching = 0

    while formula.find(variable, start_searching) > -1:
        variable_index = formula.find(variable, start_searching)

        if variable_index > -1:
            if formula.startswith("-", variable_index - 1) or formula.startswith("\u2212", variable_index - 1):
                end_search = variable_index - 1
                while end_search > 0 and formula[end_search - 1].isdigit():
                    end_search -= 1

                if end_search < variable_index - 1:
                    number = formula[end_search: variable_index - 1]
                    sub = float(number) - float(value)
                    sub = round(sub, 2)
                    return_formula = return_formula.replace(number + formula[variable_index - 1] + variable,
                                                            str(sub), 1)
                else:
                    if value.startswith("-") or value.startswith("\u2212"):
                        return_formula = return_formula.replace(formula[variable_index - 1] + variable,
                                                                value[1:], 1)
                    else:
                        return_formula = return_formula.replace(variable, value, 1)
            else:
                if variable_index + len(variable) < len(formula) - 1:
                    if not formula[variable_index + len(variable)].islower():
                        return_formula = return_formula.replace(variable, value, 1)
                elif variable_index + len(variable) == len(formula):
                    return_formula = return_formula.replace(variable, value, 1)
                else:
                    print("The variable " + variable + " substitution with value " + value + " into " + formula)

        start_searching = variable_index + 1

    return return_formula


def expand_formula(formula):
    regex = r"^ ?\(([A-Za-z, ]+)\)(.*)"
    formula_dopant_pattern = re.compile(regex)
    formula_dopant_matcher = formula_dopant_pattern.match(formula)

    name_material_pattern = re.compile("-[0-9]+")
    expanded_formulas = []

    if formula_dopant_matcher:
        dopants = str(formula_dopant_matcher.group(1))
        formula_without_dopants = str.strip(formula_dopant_matcher.group(2))
        splitted_dopants = [d.strip() for d in dopants.split(",") if d.strip()]

        name_material_matcher = name_material_pattern.search(formula_without_dopants)
        if name_material_matcher:
            for dopant in splitted_dopants:
                expanded_formulas.append(f"{dopant}{formula_without_dopants}")
        else:
            if len(splitted_dopants) == 1:
                expanded_formulas.append(formula)
            elif len(splitted_dopants) == 2:
                expanded_formulas.append(f"{splitted_dopants[0]} 1-x {splitted_dopants[1]} x {formula_without_dopants}")
            elif 2 < len(splitted_dopants) < len(ENGLISH_ALPHABETH):
                alphabet = list(ENGLISH_ALPHABETH)
                sb = [f"{splitted_dopants[0]} 1"]
                sb2 = []
                for i in range(len(splitted_dopants) - 1):
                    sb2.append(f"-{alphabet[i]}")
                sb2.append(" ")
                sb.append("".join(sb2))
                for i in range(1, len(splitted_dopants)):
                    split = splitted_dopants[i]
                    sb.append(f"{split} {alphabet[i - 1]} ")
                sb.append(str.strip(formula_without_dopants))
                expanded_formulas.append("".join(sb))
            else:
                raise RuntimeError(f"The formula {formula} cannot be expanded.")
    else:
        return [formula]

    return expanded_formulas


def extract_label(item):
    if type(item) is not str:
        item = item[1]
    if item == "O":
        return "O"
    return item.split('-<')[1][:-1]


def cluster_by_label(results):
    def is_start_of_sequence(item):
        return item[1].startswith('B-')

    groups = []
    for result in results:

        sequences = []
        current_sequence = []
        for idx, item in enumerate(result):
            if item[1] == "O":
                continue
            if is_start_of_sequence(item):
                if len(current_sequence) > 0:
                    sequences.append(current_sequence)
                    current_sequence = []
            current_sequence.append(item)

        if len(current_sequence) > 0:
            sequences.append(current_sequence)

        groups.append(
            [{"text": str.strip("".join([seq[0] for seq in sequence])), "class": extract_label(sequence[0])} for
             sequence in sequences])

    return groups
