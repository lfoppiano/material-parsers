import copy
import re
from collections import defaultdict
from typing import Union

from delft.sequenceLabelling import Sequence
from delft.sequenceLabelling.models import BidLSTM_CRF

from grobid_superconductors.material_parser.materialParserWrapper import MaterialParserWrapper

REPLACEMENT_SYMBOLS_VARIABLES = [(" ͑", "")]
REPLACEMENT_SYMBOLS_VALUES = [
    (" ͑", ""),
    ("¼", ""),
    ("et al", ""),
    ("etc\\.?", "")
]

REPLACEMENT_SYMBOLS = [
    ("À", "-"),
    ("Ϸ", "≈"),
    ("¼", "-"),
    (" ͑", "")
]

ENGLISH_ALPHABETH = "xyzabcdefghijklmnopqrstuvw"

PATTERN_NAMES_TO_AVOID = r"[A-Z][a-z]{1,3}[- ]*\\d{3,5}"


class MaterialParserML:
    def __init__(self, formula_parser: MaterialParserWrapper = None, model_path: str = "resources/data/models") -> None:
        self.model = Sequence("material-BidLSTM_CRF", BidLSTM_CRF.name)
        # self.model = Sequence("material-BERT_CRF", BERT_CRF.name)
        self.model.load(dir_path=model_path)
        self.material_parser_wrapper = formula_parser

    def process(self, input_data: Union[str, list]):
        if type(input_data) == str:
            input_data = [input_data]

        results = self.model.tag(input_data, "json")

        return results

    def extract_results(self, output):
        results = []
        for example in output['texts']:
            shapes = []
            dopings = []
            fabrications = []
            substrates = []
            prefixed_values = []

            materials = []
            material = defaultdict(lambda: None, {})
            entities = example['entities'] if 'entities' in example else []

            processing_variable = None

            for entity in entities:
                label = entity['class'].replace(">", "").replace("<", "")
                text = entity['text']

                if label == 'doping':
                    dopings.append(text)
                elif label == 'fabrication':
                    fabrications.append(text)
                elif label == 'shape':
                    shapes.append(text)
                elif label == 'substrate':
                    substrates.append(text)
                elif label == 'variable':
                    variable = post_process_variable(text)
                    if processing_variable:
                        if variable != processing_variable:
                            processing_variable = variable
                    else:
                        processing_variable = variable

                elif label == 'value':
                    if processing_variable:
                        values = extract_and_filter_variable_values(text)
                        if 'variables' in material and processing_variable in material['variables']:
                            material['variables'][processing_variable].extend(values)
                        else:
                            material['variables'] = {processing_variable: values}

                        if prefixed_values:
                            material['variables'][processing_variable].extends(prefixed_values)
                            prefixed_values = []
                    else:
                        if "<" in text:
                            prefixed_values.append(text)
                        else:
                            print("Got a value but the processing variable is empty. Value: " + text)

                elif label in material:
                    materials.append(material)
                    material = {label: text}
                else:
                    material[label] = text

            if len(material.keys()) > 0:
                materials.append(material)
            else:
                print("Ponyo")

            materials = process_property(materials, 'doping', dopings)
            materials = process_property(materials, 'substrate', substrates)
            materials = process_property(materials, 'shape', shapes)

            for material in materials:
                if material['formula']:
                    material['formula'] = {'raw_value': material['formula']}

                resolved_formulas = resolve_variables(material)

                # If there are no resolved formulas (no variable), but there is a raw formula, add it
                if not resolved_formulas and (
                    material['formula']['raw_value'] is not None and material['formula']['raw_value'].strip()):
                    resolved_formulas.append(material['formula']['raw_value'])

                # Expand formulas of type (A, B)blabla
                if resolved_formulas:
                    resolved_and_expanded_formulas = []
                    for f in resolved_formulas:
                        for exp_f in expand_formula(f):
                            new_f = {
                                "raw_value": exp_f,
                            }
                            if self.material_parser_wrapper:
                                compo = self.material_parser_wrapper.formula_to_composition(exp_f)
                                if compo and 'composition' in compo:
                                    new_f["composition"] = compo

                            resolved_and_expanded_formulas.append(new_f)

                    material['resolved_formulas'] = resolved_and_expanded_formulas

                # If we don't have any formula but a name, let's try to calculate the formula from the name...
                if self.material_parser_wrapper:
                    if (
                        material['formula'] is None or not material['formula'][
                        'raw_value'].strip()) and material.name and not re.match(PATTERN_NAMES_TO_AVOID,
                                                                                 material['name'].replace("  ", " ")):

                        converted_formula = self.material_parser_wrapper.name_to_formula(material.name)
                        formula = None

                        if converted_formula['formula']:
                            formula = {'raw_value': converted_formula['formula']}
                            material['formula'] = formula

                        if converted_formula.composition:
                            if formula is None:
                                formula = {}
                            formula['composition'] = converted_formula['composition']
                            material['formula'] = formula

            results.extend(materials)

        return results


def process_property(materials, property_name, property_values_list):
    if len(property_values_list) > 1:
        # Multiple doping AND single material -> create multiple materials
        if len(materials) == 1:
            materials = []
            for doping in property_values_list:
                new_material = copy.copy(materials[0])
                new_material[property_name] = doping
                # Substrate and fabrication will be added later as single or joined information
                materials.append(new_material)
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
        'formula']) or not ('raw_value' in material['formula'] and material['formula']['raw_value']):
        return []

    formula_raw_value = material['formula']['raw_value']

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
