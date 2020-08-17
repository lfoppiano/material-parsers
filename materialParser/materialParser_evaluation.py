from material_parser.material_parser import MaterialParser
from sympy import SympifyError

from material_data_commons import readMaterialData

mp = MaterialParser(pubchem_lookup=False, verbose=False)
data = readMaterialData('evaluation/500papers.material.tei.xml')

def test1_MaterialParser_from_raw():
    print(" Test 1a: test the method parse_material_string() from the Material Parser")
    ## TEST 1: ability to parser a more complext material string
    correct = 0
    wrong = 0
    total = 0

    for item in data:
        # print(item['raw'])
        try:
            result = mp.parse_material_string(str(item['raw']))

            if 'formula' in item['entities']:
                total += 1
                if 'material_formula' in result:
                    if result['material_formula'] == item['entities']['formula']:
                        correct += 1
                    else:
                        wrong += 1

                else:
                    wrong += 1

        except Exception as e:
            print("Exception for " + item['raw'] + " -> " + str(e))
        except SympifyError as e:
            print("Syntax error for " + item['raw'] + " -> " + str(e))

    print("correct: " + str(correct / total))
    print("wrong: " + str(wrong / total))
    print("total: " + str(total))


test1_MaterialParser_from_raw()

def test2():
    print(" Test 2: test the method extract_formula_from_string() from the Material Parser  ")
    correct = 0
    wrong = 0
    total = 0
    for item in data:
        # print(item['raw'])
        try:
            result = mp.extract_formula_from_string(str(item['raw']))

            if 'formula' in item['entities']:
                total += 1
                if result[0] == item['entities']['formula']:
                    correct += 1
                else:
                    wrong += 1

        except Exception:
            print("Exception for " + item['raw'])
        except SympifyError:
            print("Syntax error for " + item['raw'])
    print("correct: " + str(correct / total))
    print("wrong: " + str(wrong / total))
    print("total: " + str(total))

test2()

from delft.sequenceLabelling import Sequence
from delft.sequenceLabelling.models import BidLSTM_CRF
from material_parser.material_parser import MaterialParser
from sympy import SympifyError

from material2class import Material2Class
from materialParser_evaluation import readMaterialData

def test3():
    data = readMaterialData('evaluation/eval2.xml')

    mp = MaterialParser(pubchem_lookup=False, verbose=False)

    raw_data = [d['raw'] for d in data]

    ## Test 3: Application of material parser (crf) + ceder material parser

    model = Sequence("material", BidLSTM_CRF.name)
    model.load(dir_path="./models")
    tags = model.tag(raw_data, "json")

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
                print("Extract composition from formula: " + formula + " -> " + str(composition))

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

                # reconstructed_formula = mp.reconstruct_formula_from_string(formula)
                # print("reconstruct_formula_from_string: " + formula + " -> " + str(reconstructed_formula))

                # split_formula = mp.split_formula_into_compounds(formula)
                # print("split_formula_into_compounds: " + formula + " -> " + str(split_formula))
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
