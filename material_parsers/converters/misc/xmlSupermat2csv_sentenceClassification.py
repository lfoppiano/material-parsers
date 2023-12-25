import argparse
import copy
import csv
import difflib
import hashlib
import os
from collections import OrderedDict
from pathlib import Path

from material_parsers.commons.grobid_tokenizer import tokenizeAndFilterSimple
from material_parsers.converters.misc.xml2LossyJSON import process_file


def write_on_file(fw, row):
    fw.writerow(row)


def tokenise(string):
    return tokenizeAndFilterSimple(string)


def correct_segmentation_block(sentence_spans, ref_spans):
    new_sentence_spans = []
    ref_index = 0
    for j, sentence_span in enumerate(sentence_spans):

        for i in range(ref_index, len(ref_spans)):
            ref_span = ref_spans[i]

            if ref_span["end"] < sentence_span['end']:
                continue
            if ref_span['start'] > sentence_span["end"]:
                break

            while ref_span['start'] < sentence_span['end'] < ref_span['end']:
                if j + 1 < len(sentence_spans):
                    sentence_span['end'] = sentence_spans[j + 1]['end']
                    j += 1
                    ref_index = i
                else:
                    break

        if len(new_sentence_spans) == 0 or new_sentence_spans[len(new_sentence_spans) - 1]['end'] < sentence_span[
            'end']:
            new_sentence_spans.append(sentence_span)
    return new_sentence_spans


def get_sentence_spans(text, sentences, debug=False):
    sentence_spans = []
    previous_start = -1
    previous_end = -1
    for sentence in sentences:
        sentence_clean = sentence.strip()
        sentence_clean = sentence_clean.strip('\n')
        if previous_end > -1:
            start = text.find(sentence_clean, previous_end)
        else:
            start = text.find(sentence_clean)
        if start == -1:
            if previous_end > -1:
                start = text.replace("\n", " ").find(sentence_clean, previous_end)
            else:
                start = text.replace("\n", " ").find(sentence_clean)

            if start == -1:
                text_adapted = text
                if previous_end > -1:
                    text_adapted = text[previous_end:]
                    output_str, start = find_in_text(sentence_clean, text_adapted)
                    start += previous_end
                elif previous_start > -1:
                    text_adapted = text[previous_start:]

                    output_str, start = find_in_text(sentence_clean, text_adapted)
                    start += previous_start

                else:
                    output_str, start = find_in_text(sentence_clean, text_adapted)

                end = start + len(output_str)
                if start == -1:
                    print(
                        "\n- The starting offset is -1. We have tried to recover it, but probably something is still wrong. Please check. ")
                    print(output_str, " / ", text_adapted)
            else:
                end = start + len(sentence_clean)
        else:
            end = start + len(sentence_clean)

        previous_start = start

        # register the previous end only when the start is valid
        if start > -1:
            previous_end = end

        if debug:
            sentence_spans.append({'text': sentence_clean, 'start': start, 'end': end})
        else:
            sentence_spans.append({'start': start, 'end': end})

    return sentence_spans


def find_in_text(sub_string, text):
    ## Find the beginning of the contained sentence
    output = []
    inside = False
    differences = list(difflib.ndiff(text, sub_string))
    # remove addition from the sub_string
    differences_2 = [d for d in differences if d[0] != '+']
    for idx, item in enumerate(differences_2):
        if (item[0] == '-') and inside is False:
            continue
        else:
            inside = True
            output.append(text[idx])

    adapted_sub_string = "".join(output)
    # print(output_str)
    # print(len(output_str))
    ## find the end of the contained sentence
    for idx in range(len(output) - 1, 0, -1):
        item = differences_2[idx]
        if item[0] == '-' or item[0] == '+':
            output.pop(idx)
        else:
            break
    adapted_sub_string = "".join(output)
    # print(output_str)
    # print(len(output_str))
    start = text.find(adapted_sub_string)
    return adapted_sub_string, start


def from_paragraphs_to_sentences(document_object):
    new_document_object = OrderedDict()
    new_document_object['level'] = 'sentence'
    new_document_object['lang'] = document_object['lang']
    new_document_object['paragraphs'] = []

    from blingfire import text_to_sentences

    # split in sentences
    for paragraph in document_object['paragraphs']:
        paragraph_text = paragraph['text']
        paragraph_spans = copy.copy(paragraph['spans'])

        sentence_spans = get_sentence_spans(paragraph_text, text_to_sentences(paragraph_text).split("\n"))
        ## Dirty workaround
        for s in paragraph['spans']:
            s['start'] = s['offset_start']
            s['end'] = s['offset_end']
        corrected_sentence_spans = correct_segmentation_block(sentence_spans, paragraph_spans)

        output_sentences = []
        for sentence_span in corrected_sentence_spans:
            contained_spans = list(
                filter(lambda s: s['offset_start'] >= sentence_span['start'] and s['offset_end'] < sentence_span['end'],
                       paragraph_spans))

            for s in contained_spans:
                s['offset_start'] = s['offset_start'] - sentence_span['start']
                s['offset_end'] = s['offset_end'] - sentence_span['start']
                del s['start']
                del s['end']

            output_sentences.append({
                "text": paragraph_text[sentence_span['start']: sentence_span['end']],
                "spans": contained_spans
            })
        new_paragraph = {"text": paragraph_text, 'sentences': output_sentences}
        new_document_object['paragraphs'].append(new_paragraph)

    return new_document_object


