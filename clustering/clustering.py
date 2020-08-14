# Script to extract superconductor and materials name from PDFs
import csv
import json
import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from grobid_client_generic import grobid_client_generic

grobid_client = grobid_client_generic(config_path='./config.json')


def decode(response_string):
    try:
        return json.loads(response_string)
    except ValueError as e:
        return "Value error: " + str(e)
    except TypeError as te:
        return "Type error: " + str(te)


def process_file(source_path):
    output_classes = []

    output = {
        'sourcepath': str(source_path),
        'filename': source_path.name,

        # classes
        'classes': output_classes,
    }

    print("Processing file " + str(source_path))

    r = grobid_client.process_pdf(str(source_path), "processPDF_noLinking")
    if r is None:
        raise Exception("Response is None for " + str(source_path) + ". Moving on. ")
    jsonOut = decode(r)

    if 'paragraphs' not in jsonOut:
        return

    for sentence in jsonOut['paragraphs']:

        if 'spans' not in sentence:
            continue

        class_span = [item['text'] for item in sentence['spans'] if
                      'type' in item and (item['type'] == '<class>')]
        if len(class_span) > 0:
            output_classes.extend(class_span)

    return output


def process_directory(source_directory, output_directory):
    # xdir = Path('/data/workspace/Suzuki/supercon_files_20190808/iop/data/')
    # xmlfiles = [x for x in xdir.glob('**/*.xml')]
    # pdffiles = [x for x in xdir.glob('**/*.pdf')]
    # write_header(output_directory)
    output = []
    for root, dirs, files in os.walk(source_directory):
        for file_ in files:
            if not file_.lower().endswith(".pdf"):
                continue

            abs_path = os.path.join(root, file_)
            try:
                cluster_single_file = process_file(Path(abs_path))
            except Exception as e:
                print("Something went wrong. Skipping. " + str(e))
                continue


            cluster_single_file['classes'] = compact_classes(cluster_single_file['classes'])
            cluster_single_file['sourcepath'] = os.path.relpath(cluster_single_file['sourcepath'], Path(output_directory).absolute())
            output.append(cluster_single_file)
            # write_on_files(cluster_single_file, output_directory, append=True)
    return output


def write_header(output_directory):
    with open(output_directory + '/output.tsv', 'w') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(['filename', 'classes'])


def write_on_files(output, output_directory, append=False):
    write_mode = 'a' if append else 'w'
    with open(output_directory + '/output.tsv', write_mode) as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow([output['filename'], output['classes_dist']])


def group_by_with_soft_matching(input_list, threshold):
    matching = {}
    last_matching = -1

    input_list_sorted = sorted(list(set(input_list)), reverse=True)

    for index_x, x in enumerate(input_list_sorted):
        unpacked = [y for x in matching for y in matching[x]]
        if x not in matching and x not in unpacked:
            matching[x] = []

            for index_y, y in enumerate(input_list_sorted[index_x + 1:]):
                if x == y:
                    continue

                if SequenceMatcher(None, x.lower(), y.lower()).ratio() > threshold:
                    matching[x].append(y)

        else:
            continue

    return matching


def compact_classes(classes_list):
    cleanup_classes = [re.sub(r'superconductors?|systems?|materials?', "", clazz).strip() for clazz in classes_list]
    distincts = group_by_with_soft_matching(cleanup_classes, 0.9)
    return list(distincts.keys())


if __name__ == '__main__':
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Invalid parameters. Usage: python clustering.py source output_directory. "
              "The source can be either a directory or a file. ")
        sys.exit(-1)

    # input directory
    input = sys.argv[1]
    output = None
    if len(sys.argv) == 3:
        output = sys.argv[2]

    if os.path.isdir(input):
        if output is None:
            print("When specified a source directory, is mandatory to specify an output directory too. ")
            exit(-1)
        input_path = Path(input)
        content = process_directory(input_path, output)

        with open(output + '/output.json', 'w') as f:
            json.dump(content, f)

    elif os.path.isfile(input):
        input_path = Path(input)
        content = process_file(input_path)

        content['classes'] = compact_classes(content['classes'])

        # if output is None:
        print(json.dumps(content))
        # else:
        # write_on_files(content, output)
