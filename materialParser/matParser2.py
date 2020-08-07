from bs4 import BeautifulSoup, Tag
from delft.sequenceLabelling import Sequence
from delft.sequenceLabelling.models import BidLSTM_CRF
from material_parser.material_parser import MaterialParser
from sympy import SympifyError

from material2class import Material2Class

mp = MaterialParser(pubchem_lookup=False, verbose=False)
data = []

raw_data = []
## Loading evaluation data
# with open('evaluation/500papers.material.tei.xml', 'r') as fp:
with open('evaluation/eval2.xml', 'r') as fp:
    doc = fp.read()

    soup = BeautifulSoup(doc, 'xml')

    for i, pTag in enumerate(soup.materials):
        if type(pTag) == Tag:
            item = {
                'raw': str(pTag.get_text())
            }
            raw_data.append(str(pTag.get_text()))
            data.append(item)
            for child in pTag.children:
                if type(child) == Tag:
                    item[child.name] = child.get_text()
                    # print(child.get_text())
                    # print(child.name)

## Test 2: Application of material parser (crf) + ceder material parser

model = Sequence("material", BidLSTM_CRF.name)
model.load(dir_path="./models")
tags = model.tag(raw_data, "json")

for tag in tags['texts'] if 'texts' in tags else []:
    print(tag)
    variables = {}
    lastVariable = ""
    name = ""
    formula = ""

    for entity in tag['entities'] if 'entities' in tag else []:
        if entity['class'] == "<variable>":
            lastVariable = str(entity['text'])
            variables[lastVariable] = []
        if entity['class'] == "<value>":
            if lastVariable:
                variables[lastVariable].append(str(entity['text']))
        if entity['class'] == "<formula>":
            formula = str(entity['text']).replace(" ", "")
        elif entity['class'] == "<name>":
            name = str(entity['text'])

    if formula:
        try:
            composition = mp.formula2composition(formula)
            print("formula2composition: " + formula + " -> " + str(composition))

            if composition:
                vars = composition['amounts_vars']
                elements = composition['elements_vars']

                if len(variables.keys()) > 0:
                    print("Examining the variables in " + str(variables))
                    for key, value in variables.items():
                        if key in vars:
                            vars[key] = value
                        elif key in elements:
                            elements[key] = value
                        else:
                            print("variable " + key + "was not found.")

            reconstructed_formula = mp.reconstruct_formula_from_string(formula)
            print("reconstruct_formula_from_string: " + formula + " -> " + str(reconstructed_formula))

            split_formula = mp.split_formula_into_compounds(formula)
            print("split_formula_into_compounds: " + formula + " -> " + str(split_formula))
        except SympifyError as e:
            print("Error when parsing: ", str(e))

        clazz = Material2Class().get_class(formula)

        print("Formula2Class: " + formula + " -> " + clazz)

    if name:
        try:
            formula = mp.string2formula(name)
            print("String2formula: " + name + " -> " + str(formula))
        except SympifyError as e:
            print("Error when parsing: ", str(e))
