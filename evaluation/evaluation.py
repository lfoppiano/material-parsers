## This script takes in input the output file from the extractor and a list of correct cases and return the aggregated results
import csv
import sys
from difflib import SequenceMatcher
from sys import argv


def load_reference(reference):
    reference_map = {}
    with open(reference, 'r') as reference_file:
        csv_reader = csv.reader(reference_file, delimiter=',', quotechar='"')
        next(csv_reader)
        for row in csv_reader:
            material = row[0]
            tc = row[1]
            path = row[3]
            if path not in reference_map.keys():
                reference_map[path] = {material: tc}
            else:
                reference_map[path][material] = tc

    return reference_map


def process(output, reference):
    reference_map = load_reference(reference)

    output_list = []

    with open(output, 'r') as output_file:
        csv_reader = csv.reader(output_file, delimiter=',', quotechar='"')
        next(csv_reader)
        for row in csv_reader:
            material = row[0]
            tc = row[1]
            path = row[3]
            next_rows = [row[2]]
            skip = False
            if path in reference_map:
                path_results = reference_map[path]

                for result_material, result_tc in path_results.items():
                    ## Strict matching
                    if material == result_material:
                        if tc == result_tc:
                            output_list.append([material, tc, "Strict Matching", "OK", "", path] + next_rows)
                            skip = True
                            break

                if skip:
                    continue

                for result_material, result_tc in path_results.items():
                    ## Soft matching
                    if SequenceMatcher(None, result_material, material).ratio() > 0.95:
                        if tc == result_tc:
                            output_list.append([material, tc, "Soft Matching", "OK", "", path] + next_rows)
                            skip = True
                            break

                if not skip:
                    output_list.append([material, tc, "", "", "", path] + next_rows)

            else:
                output_list.append([material, tc, "", "", "", path] + next_rows)

    return output_list


if __name__ == "__main__":
    if len(argv) != 3:
        print("Invalid parameters. Usage: python evaluation.py output.csv reference.csv")
        sys.exit(-1)

    output = argv[1]
    reference = argv[2]

    output = process(output, reference)

    with open("output.csv", 'w') as csv_output:
        csv_writer = csv.writer(csv_output, quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(["Material", "Tc", "Matching", "Correct", "Comment", "Path", "Sentence"])
        csv_writer.writerows(output)

    # print(output)
