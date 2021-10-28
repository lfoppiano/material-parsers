from material2class import Material2Class, Material2Tags
from sympy import SympifyError
from text2chem.parser_pipeline import ParserPipelineBuilder
from text2chem.postprocessing_tools.substitute_additives import SubstituteAdditives
from text2chem.preprocessing_tools.additives_processing import AdditivesProcessing
from text2chem.preprocessing_tools.chemical_name_processing import ChemicalNameProcessing
from text2chem.preprocessing_tools.mixture_processing import MixtureProcessing
from text2chem.preprocessing_tools.phase_processing import PhaseProcessing
from text2chem.regex_parser import RegExParser


class MaterialParserWrapper:
    def __init__(self, material_parser=None):
        if not material_parser:
            material_parser = ParserPipelineBuilder() \
            .add_preprocessing(AdditivesProcessing) \
            .add_preprocessing(ChemicalNameProcessing) \
            .add_preprocessing(PhaseProcessing) \
            .add_preprocessing(MixtureProcessing) \
            .add_postprocessing(SubstituteAdditives) \
            .set_regex_parser(RegExParser) \
            .build()
        
        self.material_parser = material_parser
        self.material2class = Material2Class()
        self.material2tags = Material2Tags()
        

    def formula_to_class(self, formula):
        return self.material2class.get_class(formula)

    def formula_to_classes(self, formula):
        return self.material2tags.get_classes(formula)

    def formula_to_composition(self, formula):
        structured_formula = {}
        try:
            output = self.material_parser.parse(formula)
        except SympifyError as e:
            raise ValueError(e)
        except ValueError as ve:
            output = self.material_parser.parse(formula.replace(" ", ""))

        if output.composition:
            composition_ = output.composition[0]
            structured_formula['composition'] = composition_.elements
                
        return structured_formula

    def name_to_formula(self, name):
        output_formula = {}
        try:
            output = self.material_parser.parse(name)
        except SympifyError as e:
            raise ValueError(e)
        except ValueError as ve:
            output = self.material_parser.parse(name.replace(" ", ""))

        if output.composition:
            composition_ = output.composition[0]
            output_formula['composition'] = composition_.elements

        output_formula['name'] = output.material_name
        output_formula['formula'] = output.material_formula

        return output_formula
