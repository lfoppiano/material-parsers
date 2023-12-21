from grobid_superconductors.material_parser.material_parser_formulas import MaterialParserFormulas
from grobid_superconductors.material_parser.material_parser_ml import MaterialParserML, replace_variable, \
    expand_formula, resolve_variables, generate_permutations

model = MaterialParserML(MaterialParserFormulas(), model_path=None)
# def test():
#     result = model.process(
#         ["j9f9j209 underdoped LaFeB07", "La Fe B 8-x with x = 0.1", "underdoped single crystal LaFeB09 (TLL222)"])
#     print(result)


def test_extract_results():
    output = {
        'software': 'DeLFT',
        'date': '2023-12-19T19:15:48.334995',
        'model': 'material-BidLSTM_CRF',
        'texts': [
            {
                'text': 'powderss underdoped LaFeB07',
                'entities': [
                    {'text': 'powderss', 'class': '<shape>', 'score': 1.0, 'beginOffset': 0, 'endOffset': 7},
                    {'text': 'underdoped', 'class': '<doping>', 'score': 1.0, 'beginOffset': 9, 'endOffset': 18},
                    {'text': 'LaFeB07', 'class': '<formula>', 'score': 1.0, 'beginOffset': 20, 'endOffset': 26}
                ]
            },
            {
                'text': 'La Fe B 8-x with x = 0.1, 0.2',
                'entities': [
                    {'text': 'La Fe B 8-x', 'class': '<formula>', 'score': 1.0, 'beginOffset': 0, 'endOffset': 10},
                    {'text': 'x', 'class': '<variable>', 'score': 1.0, 'beginOffset': 17, 'endOffset': 17},
                    {'text': '0.1', 'class': '<value>', 'score': 1.0, 'beginOffset': 21, 'endOffset': 23},
                    {'text': '0.2', 'class': '<value>', 'score': 1.0, 'beginOffset': 21, 'endOffset': 23}
                ]
            },
            {
                'text': 'underdoped single crystal LaFeB09 (TLL222)',
                'entities': [
                    {'text': 'underdoped', 'class': '<doping>', 'score': 1.0, 'beginOffset': 0, 'endOffset': 9},
                    {'text': 'single crystal', 'class': '<shape>', 'score': 1.0, 'beginOffset': 11,
                     'endOffset': 24},
                    {'text': 'LaFeB09', 'class': '<formula>', 'score': 1.0, 'beginOffset': 26, 'endOffset': 32},
                    {'text': 'TLL222', 'class': '<name>', 'score': 1.0, 'beginOffset': 35, 'endOffset': 40}
                ]
            }
        ],
        'runtime': 3.248
    }

    entities = model.extract_results(output)

    assert len(entities) == 3

    assert entities[0]['shape'] == "powderss"
    assert entities[0]['doping'] == "underdoped"
    assert entities[0]['formula']['raw_value'] == "LaFeB07"

    assert entities[1]['formula']['raw_value'] == "La Fe B 8-x"
    assert entities[1]['variables'] == {'x': ['0.1', '0.2']}
    assert len(entities[1]['resolved_formulas']) == 2
    assert entities[1]['resolved_formulas'][0]['raw_value'] == 'La Fe B 7.9'
    assert entities[1]['resolved_formulas'][1]['raw_value'] == 'La Fe B 7.8'

    assert entities[2]['doping'] == "underdoped"
    assert entities[2]['shape'] == 'single crystal'
    assert entities[2]['formula']['raw_value'] == 'LaFeB09'
    assert entities[2]['name'] == 'TLL222'


def test_replace_variable():
    output = replace_variable("Fe1-xCuxO2", "x", "0.8")
    assert output == "Fe0.2Cu0.8O2"


def test_replace_variable2():
    output = replace_variable("Fe-xCu1-xO2", "x", "0.8")
    assert output == "Fe-0.8Cu0.2O2"


def test_replace_variable3():
    output = replace_variable("FexCuxO2", "x", "0.8")
    assert output == "Fe0.8Cu0.8O2"


def test_replace_variable4():
    output = replace_variable("LnFeAs(O1−x Fx)", "Ln", "Pr")
    assert output == "PrFeAs(O1−x Fx)"


def test_replace_variable5():
    output = replace_variable("1-x Ru x", "x", "0.2")
    assert output == "0.8 Ru 0.2"


def test_replace_variable_error_case_1():
    output = replace_variable("RE", "RE", "Sc")
    assert output == "Sc"


def test_expand_formula_should_not_expand_nor_throw_exception():
    output_formulas = expand_formula("(TMTTF) 2 PF 6")
    assert len(output_formulas) == 1
    assert output_formulas[0] == "(TMTTF) 2 PF 6"


def test_expand_formula():
    output_formulas = expand_formula("(Sr, Na)Fe 2 As 2")
    assert len(output_formulas) == 1
    assert output_formulas[0] == "Sr 1-x Na x Fe 2 As 2"


def test_expand_formula_3():
    formula = "(Sr,K)Fe2As2"
    expand_formulas = expand_formula(formula)
    assert len(expand_formulas) == 1
    assert expand_formulas[0] == "Sr 1-x K x Fe2As2"


def test_expand_formula_4():
    formula = "(Sr , K ) Fe2As2"
    expand_formulas = expand_formula(formula)
    assert len(expand_formulas) == 1
    assert expand_formulas[0] == "Sr 1-x K x Fe2As2"


