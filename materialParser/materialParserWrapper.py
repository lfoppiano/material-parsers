# from material_parser.material_parser import MaterialParser
import re

from material_parser.material_parser import MaterialParser
from sympy import SympifyError

from material2class import Material2Class, Material2Tags
from material_data_commons import read_material_data


class MaterialParserWrapper:
    # mp = MaterialParser()
    material2class = Material2Class()
    material2tags = Material2Tags()

    # def formula_to_composition(self, formula):
    #     composition = self.mp.formula2composition(formula)
    #
    #     if 'elements' in composition:
    #         return composition
    #
    #     else:
    #         return {}
    #
    def formula_to_class(self, formula):
        return self.material2class.get_class(formula)

    def formula_to_classes(self, formula):
        return self.material2tags.get_classes(formula)

    # def name_to_formula(self, name):
    #     formula = self.mp.string2formula(name)
    #
    #     return formula


class MaterialParseMod():
    def __init__(self):
        from delft.sequenceLabelling import Sequence
        from delft.sequenceLabelling.models import BidLSTM_CRF

        self.model = Sequence("material", BidLSTM_CRF.name)
        self.model.load(dir_path="./models")

        self.mp = MaterialParser(pubchem_lookup=False, verbose=False)

    def process(self, text: str):
        tags = self.model.tag([text], "json")

        for tag in tags['texts'] if 'texts' in tags else []:
            print("===>>>" + str(tag) + "<<<===")
            variables = {}
            lastVariable = ""
            name = ""
            formula = ""

            for entity in tag['entities'] if 'entities' in tag else []:
                if entity['class'] == "<variable>":
                    lastVariable = str(entity['text'])
                    variables[lastVariable] = []
                elif entity['class'] == "<value>":
                    if lastVariable:
                        variables[lastVariable].append(str(entity['text']))
                elif entity['class'] == "<formula>":
                    formula = str(entity['text']).replace(" ", "")
                elif entity['class'] == "<name>":
                    name = str(entity['text'])

            if variables:
                processed_values = {}
                for var, vals in variables.items():
                    for v in vals:
                        if v not in processed_values:
                            processed_values[var] = [x.strip() for x in re.compile(',|or|and|,|;').split(v)]
                        else:
                            processed_values[var] += [x.strip() for x in    re.compile(',|or|and|,|;').split(v)]

            if formula:
                # if len(variables.keys()) > 0:
                #     formula + '(' + " ".join([key + '=' + ", ".join(variables[key]) for key in variables.keys()]) + ')'

                try:
                    composition = self.mp.formula2composition(formula, elements_vars_suggestions=processed_values)
                    print("Extract composition from formula: " + formula + " -> " + str(composition))

                    # if composition:
                    #     vars = composition['amounts_vars']
                    #     elements = composition['elements_vars']


                    # reconstructed_formula = mp.reconstruct_formula_from_string(formula)
                    # print("reconstruct_formula_from_string: " + formula + " -> " + str(reconstructed_formula))

                    # split_formula = mp.split_formula_into_compounds(formula)
                    # print("split_formula_into_compounds: " + formula + " -> " + str(split_formula))
                except SympifyError as e:
                    print("Error when parsing: ", str(e))

            if name:
                try:
                    formula = self.mp.string2formula(name)
                    print("String2formula: " + name + " -> " + str(formula))
                except SympifyError as e:
                    print("Error when parsing: ", str(e))


if __name__ == '__main__':

    data = read_material_data('evaluation/eval2.xml')
    raw_data = [d['raw'] for d in data]

    for text in raw_data:
        MaterialParseMod().process(text)
