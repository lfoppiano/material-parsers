import re

from pymatgen.core import Composition
## This map define the rules for selecting the classes.
# and_compunds is satisfied if ALL of the contained compounds are present
# or_compounds is satisfied if ANY of the contained compound is present
from sympy import SympifyError


class ClassResolver:
    """
    This is the superclass of an object that is able to resolve the class from a raw material name, which has,
    potentially a relevant amount of garbage in it.
    """

    verbose = False

    def __init__(self, materialParser=None, verbose=False):
        self.mp = materialParser
        self.verbose = verbose

    def decompose_formula(self, formula):

        decomposed_formula = []

        try:
            dc = Composition(formula, strict=False).as_dict().keys()
        except Exception as ce:
            if self.verbose:
                print("Exception when parsing " + str(formula) + ". Error: " + str(ce))
            # Trying with some tricks
            material_formula_with_replacements = re.sub(r'[+-][ZXYzxy]', '', formula)
            try:
                if self.verbose:
                    print("Trying to parse " + str(material_formula_with_replacements))
                dc = Composition(material_formula_with_replacements, strict=False).as_dict().keys()
            except Exception as ce:
                if self.verbose:
                    print("Exception when parsing " + str(material_formula_with_replacements) + ". Error: " + str(ce))
                if self.mp is None:
                    return decomposed_formula

                try:
                    if self.verbose:
                        print("Trying to parse using the Material Parser" + str(material_formula_with_replacements))
                    compounds = self.mp.formula2composition(material_formula_with_replacements)
                    if compounds is not None and 'elements' in compounds:
                        dc = compounds['elements'].keys()
                    else:
                        return decomposed_formula

                except Exception as ee:
                    # We give up... skipping this record
                    if self.verbose:
                        print("Exception when parsing ", material_formula_with_replacements, ". Error: ", ee)
                    return decomposed_formula
                except SympifyError as eee:
                    # We give up... skipping this record
                    if self.verbose:
                        print("Exception when parsing ", material_formula_with_replacements, ". Error: ", eee)
                    return decomposed_formula

        # print(" Input Formula: " + str())
        decomposed_formula = list(dc)
        return decomposed_formula


class Material2Class(ClassResolver):
    composition_map = [
        {"and_compounds": ["O", "Cu"], "name": "Cuprate"},
        {"and_compounds": ["Fe", "P"], "name": "Iron-pnictide"},
        {"and_compounds": ["Fe", "As"], "name": "Iron-pnictide"},
        {"and_compounds": ["Fe", 'S'], "name": "Iron-chalcogenides"},
        {"and_compounds": ["Fe", 'Se'], "name": "Iron-chalcogenides"},
        {"and_compounds": ["Fe", 'Te'], "name": "Iron-chalcogenides"},
        {"and_compounds": ["H"], "name": "Hydrides"},
        {"and_compounds": ["C"], "name": "Carbides"},
        {"and_compounds": ["N"], "name": "Nitrides"},
        {"and_compounds": ["F"], "name": "Fluorides"},
        # comment here   Ch is not an atomic symbol but "Ch" and others like "copper" would be usuful later for sub-classes
        {"or_compounds": ["S", "Se", "Te"], "name": "Chalcogenides"},
        {"or_compounds": ["P", "As"], "name": "Pnictides"},
        {"and_compounds": ["B"], "name": "Borides"},
        {"and_compounds": ["O"], "name": "Other oxides"},
        # alloys---> that does not satisfy none of above
    ]

    verbose = False

    def get_class(self, formula):
        output = ''

        input_formula = self.decompose_formula(formula)

        # print(" Input Formula: " + str(input_formula))

        for composition in self.composition_map:
            and_compounds = []
            if 'and_compounds' in composition:
                and_compounds = composition['and_compounds']

            or_compounds = []
            if 'or_compounds' in composition:
                or_compounds = composition['or_compounds']

            output_class = composition['name']

            if len(and_compounds) > 0:
                if all(elem in input_formula for elem in and_compounds):
                    output = output_class
                    break
            elif len(or_compounds) > 0:
                if any(elem in input_formula for elem in or_compounds):
                    output = output_class
                    break

        if output == '':
            output = "Alloy"

        return output


