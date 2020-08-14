from material_parser.material_parser import MaterialParser

from material2class import Material2Class


class MaterialParserWrapper:

    mp = MaterialParser()
    material2class = Material2Class()

    def formula_to_composition(self, formula):
        composition = self.mp.formula2composition(formula)

        if 'elements' in composition:
            return composition

        else:
            return {}

    def formula_to_class(self, formula):
        clazz = self.material2class.get_class(formula)

        return clazz

    def name_to_formula(self, name):
        formula = self.mp.string2formula(name)

        return formula
