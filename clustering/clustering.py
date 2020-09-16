# Script to extract superconductor and materials name from PDFs
import argparse
import csv
import json
import os
import re
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


def process_file(source_path, type="pdf"):
    output_classes = []
    output_classes_from_materials = []
    materials = []
    materials_from_abstract = []
    materials_from_body = []
    materials_from_keywords = []
    materials_from_title = []

    output = {
        'sourcepath': str(source_path),
        'filename': source_path.name,

        # classes
        'classes': output_classes,
        'classes_from_materials': output_classes_from_materials,
        'materials': materials,
        'materials_from_abstract': materials_from_abstract,
        'materials_from_body': materials_from_body,
        'materials_from_keywords': materials_from_keywords,
        'materials_from_title': materials_from_title

    }

    print("Processing file " + str(source_path))

    r = '{}'
    if type == 'pdf':
        r = grobid_client.process_pdf(str(source_path), "processPDF_noLinking")
        if r is None:
            raise Exception("Response is None for " + str(source_path) + ". Moving on. ")
        jsonOut = decode(r)
    else:
        with open(source_path, 'r') as f:
            jsonOut = json.load(f)

    if 'paragraphs' not in jsonOut:
        return

    for sentence in jsonOut['paragraphs']:

        if 'spans' not in sentence:
            continue

        class_spans = [item['text'] for item in sentence['spans'] if
                       'type' in item and (item['type'] == '<class>')]

        if len(class_spans) > 0:
            output_classes.extend(class_spans)

        material_class_spans = [item['attributes'][attribute] for item in sentence['spans'] if
                                'type' in item and (item['type'] == '<material>') for attribute in item['attributes'] if
                                attribute.endswith("clazz")]

        if len(material_class_spans) > 0:
            output_classes_from_materials.extend(material_class_spans)

        material_spans = [item['text'] for item in sentence['spans'] if
                          'type' in item and (item['type'] == '<material>')]

        if len(material_spans) > 0:
            materials.extend(material_spans)

        if 'subSection' in sentence and sentence['subSection'] == 'abstract':
            materials_from_abstract_spans = [item['text'] for item in sentence['spans'] if
                                             'type' in item and (item['type'] == '<material>')]

            if len(materials_from_abstract_spans) > 0:
                materials_from_abstract.extend(materials_from_abstract_spans)

        if 'subSection' in sentence and sentence['subSection'] == 'title':
            materials_from_title_spans = [item['text'] for item in sentence['spans'] if
                                          'type' in item and (item['type'] == '<material>')]

            if len(materials_from_title_spans) > 0:
                materials_from_title.extend(materials_from_title_spans)

        if 'subSection' in sentence and sentence['subSection'] == 'keywords':
            materials_from_keywords_spans = [item['text'] for item in sentence['spans'] if
                                             'type' in item and (item['type'] == '<material>')]

            if len(materials_from_keywords_spans) > 0:
                materials_from_keywords.extend(materials_from_keywords_spans)

        if 'section' in sentence and sentence['section'] == 'body':
            materials_from_body_spans = [item['text'] for item in sentence['spans'] if
                                             'type' in item and (item['type'] == '<material>')]

            if len(materials_from_body_spans) > 0:
                materials_from_body.extend(materials_from_body_spans)

    return output


def process_directory(source_directory, output_directory, type="pdf"):
    # xdir = Path('/data/workspace/Suzuki/supercon_files_20190808/iop/data/')
    # xmlfiles = [x for x in xdir.glob('**/*.xml')]
    # pdffiles = [x for x in xdir.glob('**/*.pdf')]
    # write_header(output_directory)
    output = []
    for root, dirs, files in os.walk(source_directory):
        for file_ in files:
            if not file_.lower().endswith("." + type):
                continue

            abs_path = os.path.join(root, file_)
            try:
                cluster_single_file = process_file(Path(abs_path), type)
            except Exception as e:
                print("Something went wrong. Skipping. " + str(e))
                continue

            cluster_single_file['classes'] = compact_classes(cluster_single_file['classes'])
            cluster_single_file['classes_from_materials'] = compact_classes(
                cluster_single_file['classes_from_materials'])
            cluster_single_file['materials'] = compact_classes(cluster_single_file['materials'])
            cluster_single_file['materials_from_title'] = compact_classes(cluster_single_file['materials_from_title'])
            cluster_single_file['materials_from_keywords'] = compact_classes(cluster_single_file['materials_from_keywords'])
            cluster_single_file['materials_from_abstract'] = compact_classes(cluster_single_file['materials_from_abstract'])
            cluster_single_file['materials_from_body'] = compact_classes(cluster_single_file['materials_from_body'])

            cluster_single_file['sourcepath'] = os.path.relpath(cluster_single_file['sourcepath'],
                                                                Path(output_directory).absolute()) \
                .replace(".json", ".pdf").replace("jsons/", "pdfs/")

            cluster_single_file['filename'] = cluster_single_file['filename'].replace(".json", "")

            output.append(cluster_single_file)
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
    cleanup_classes = [re.sub(r'superconductors?|systems?|materials?', "", str(clazz)).strip() for clazz in
                       classes_list]
    distincts = group_by_with_soft_matching(cleanup_classes, 0.9)
    return list(distincts.keys())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract clustering information from scientific articles")

    parser.add_argument("--input", help="Input file or directory")
    parser.add_argument("--output", required=False, default=None,
                        help="Output directory (if omitted, the output will be the same directory/file with different extension)")
    parser.add_argument("--type", default="pdf", choices=['pdf', 'json'],
                        help="Type of processing: pdf through grobid-superconductors) or json pre-extracted files")

    args = parser.parse_args()

    input = args.input
    output = args.output
    type = args.type

    # input directory
    if os.path.isdir(input):
        if output is None:
            print("When specified a source directory, is mandatory to specify an output directory too. ")
            exit(-1)
        input_path = Path(input)
        content = process_directory(input_path, output, type)

        with open(output + '/output.json', 'w') as f:
            json.dump(content, f)

    elif os.path.isfile(input):
        input_path = Path(input)
        content = process_file(input_path, type=type)

        content['classes'] = compact_classes(content['classes'])
        content['classes_from_materials'] = compact_classes(content['classes_from_materials'])

        # if output is None:
        print(json.dumps(content))
        # else:
        # write_on_files(content, output)

    else:
        parser.print_help()
