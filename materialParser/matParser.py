from bs4 import BeautifulSoup, Tag
from material_parser.material_parser import MaterialParser
from sympy import SympifyError

mp = MaterialParser(pubchem_lookup=False, verbose=False)
data = []

## Loading evaluation data
with open('evaluation/500papers.material.tei.xml', 'r') as fp:
    doc = fp.read()

    soup = BeautifulSoup(doc, 'xml')

    for i, pTag in enumerate(soup.materials):
        if type(pTag) == Tag:
            item = {
                'raw': str(pTag.get_text())
            }
            data.append(item)
            for child in pTag.children:
                if type(child) == Tag:
                    item[child.name] = child.get_text()
                    # print(child.get_text())
                    # print(child.name)

correct = 0
wrong = 0
total = 0

for item in data:
    print(item['raw'])
    try:
        result = mp.parse_material_string(str(item['raw']))

        if 'formula' in item:
            total +=1
            if 'material_formula' in result:
                if result['material_formula'] == item['formula']:
                    correct += 1
                else:
                    wrong += 1

            else:
                wrong += 1

    except Exception:
        print("Exception for " + item['raw'])
    except SympifyError:
        print("Syntax error for " + item['raw'])

print("correct: " + str(correct/total))
print("wrong: " + str(wrong/total))
print("total: " + str(total))