def extract_tabular_information(document, use_paragraphs=False):
    # csv_output = [["id", "sentence", "entity1", "entity2", "linked"]]
    csv_output = [["id", "sentence", "linked"]]
    for paragraph in document['paragraphs']:
        if use_paragraphs:
            if len(paragraph['spans']) == 0:
                continue

            write_csv(paragraph, csv_output)
        else:
            for sentence in paragraph['sentences']:
                if len(sentence['spans']) == 0:
                    continue
                write_csv(sentence, csv_output)

    return csv_output


def write_csv(item, csv_output):
    linked_spans = list(filter(lambda s: 'links' in s, item['spans']))

    if len(linked_spans) > 0 and len(item['spans']) > 1:
        for i in range(0, len(item['spans'])):
            for j in range(i + 1, len(item['spans'])):
                if i == j:
                    continue
                entity1 = item['spans'][i]
                entity2 = item['spans'][j]
                if 'links' in entity1:
                    linked = len(list(filter(lambda e: 'id' in entity2 and e['targetId'] == entity2['id'],
                                             entity1['links']))) > 0
                else:
                    linked = False

                linked = 0 if not linked else 1

                # csv_output.append([get_hash(sentence['text']), sentence['text'], entity1['text'], entity2['text'], linked])
                csv_output.append(
                    [hashlib.md5(item['text'].encode('utf-8')).hexdigest(), item['text'], linked])


def write_output(data, path, format, append=False):
    delimiter = "\t" if format == "tsv" else ","
    if not append:
        with open(path, encoding='utf-8', mode='w') as f:
            fw = csv.writer(f, delimiter=delimiter, quotechar='"')
            for row in data:
                fw.writerow(row)
    else:
        with open(path, encoding='utf-8', mode='a') as f:
            fw = csv.writer(f, delimiter=delimiter, quotechar='"')
            for row in data:
                fw.writerow(row)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converts XML (Supermat) to a CSV/TSV file for classification")

    parser.add_argument("--input", help="Input file or directory", required=True)
    parser.add_argument("--output", help="Output directory", required=True)
    parser.add_argument("--recursive", action="store_true", default=False,
                        help="Process input directory recursively. If input is a file, this parameter is ignored.")
    parser.add_argument("--format", default='csv', choices=['tsv', 'csv'],
                        help="Output format.")
    parser.add_argument("--use-paragraphs", action="store_true", default=False, help="Use paragraphs instead of sentences.")

    args = parser.parse_args()

    input = args.input
    output = args.output
    recursive = args.recursive
    format = args.format
    use_paragraphs = args.use_paragraphs

    if os.path.isdir(input):
        path_list = []

        if recursive:
            for root, dirs, files in os.walk(input):
                for file_ in files:
                    if not file_.lower().endswith(".xml"):
                        continue

                    abs_path = os.path.join(root, file_)
                    path_list.append(abs_path)

        else:
            path_list = Path(input).glob('*.xml')

        first = True
        for path in path_list:
            print("Processing: ", path)
            pre_document = process_file(path, use_paragraphs=use_paragraphs)
            if not use_paragraphs:
                document = from_paragraphs_to_sentences(pre_document)
            else:
                document = pre_document

            csv_output = extract_tabular_information(document, use_paragraphs=use_paragraphs)

            if not os.path.isdir(str(output)):
                ## If the output is a file, I stream to it
                parent_dir = Path(output).parent
                output_path = os.path.join(parent_dir, "output." + format)

                if first:
                    write_output(csv_output, output_path, format, append=False)
                    first = False
                else:
                    # remove header, except the first file
                    csv_output.pop(0)
                    write_output(csv_output, output_path, format, append=True)
            else:
                ## If output is a directory a create multiple files
                output_path = os.path.join(output, Path(path).stem.replace(".tei", "") + "." + format)
                write_output(csv_output, output_path, format)



    elif os.path.isfile(input):
        input_path = Path(input)
        pre_document = process_file(input_path, use_paragraphs=use_paragraphs)
        document = from_paragraphs_to_sentences(pre_document)
        output_filename = input_path.stem.replace(".tei", "") + "." + format
        output_path = os.path.join(output, output_filename)
        csv_output = extract_tabular_information(document)
        write_output(csv_output, output_path, format)