def test_expand_name():
    formula = "(Sr,K)-2222"
    expand_formulas = expand_formula(formula)
    assert len(expand_formulas) == 2
    assert expand_formulas[0] == "Sr-2222"
    assert expand_formulas[1] == "K-2222"


def test_expand_formula_2_variables():
    input_formula = "(Sr, La) Fe 2 O 7"
    expanded_formulas = expand_formula(input_formula)
    assert len(expanded_formulas) == 1
    assert expanded_formulas[0] == "Sr 1-x La x Fe 2 O 7"


def test_expand_formula_4_variables():
    input_formula = "(Sr, La, Cu, K) Fe 2 O 7"
    expanded_formulas = expand_formula(input_formula)
    assert len(expanded_formulas) == 1
    assert expanded_formulas[0] == "Sr 1-x-y-z La x Cu y K z Fe 2 O 7"


# def test_expand_formula_with_too_many_variables_should_throw_exception():
#     input_formula = "(Sr, Fe, La,Sr, Fe, La,Sr, Fe, La,Sr, Fe, La,Sr, Fe, La,Sr, Fe, La,Sr, Fe, La,Sr, Fe, La,Sr, Fe, Sr, Fe, La,Sr, Fe, Sr, Fe, La,Sr, Fe, Sr, Fe, La,Sr, Fe) Cu 2 O 13"
#     with pytest.raises(RuntimeError):
#         expand_formula(input_formula)


# Test resolveVariables method
def test_resolve_variable_1():
    material = {'formula': {'raw_value': "Fe1-xCuxO2"}, 'variables': {"x": ["0.1", "0.2", "0.3"]}}
    output_materials = resolve_variables(material)
    assert len(output_materials) == 3
    assert output_materials[0] == "Fe0.9Cu0.1O2"
    assert output_materials[1] == "Fe0.8Cu0.2O2"
    assert output_materials[2] == "Fe0.7Cu0.3O2"


def test_resolve_variable_2():
    material = {'formula': {'raw_value': "Fe1-xCuyO2"},
                'variables': {"x": ["0.1", "0.2", "0.3"], "y": ["-1", "-0.2", "0.3", "0.5"]}}
    output_materials = resolve_variables(material)
    assert len(output_materials) == 12
    assert "Fe0.9Cu-1O2" in output_materials
    assert "Fe0.9Cu-0.2O2" in output_materials
    assert "Fe0.9Cu0.3O2" in output_materials
    assert "Fe0.9Cu0.5O2" in output_materials
    assert "Fe0.8Cu-1O2" in output_materials
    assert "Fe0.8Cu-0.2O2" in output_materials
    assert "Fe0.8Cu0.3O2" in output_materials
    assert "Fe0.8Cu0.5O2" in output_materials
    assert "Fe0.7Cu-1O2" in output_materials
    assert "Fe0.7Cu-0.2O2" in output_materials
    assert "Fe0.7Cu0.3O2" in output_materials
    assert "Fe0.7Cu0.5O2" in output_materials


def test_resolve_variable_3():
    material = {'formula': {'raw_value': "Li x (NH 3 ) y Fe 2 (Te z Se 1−z ) 2"},
                'variables': {"x": ["0.1"], "y": ["0.1"], "z": ["0.1"]}}
    output_materials = resolve_variables(material)
    assert len(output_materials) == 1
    assert output_materials[0] == "Li 0.1 (NH 3 ) 0.1 Fe 2 (Te 0.1 Se 0.9 ) 2"


def test_resolve_variable_interval():
    material = {'formula': {'raw_value': "Li x (NH 3 ) 1-x Fe 2 (Te x Se 1−x ) 2"},
                'variables': {"x": ["< 0.1", "> 0.01"]}}
    output_materials = resolve_variables(material)
    assert len(output_materials) == 2
    assert output_materials[0] == "Li 0.1 (NH 3 ) 0.9 Fe 2 (Te 0.1 Se 0.9 ) 2"
    assert output_materials[1] == "Li 0.01 (NH 3 ) 0.99 Fe 2 (Te 0.01 Se 0.99 ) 2"


def test_generate_permutations():
    formula = "Li x (NH 3 ) y Fe 2 (Te z Se 1−z ) 2"

    variables = {
        "x": ["0.1"],
        "y": ["0.1"],
        "z": ["0.1"]
    }

    result = []
    generate_permutations(variables, list(variables.keys()), result, (0, 0), formula)

    assert len(result) == 1
    assert result[0] == "Li 0.1 (NH 3 ) 0.1 Fe 2 (Te 0.1 Se 0.9 ) 2"


def test_generate_permutations_2():
    formula = "Li x (NH 3 ) y Fe 2 (Te z Se 1−z ) 2"

    variables = {
        "x": ["0.1", "0.2"],
        "y": ["0.1", "0.2"],
        "z": ["0.1"]
    }

    result = []
    generate_permutations(variables, list(variables.keys()), result, (0, 0), formula)

    assert len(result) == 4
    assert result[0] == "Li 0.1 (NH 3 ) 0.1 Fe 2 (Te 0.1 Se 0.9 ) 2"
    assert result[1] == "Li 0.1 (NH 3 ) 0.2 Fe 2 (Te 0.1 Se 0.9 ) 2"
    assert result[2] == "Li 0.2 (NH 3 ) 0.1 Fe 2 (Te 0.1 Se 0.9 ) 2"
    assert result[3] == "Li 0.2 (NH 3 ) 0.2 Fe 2 (Te 0.1 Se 0.9 ) 2"
