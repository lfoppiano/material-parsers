from  material_parsers.commons.grobid_evaluation_analysis import append_tokens_before, append_tokens_after, \
    extract_error_cases


def test_append_tokens_before():
    error_case = []
    input_data = {
        'data': [
            ['a', '<other>', '<other>'],
            ['b', '<other>', '<other>'],
            ['c', '<other>', '<other>'],
            ['d', 'I-<l1>', 'I-<l1>'],
            ['e', '<l1>', '<l1>'],
            ['f', '<l1>', '<other>'],
            ['g', '<other>', '<other>']
        ]
    }
    nb_token_before = 5
    output = append_tokens_before(error_case, input_data, 5, nb_token_before)

    print(output)
    assert len(output) == nb_token_before
    assert output[0][0] == "a"
    assert output[1][0] == "b"
    assert output[2][0] == "c"
    assert output[3][0] == "d<=>"
    assert output[4][0] == "e<=>"


def test_append_toekns_before_2():
    error_case = []
    input_data = {
        'data': [
            ['a', 'I-<ba>', 'I-<ba>'],
            ['b', '<ba>', '<ba>'],
            ['c', '<other>', '<other>'],
            ['d', 'I-<l1>', 'I-<l1>'],
            ['e', '<l1>', '<l1>'],
            ['f', '<l1>', '<other>'],
            ['g', '<other>', '<other>']
        ]
    }
    nb_token_before = 5
    output = append_tokens_before(error_case, input_data, 5, nb_token_before)

    print(output)
    assert len(output) == nb_token_before
    assert output[0][0] == "a"
    assert output[1][0] == "b"
    assert output[2][0] == "c"
    assert output[3][0] == "d<=>"
    assert output[4][0] == "e<=>"


def test_append_tokens_after():
    error_case = []
    input_data = {
        'data': [
            ['a', '<other>', '<other>'],
            ['b', 'I-<l3>', 'I-<l3>'],
            ['c', '<l3>', 'I-<l2>'],
            ['d', '<other>', '<l2>'],
            ['e', '<other>', '<other>'],
            ['f', '<other>', '<other>'],
            ['g', '<other>', '<other>']
        ]
    }
    nb_token_after = 5
    output = append_tokens_after(error_case, input_data, 2, nb_token_after)

    print(output)
    assert len(output) == nb_token_after - 1
    assert output[0][0] == "d"
    assert output[1][0] == "e"
    assert output[2][0] == "f"
    assert output[3][0] == "g"


def test_append_toekns_after_2():
    error_case = []
    input_data = {
        'data': [
            ['a', '<other>', '<other>'],
            ['b', 'I-<l3>', 'I-<l3>'],
            ['c', '<l3>', 'I-<l2>'],
            ['d', '<other>', '<l2>'],
            ['e', '<other>', '<other>'],
            ['f', '<other>', '<other>'],
            ['g', '<other>', '<other>']
        ]
    }
    nb_token_after = 5
    output = append_tokens_after(error_case, input_data, 3, nb_token_after)

    print(output)
    assert len(output) == 3
    assert output[0][0] == "e"
    assert output[1][0] == "f"
    assert output[2][0] == "g"


def test_extract_error_cases_1():
    input_data = [
        {
            'name': 'fold 0',
            'data': [
                ['Hall', '<other>', '<other>'],
                ['coefficient', '<other>', '<other>'],
                ['and', '<other>', '<other>'],
                ['specific', 'I-<me_method>', 'I-<me_method>'],
                ['heat', '<me_method>', '<me_method>'],
                ['measurements', '<me_method>', '<other>'],
                [',', '<other>', '<other>'],
                ['and', '<other>', '<other>'],
                ['the', '<other>', '<other>'],
                ['remaining', '<other>', '<other>'],
                ['part', '<other>', '<other>'],
                ['was', '<other>', '<other>']
            ],
            'results': []
        }
    ]

    output = extract_error_cases(input_data, 3, 3)

    print(output)
    assert len(output) == 1
    assert len(output[
                   0]) == 2  # Each error case is composed by a list of two elements, the representative label and the sequence
    sequence = output[0][1]
    assert len(sequence) == 7  # sequence
    assert sequence[0][0] == "and"
    assert sequence[1][0] == "specific<=>"
    assert sequence[2][0] == "heat<=>"
    assert sequence[3][0] == "measurements<-r>"
    assert sequence[4][0] == ","
    assert sequence[5][0] == "and"
    assert sequence[6][0] == "the"


# def test_count_discrepancies_near_annotations():
#     cases = [
#         [
#             '<l3>',
#             [
#                 ['a', '<other>', '<other>'],
#                 ['b<=>', 'I-<l3>', 'I-<l3>'],
#                 ['c<+>', '<l3>', 'I-<l2>'],
#                 ['d<+>', '<other>', '<l2>'],
#                 ['e', '<other>', '<other>'],
#                 ['f', '<other>', '<other>'],
#                 ['g', '<other>', '<other>']
#             ]
#         ]
#     ]
# 
#     discrepancies = count_discrepancies(cases)
# 
#     print(discrepancies)
#     assert len(discrepancies.keys()) == 1
#     label_discrepancy = discrepancies['<l3>']
#     assert len(label_discrepancy['<+>']) == 1
#     assert label_discrepancy['<+>']['d'] == 1


# def test_count_discrepancies_near_annotations_real_case():
#     cases = [
#         [
#             '<valueAtomic>',
#             [
#                 ['on', '<other>', '<other>'],
#                 ['October<=>', 'I-<valueAtomic>', 'I-<valueAtomic>'],
#                 ['19<=>', '<valueAtomic>', '<valueAtomic>'],
#                 [',<=>', '<valueAtomic>', '<valueAtomic>'],
#                 ['2014<=>', '<valueAtomic>', '<valueAtomic>'],
#                 ['at<-r>', '<valueAtomic>', '<other>'],
#                 ['approximately<-r>', '<valueAtomic>', '<other>'],
#                 ['18<-p>', '<valueAtomic>', 'I-<valueAtomic>'],
#                 [':<=>', '<valueAtomic>', '<valueAtomic>'],
#                 ['29<=>', '<valueAtomic>', '<valueAtomic>'],
#                 ['UT<=>', '<valueAtomic>', '<valueAtomic>'],
#                 [',', '<other>', '<other>'],
#                 ['reaching', '<other>', '<other>']
#             ]
#         ]
#     ]
# 
#     discrepancies = count_discrepancies(cases)
# 
#     assert len(discrepancies.keys()) == 1       # labels
#     label_discrepancy = discrepancies['<valueAtomic>']
#     assert len(label_discrepancy['<-r>']) == 2
#     assert len(label_discrepancy['<-p>']) == 1
#     assert label_discrepancy['<-r>']['at'] == 1
#     assert label_discrepancy['<-r>']['approximately'] == 1
#     assert label_discrepancy['<-p>']['18'] == 1
