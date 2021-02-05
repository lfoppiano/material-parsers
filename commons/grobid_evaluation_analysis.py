## Analysis ML results
import argparse
import os
import sys
from pathlib import Path


def extract_log(log_file):
    first = True
    raw = False
    results = False

    folds = []
    fold = {
        "name": "",
        "data": [],
        "results": ""
    }

    accumulator = []
    results_accumulator = []

    with open(log_file, 'r') as file:
        for line in file:
            if line.startswith("======================"):
                fold_text = line.split("====================== ")[1]
                if first:
                    fold['name'] = fold_text
                    first = False
                else:
                    # store
                    fold['results'] = results_accumulator
                    folds.append(fold)
                    fold = {
                        "name": fold_text,
                        "data": [],
                        "results": ""
                    }
                    raw = False
                    results = False

            elif line.startswith("=== START RAW RESULTS ==="):
                raw = True
            elif line.startswith("=== END RAw RESULTS ==="):
                fold['data'] = accumulator
                accumulator = []
                raw = False
            elif line.startswith("===== Field-level results ====="):
                results = True
            else:
                if results == True:
                    results_accumulator.append(line)
                elif raw == True:
                    splits = line.split('\t')
                    splits[len(splits) - 1].replace("\n", "")
                    accumulator.append(splits)

    fold['results'] = results_accumulator
    folds.append(fold)
    return folds


def extract_error_cases(input_data, tokens_before=5, tokens_after=5):
    error_cases = []
    for idx, fold in enumerate(input_data):
        error_case = []
        in_error = False

        for i, raw_line in enumerate(fold['data']):
            # If the line is not empty
            if len(raw_line) > 1:
                # if the entities are wrongly recognised (and not <other>)
                expected_class_index = len(raw_line) - 2
                predicted_class_index = len(raw_line) - 1
                if raw_line[expected_class_index] != '<other>' and raw_line[expected_class_index] != raw_line[
                    predicted_class_index].replace('\n', ''):
                    if in_error == True:
                        # check if the previous item is part of the same label
                        if i > 0 and fold['data'][i - 1][expected_class_index].replace("I-", "") == raw_line[
                            expected_class_index]:
                            if raw_line[expected_class_index].startswith("I-"):
                                error_case = append_tokens_after(error_case, fold, i, tokens_after)
                                error_cases.append(error_case)
                                error_case = []
                                error_case = append_tokens_before(error_case, fold, i, tokens_before)
                            error_case.append([raw_line[0], raw_line[expected_class_index],
                                               raw_line[predicted_class_index].replace('\n', '')])
                        else:
                            error_case = append_tokens_after(error_case, fold, i, tokens_after)
                            error_cases.append(error_case)
                            error_case = []
                            error_case = append_tokens_before(error_case, fold, i, tokens_before)
                            error_case.append([raw_line[0], raw_line[expected_class_index],
                                               raw_line[predicted_class_index].replace('\n', '')])
                    else:
                        if len(error_case) > 0:
                            error_case = append_tokens_after(error_case, fold, i, tokens_after)
                            error_cases.append(error_case)
                            error_case = []

                        error_case = append_tokens_before(error_case, fold, i, tokens_before)

                        error_case.append([raw_line[0], raw_line[expected_class_index],
                                           raw_line[predicted_class_index].replace('\n', '')])
                        in_error = True
                else:
                    if in_error == True:
                        in_error = False
                        if len(error_case) > 0:
                            error_case = append_tokens_after(error_case, fold, i, tokens_after)
                            error_cases.append(error_case)
                            error_case = []


            elif in_error == True:
                in_error = False
                error_cases.append(error_case)

        if len(error_case) > 0:
            error_case.append(['|', '', ''])
            error_cases.append(error_case)

    return error_cases


def append_tokens_before(error_case, fold, i, tokens_before):
    if i > tokens_before - 1 and len(fold['data'][i - 1]) > 1:
        for x in range(i - tokens_before, i):
            item = fold['data'][x]
            if len(item) <= 1:
                error_case = []
                continue
            error_case.append([item[0], item[len(item) - 2], item[len(item) - 1].replace('\n', '')])
    error_case.append(['|', '', ''])
    return error_case


def append_tokens_after(error_case, fold, i, tokens_after):
    error_case.append(['|', '', ''])
    if len(fold['data']) > i + tokens_after:
        for x in range(i, i + tokens_after):
            item = fold['data'][x]
            if len(item) <= 1:
                break
            error_case.append([item[0], item[len(item) - 2], item[len(item) - 1].replace('\n', '')])

    return error_case


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Analysis n-fold cross-validation / holdout evaluation  results")

    parser.add_argument("--input", help="Input output file produced by grobid", required=True, type=Path)
    # parser.add_argument("--output", help="Output directory", required=True)
    # parser.add_argument("--recursive", action="store_true", default=False,
    #                     help="Process input directory recursively. If input is a file, this parameter is ignored.")
    # parser.add_argument("--format", default='csv', choices=['tsv', 'csv'],
    #                     help="Output format.")
    # parser.add_argument("--filter", default='all', choices=['all', 'oa', 'non-oa'],
    #                     help='Extract data from a certain type of licenced documents')

    args = parser.parse_args()
    input = args.input

    if not os.path.isfile(input):
        help()
        sys.exit(-1)

    data = extract_log(input)

    error_cases = extract_error_cases(data)

    grouped_cases = {}

    for case in error_cases:
        text = ""
        annotation = []
        in_annotation = False
        for x in case:
            if x[0] == "|":
                if in_annotation:
                    in_annotation = False
                else:
                    in_annotation = True
                continue

            if in_annotation == True:
                annotation.append(x)

        expected_label = annotation[0][1].replace("I-", "")
        for t in case:
            text += t[0] + " "

        if expected_label not in grouped_cases.keys():
            grouped_cases[expected_label] = []
        grouped_cases[expected_label].append(text)

    for i, key in enumerate(grouped_cases.keys()):
        print('\n\n===', key, '\n')
        for case in grouped_cases[key]:
            print(case)

        print('==========')
