# from material_parser.material_parser import MaterialParser

from material2class import Material2Class, Material2Tags


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
        return  self.material2class.get_class(formula)

    def formula_to_classes(self, formula):
        return self.material2tags.get_classes(formula)

    # def name_to_formula(self, name):
    #     formula = self.mp.string2formula(name)
    #
    #     return formula
