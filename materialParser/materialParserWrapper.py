from material2class import Material2Class, Material2Tags
from material_parser.material_parser import MaterialParser
from sympy import SympifyError


class MaterialParserWrapper:
    def __init__(self):
        self.mp = MaterialParser(pubchem_lookup=False)
        self.material2class = Material2Class()
        self.material2tags = Material2Tags()

    def formula_to_class(self, formula):
        return self.material2class.get_class(formula)

    def formula_to_classes(self, formula):
        return self.material2tags.get_classes(formula)

    def decompose_formula(self, formula):
        structured_formula = {}
        try:
            structured_formula = self.mp.parse(formula)
        except SympifyError as e:
            print("Error when parsing formula: ", str(e))

        return structured_formula

    def name_to_formula(self, name):
        formula = {}
        try:
            formula = self.mp.string2formula(name)
        except SympifyError as e:
            print("Error when parsing formula: ", str(e))

        return formula

    def formula_to_composition(self, formula):
        composition = self.mp.formula2composition(formula)

        if not 'elements' in composition:
            return {}

        return composition