class Material2Tags(ClassResolver):
    material2class_first_level = [
        {"and_compounds": ["O", "Cu"], "name": "Cuprates"},
        {"and_compounds": ["Fe", "P"], "name": "Iron-pnictides"},
        {"and_compounds": ["Fe", "As"], "name": "Iron-pnictides"},
        {"and_compounds": ["Fe", 'S'], "name": "Iron-chalcogenides"},
        {"and_compounds": ["Fe", 'Se'], "name": "Iron-chalcogenides"},
        {"and_compounds": ["Fe", 'Te'], "name": "Iron-chalcogenides"},
        {"and_compounds": ["H"], "name": "Hydrides"},
        {"and_compounds": ["C"], "name": "Carbides"},
        {"and_compounds": ["N"], "name": "Nitrides"},
        {"and_compounds": ["F"], "name": "Fluorides"},
        # comment here   Ch is not an atomic symbol but "Ch" and others like "copper" would be usuful later for sub-classes
        {"or_compounds": ["S", "Se", "Te"], "name": "Chalcogenides"},
        {"or_compounds": ["P", "As"], "name": "Pnictides"},
        {"and_compounds": ["B"], "name": "Borides"},
        {"and_compounds": ["O"], "name": "Oxides"},
        # alloys---> that does not satisfy none of above
        {"not_compounds": ["O", " B", "C", "N", "F", "P", "S", "As", "Se", "Te"], "name": "Alloys"}
    ]

    material2class_second_level = {
        'Cuprates': [
            {"and_compounds": ["Bi"], "name": "Bi-based"},
            {"and_compounds": ["Hg"], "name": "Hg-based"},
            {"and_compounds": ["Tl"], "name": "Tl-based"},
            {"and_compounds": ["La"], "name": "La-based"},
            {"and_compounds": ["Nd", "Cu", "O"], "name": "T'"},
            {"and_compounds": ["Nd,", "Ce", "Cu", "O"], "name": "T'"},
            {"and_compounds": ["Pr", "Ce", "Cu", "O"], "name": "T'"},
            {"and_compounds": ["Pr", "Ce", "La", "Cu", "O"], "name": "T'"},
        ],
        'Iron-pnictides': [],
        'Iron-chalcogenides': [],
        'Hydrides': [
            {"and_compounds": ["H", "S"], "name": "Sulfure Hydrate"}
        ],
        'Carbides': [
            {"and_compounds": ["B", "C"], "name": "Borocarbides"},
            {"and_compounds": ["O", "C"], "name": "Organics"}
        ],
        'Chalcogenides': [
            {"and_compounds": ["Bi", {"S": 2}], "name": "BiCh2"},
            {"and_compounds": ["Bi", {"Se": 2}], "name": "BiCh2"},
            {"and_compounds": ["Bi", {"Te": 2}], "name": "BiCh2"},
        ],
        'Oxides': [
            {"or_compounds": ["Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Y", "Zr", "Nb", "Mo",
                              "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "La", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt",
                              "Au", "Hg"], "name": "Transition Metal-Oxides"}
            # {"and_compounds": ["O", "C"], "name": "Pyrochlore Oxides"},
            # {"and_compounds": ["O", "C"], "name": "Pyrochlore Oxides"}
        ],
        'Alloys': [
            {"or_compounds": ["Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "U"],
             "name": "Possible Heavy-fermions"}
        ]

    }

    def assign_tags(self, formula, composition_map):
        output_tags = []

        input_formula = self.decompose_formula(formula)

        if type(composition_map) == list:
            for composition in composition_map:
                and_compounds = []
                if 'and_compounds' in composition:
                    and_compounds = composition['and_compounds']

                or_compounds = []
                if 'or_compounds' in composition:
                    or_compounds = composition['or_compounds']

                not_compounds = []
                if 'not_compounds' in composition:
                    not_compounds = composition['not_compounds']

                output_class = composition['name']

                if len(and_compounds) > 0:
                    if all(elem in input_formula for elem in and_compounds if type(elem) == str):
                        output_tags.append(output_class)
                        continue
                elif len(or_compounds) > 0:
                    if any(elem in input_formula for elem in or_compounds if type(elem) == str):
                        output_tags.append(output_class)
                        continue
                elif len(not_compounds) > 0:
                    if not any(elem in input_formula for elem in not_compounds if type(elem) == str):
                        output_tags.append(output_class)
                        continue

        elif type(composition_map) == map:
            for first_element, composition in composition_map.items():
                and_compounds = []
                if 'and_compounds' in composition:
                    and_compounds = composition['and_compounds']

                or_compounds = []
                if 'or_compounds' in composition:
                    or_compounds = composition['or_compounds']

                not_compounds = []
                if 'not_compounds' in composition:
                    not_compounds = composition['not_compounds']

                output_class = composition_map[first_element]['name']

                if len(and_compounds) > 0:
                    if all(elem in input_formula for elem in and_compounds if type(elem) == str):
                        output_tags.append(output_class)
                        continue
                elif len(or_compounds) > 0:
                    if any(elem in input_formula for elem in or_compounds if type(elem) == str):
                        output_tags.append(output_class)
                        continue
                elif len(not_compounds) > 0:
                    if not any(elem in input_formula for elem in not_compounds if type(elem) == str):
                        output_tags.append(output_class)
                        continue
        return set(output_tags)

    def get_classes(self, formula):
        tags = self.assign_tags(formula, composition_map=self.material2class_first_level)

        output = {tag: [] for tag in tags}

        for tag in tags:
            if tag in self.material2class_second_level:
                output[tag] = list(self.assign_tags(formula, composition_map=self.material2class_second_level[tag]))
            else:
                output[tag] = []

        return output
