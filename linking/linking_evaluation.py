# transform tei to csv for classification
import json
import os
import re
import sys
from html import escape
from pathlib import Path
from sys import argv

from bs4 import BeautifulSoup, NavigableString, Tag

from data_model import to_dict_span, to_dict_token
from grobid_client_generic import grobid_client_generic
from grobid_tokenizer import tokenizeSimple
from linking_module import process_paragraph, get_link_type, MATERIAL_TC_TYPE, TC_PRESSURE_TYPE, TC_ME_METHOD_TYPE


def tokenise(string):
    return tokenizeSimple(string)


def read_evaluation_file(finput):
    with open(finput, encoding='utf-8') as fp:
        doc = fp.read()

    # move the space within the tag - not sure why...
    mod_tags = re.finditer(r'(</\w+>) ', doc)
    for mod in mod_tags:
        doc = doc.replace(mod.group(), ' ' + mod.group(1))
    #     print(doc)
    soup = BeautifulSoup(doc, 'xml')

    ## Find the root node in the xml tree
    root = None
    for child in soup.tei.children:
        if child.name == 'text':
            root = child

    # list containing text and the dictionary with all the annotations
    paragraphs = []

    # indicate for each pointer, the destination of the link
    rel_ptrs_to = {}
    rel_ptrs_from = {}

    # indicate for each id the related object
    spans_ids = {}

    for i, pTag in enumerate(root('p')):
        paragraph_text = ''
        tokens = []
        spans = []
        off_token = 0

        # contains the relations within the same paragraph
        rel_paragraph_ptrs_to = {}
        rel_paragraph_ptrs_from = {}
        spans_paragraph_ids = {}

        for item in pTag.contents:
            if type(item) == NavigableString:
                paragraph_text += str(item)
                local_tokens, off_token = tokenize_chunk(item.string, off_token)
                tokens.extend(local_tokens)

            elif type(item) is Tag:
                paragraph_text += item.text
                entity_class = '<' + item.name + '>'

                token_start = len(tokens)
                local_tokens, off_token = tokenize_chunk(item.text, off_token)
                tokens.extend(local_tokens)
                token_end = token_start + len(local_tokens)

                id = None
                if 'id' in item.attrs:
                    id = item.attrs['id']

                span = to_dict_span(item.string, entity_class, id, offsetStart=local_tokens[0]['offset'],
                                    offsetEnd=local_tokens[0]['offset'] + len(paragraph_text), tokenStart=token_start,
                                    tokenEnd=token_end)

                if id not in spans_ids:
                    spans_ids[span['id']] = entity_class
                    spans_paragraph_ids[span['id']] = entity_class

                if 'ptr' in item.attrs:
                    ptr_raw = item.attrs['ptr']

                    splits = ptr_raw.split(',')
                    for ptr in splits:
                        ptr_clean = ptr.replace('#', '')

                        if ptr_clean not in rel_ptrs_to:
                            rel_ptrs_to[ptr_clean] = {span['id']: entity_class}
                        else:
                            rel_ptrs_to[ptr_clean][span['id']] = entity_class

                        if ptr_clean not in rel_paragraph_ptrs_to:
                            rel_paragraph_ptrs_to[ptr_clean] = {span['id']: entity_class}
                        else:
                            rel_paragraph_ptrs_to[ptr_clean][span['id']] = entity_class

                        # if span['id'] not in rel_ptrs_from:
                        #     rel_ptrs_from[span['id']] = [[ptr_clean, entity_class]]
                spans.append(span)

        off_token += 1  # return

        for ptr_to, sources in rel_paragraph_ptrs_to.items():
            for source_id, source_type in sources.items():
                if ptr_to in spans_paragraph_ids:
                    other_type = spans_ids[ptr_to]
                    if source_id not in rel_paragraph_ptrs_from:
                        rel_paragraph_ptrs_from[source_id] = {ptr_to: other_type}
                    else:
                        rel_paragraph_ptrs_from[source_id][ptr_to] = other_type
                else:
                    print("The link is pointing outside the current paragraph, therefore is going to be ignored. ")

        paragraph = {'text': paragraph_text, 'spans': spans, 'tokens': tokens,
                     'rel_ptrs_from': rel_paragraph_ptrs_from, 'rel_ptrs_to': rel_paragraph_ptrs_to}
        paragraphs.append(paragraph)

    # Populating the inverted map
    for ptr_to, sources in rel_ptrs_to.items():
        for other_id, other_type in sources.items():
            if other_id not in rel_ptrs_from:
                rel_ptrs_from[other_id] = {ptr_to: other_type}
            else:
                rel_ptrs_from[other_id][ptr_to] = other_type

    return paragraphs, rel_ptrs_from, rel_ptrs_to


def tokenize_chunk(text, start_offset):
    token_list = tokenise(text)

    output_tokens = []

    # if token_list[0] == ' ':  # remove space after the tag, if occurring
    #     del token_list[0]
    current_offset = start_offset
    for token in token_list:
        # if token.rstrip(' '):
        output_tokens.append(to_dict_token(token, current_offset))
        current_offset = current_offset + len(token)
        # if token[-1] == ' ':
        #     start_offset += 1
    return output_tokens, current_offset


def extract_links(paragraphs, rel_ptrs_from, rel_ptrs_to):
    pass


def extract_links_same_paragraphs(paragraphs):
    """
        This method will ignore the links that are going outside the current paragraph
    """
    global_links = []
    for paragraph in paragraphs:
        rel_paragraph_ptrs_from = paragraph['rel_ptrs_from']
        rel_paragraph_ptrs_to = paragraph['rel_ptrs_to']
        # local_links = []

        for source_id, targets in rel_paragraph_ptrs_from.items():
            # local_links.append((rel_from, target[0]))
            for target_id, target_type in targets.items():
                source_type = rel_paragraph_ptrs_to[target_id][source_id]
                global_links.append((source_id, target_id, get_link_type(source_type, target_type)))

    return global_links


def run_linking_crf(paragraphs):
    predicted_links = []
    for paragraph in paragraphs:
        output_text = ""
        offset = 0
        if len([span for span in (paragraph['spans'] if 'spans' in paragraph else []) if
                span['type'] == "<material>"]) == 0 or len(
            [span for span in (paragraph['spans'] if 'spans' in paragraph else []) if
             span['type'] == "<tcValue>"]) == 0:
            continue

        for span in paragraph['spans'] if 'spans' in paragraph else []:
            output_text += escape(paragraph['text'][offset: span['offsetStart']])
            offset = span['offsetStart']
            output_text += span['type'].replace(">", " id='" + str(span['id']) + "'>")
            if span['text'].endswith(" "):
                output_text += escape(span['text'][0:-1]) + span['type'].replace("<", "</") + " "
            else:
                output_text += escape(span['text']) + span['type'].replace("<", "</")

            offset += len(span['text'])

        output_text += escape(paragraph['text'][offset:])

        output = json.loads(grobid_client_generic().process_text(output_text, 'linker'))

        predicted_links.extend(extract_predicted_links(output[0]))

    return predicted_links


def run_linking_rule_based(paragraphs):
    predicted_links = []

    for paragraph in paragraphs:
        output_paragraph = process_paragraph(paragraph)

        if len(output_paragraph) == 1:
            merged_paragraph = output_paragraph[0]
        elif len(output_paragraph) > 1:
            # Merge the sentences in a single paragraph, to have consistency in evaluation
            merged_paragraph = {
                "text": "",
                "spans": [],
                "tokens": []
            }
            for sentence in output_paragraph:
                merged_paragraph['text'] += sentence['text']
                merged_paragraph['spans'].extend(sentence['spans'])
                # merged_paragraph['tokens'].extend(sentence['tokens'])
        else:
            break

        predicted_links.extend(extract_predicted_links(merged_paragraph))

    return predicted_links


def extract_predicted_links(paragraph):
    predicted_links = []
    for span in paragraph['spans'] if 'spans' in paragraph else []:
        for link in span['links'] if 'links' in span else []:
            targetId = link['targetId']
            targetType = link['targetType']

            sourceId = span['id']
            sourceType = span['type']

            targets_in_paragraph = [span_['id'] for span_ in paragraph['spans'] if
                                    str(span_['id']) == str(targetId)]
            link_type = get_link_type(sourceType, targetType)
            if len(targets_in_paragraph) > 0 and (targetId, sourceId, link_type) not in predicted_links:
                predicted_links.append((sourceId, targetId, link_type))

    return predicted_links


def compute_metrics(expected_links, predicted_links, link_type=None):
    output = {'labels': {}, 'macro': {}, 'micro': {}}
    if link_type:
        output['labels'][link_type] = compute_metrics_by_type(expected_links, predicted_links, link_type)
    else:
        for link_type in [MATERIAL_TC_TYPE, TC_PRESSURE_TYPE, TC_ME_METHOD_TYPE]:
            output['labels'][link_type] = compute_metrics_by_type(expected_links, predicted_links, link_type)

    return output


def compute_metrics_by_type(expected_links, predicted_links, link_type):
    expected_links = [link for link in expected_links if link[2] == link_type]
    predicted_links = [link for link in predicted_links if link[2] == link_type]

    correct_links = 0  # TP
    wrong_links = 0  # FP
    total_expected_links = len(expected_links)
    total_predicted_links = len(predicted_links)

    for link in predicted_links:
        link_from = str(link[0])
        link_to = str(link[1])

        corresponding_expected_links = [link for link in expected_links if
                                        (str(link[0]) == link_from and str(link[1]) == link_to) or (
                                            str(link[1]) == link_from and str(link[0]) == link_to)]

        if len(corresponding_expected_links) > 0:
            correct_links += 1
        else:
            wrong_links += 1

    precision = correct_links / (correct_links + wrong_links) if correct_links + wrong_links > 0 else 0
    recall = correct_links / total_expected_links if total_expected_links > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0
    support = total_expected_links

    return {'precision': precision, 'recall': recall, 'f1': f1, 'support': support}


## The difference with the method above is that we compute the TP, TF and so on for the micro average
def compute_counters_by_type(expected_links, predicted_links, link_type):
    expected_links = [link for link in expected_links if link[2] == link_type]
    predicted_links = [link for link in predicted_links if link[2] == link_type]

    correct_links = 0  # TP
    wrong_links = 0  # FP
    total_expected_links = len(expected_links)
    # total_predicted_links = len(predicted_links)

    for link in predicted_links:
        link_from = str(link[0])
        link_to = str(link[1])

        corresponding_expected_links = [link for link in expected_links if
                                        (str(link[0]) == link_from and str(link[1]) == link_to) or (
                                            str(link[1]) == link_from and str(link[0]) == link_to)]

        if len(corresponding_expected_links) > 0:
            correct_links += 1
        else:
            wrong_links += 1

    return {'num_correct': correct_links, 'num_wrong': wrong_links, 'num_expected': total_expected_links}


# This comes from https://github.com/kermitt2/delft/blob/master/delft/sequenceLabelling/evaluation.py
def get_report(evaluation, digits=2, include_avgs=[]):
    """
    Calculate the report from the evaluation metrics.
    :param evaluation: the map for evaluation containing three keys:
        - 'labels', a map of maps contains the values of precision, recall, f1 and support for each label
        - 'macro' and 'micro', containing the micro and macro average, respectively (precision, recall, f1 and support)
    :param digits: the number of digits to use in the report
    :param include_avgs: the average to include in the report, default: 'micro'
    :return:
    """
    name_width = max([len(e) for e in evaluation.keys()])

    last_line_heading = {
        'micro': 'all (micro avg.)',
        'macro': 'all (macro avg.)'
    }
    width = max(name_width, len(last_line_heading['micro']), digits)

    headers = ["precision", "recall", "f1-score", "support"]
    head_fmt = u'{:>{width}s} ' + u' {:>9}' * len(headers)
    report = head_fmt.format(u'', *headers, width=width)
    report += u'\n\n'

    row_fmt = u'{:>{width}s} ' + u' {:>9.{digits}f}' * 3 + u' {:>9}\n'

    block = evaluation['labels']
    labels = sorted(block.keys())

    for label in labels:
        p = block[label]['precision']
        r = block[label]['recall']
        f1 = block[label]['f1']
        s = block[label]['support']

        report += row_fmt.format(*[label, p, r, f1, s], width=width, digits=digits)

    report += u'\n'
    for average in include_avgs:
        avg = evaluation[average]
        report += row_fmt.format(last_line_heading[average],
                                 avg['precision'],
                                 avg['recall'],
                                 avg['f1'],
                                 avg['support'] if 'support' in avg else "",
                                 width=width, digits=digits)

    return report


if __name__ == '__main__':
    if len(argv) != 2:
        print("Invalid parameters. Usage: python linking_evaluation.py")
        sys.exit(-1)

    input = argv[1]

    file_count = 0
    avg_macro_precision_rb = 0
    avg_macro_recall_rb = 0
    avg_macro_f1_rb = 0
    avg_support_rb = 0

    avg_num_correct_rb = 0
    avg_num_wrong_rb = 0
    count_num_expected_rb = 0

    avg_macro_precision_crf = 0
    avg_macro_recall_crf = 0
    avg_macro_f1_crf = 0
    avg_support_crf = 0

    avg_num_correct_crf = 0
    avg_num_wrong_crf = 0
    count_num_expected_crf = 0


    if os.path.isdir(input):
        for root, dirs, files in os.walk(input):
            for file_ in files:
                if not file_.lower().endswith(".xml"):
                    continue
                abs_path = os.path.join(root, file_)
                print("Processing: " + str(abs_path))
                paragraphs, rel_ptrs_from, rel_ptrs_to = read_evaluation_file(str(abs_path))
                expected_links = extract_links_same_paragraphs(paragraphs)

                print("Using rule-based")
                predicted_links_rb = run_linking_rule_based(paragraphs)

                ## MICRO AVERAGE
                counters_by_type_rb = compute_counters_by_type(expected_links, predicted_links_rb, MATERIAL_TC_TYPE)
                avg_num_correct_rb += counters_by_type_rb['num_correct']
                avg_num_wrong_rb += counters_by_type_rb['num_wrong']
                count_num_expected_rb += counters_by_type_rb['num_expected']

                ## MACRO AVERAGE
                metrics_by_type_rb = compute_metrics_by_type(expected_links, predicted_links_rb, MATERIAL_TC_TYPE)
                print(get_report({"labels": {MATERIAL_TC_TYPE: metrics_by_type_rb}}))

                avg_macro_precision_rb += metrics_by_type_rb['precision']
                avg_macro_recall_rb += metrics_by_type_rb['recall']
                avg_macro_f1_rb += metrics_by_type_rb['f1']
                avg_support_rb += metrics_by_type_rb['support']

                print("Using CRF")
                predicted_links_crf = run_linking_crf(paragraphs)

                ## MICRO AVERAGE
                counters_by_type_crf = compute_counters_by_type(expected_links, predicted_links_crf, MATERIAL_TC_TYPE)
                avg_num_correct_crf += counters_by_type_crf['num_correct']
                avg_num_wrong_crf += counters_by_type_crf['num_wrong']
                count_num_expected_crf += counters_by_type_crf['num_expected']

                ## MACRO AVERAGE
                metrics_by_type_crf = compute_metrics_by_type(expected_links, predicted_links_crf, MATERIAL_TC_TYPE)
                print(get_report({"labels": {MATERIAL_TC_TYPE: metrics_by_type_crf}}))

                avg_macro_precision_crf += metrics_by_type_crf['precision']
                avg_macro_recall_crf += metrics_by_type_crf['recall']
                avg_macro_f1_crf += metrics_by_type_crf['f1']
                avg_support_crf += metrics_by_type_crf['support']

                file_count += 1

        print("Rule-based")
        avg_support_rb = avg_support_rb / file_count if file_count > 0 else 0

        print("Macro average Rules-based")
        avg_macro_precision_rb = avg_macro_precision_rb / file_count if file_count > 0 else 0
        avg_macro_recall_rb = avg_macro_recall_rb / file_count if file_count > 0 else 0
        avg_macro_f1_rb = avg_macro_f1_rb / file_count if file_count > 0 else 0

        print(get_report({"labels": {
            MATERIAL_TC_TYPE: {"precision": avg_macro_precision_rb, "recall": avg_macro_recall_rb, "f1": avg_macro_f1_rb,
                               "support": avg_support_rb}}}))

        print("Micro average Rules-based")
        avg_micro_precision_rb = avg_num_correct_rb / (
            avg_num_correct_rb + avg_num_wrong_rb) if avg_num_correct_rb + avg_num_wrong_rb > 0 else 0
        avg_micro_recall_rb = avg_num_correct_rb / count_num_expected_rb if count_num_expected_rb > 0 else 0
        avg_micro_f1_rb = 2 * (avg_micro_precision_rb * avg_micro_recall_rb) / (
            avg_micro_precision_rb + avg_micro_recall_rb) if avg_micro_precision_rb + avg_micro_recall_rb > 0 else 0
        print(get_report({"labels": {
            MATERIAL_TC_TYPE: {"precision": avg_micro_precision_rb, "recall": avg_micro_recall_rb, "f1": avg_micro_f1_rb,
                               "support": avg_support_rb}}}))

        print("CRF")
        avg_support_crf = avg_support_crf / file_count if file_count > 0 else 0

        print("Macro average CRF")
        avg_macro_precision_crf = avg_macro_precision_crf / file_count if file_count > 0 else 0
        avg_macro_recall_crf = avg_macro_recall_crf / file_count if file_count > 0 else 0
        avg_macro_f1_crf = avg_macro_f1_crf / file_count if file_count > 0 else 0

        print(get_report({"labels": {
            MATERIAL_TC_TYPE: {"precision": avg_macro_precision_crf, "recall": avg_macro_recall_crf,
                               "f1": avg_macro_f1_crf,
                               "support": avg_support_crf}}}))

        print("Micro average CRF")
        avg_micro_precision_crf = avg_num_correct_crf / (
            avg_num_correct_crf + avg_num_wrong_crf) if avg_num_correct_crf + avg_num_wrong_crf > 0 else 0
        avg_micro_recall_crf = avg_num_correct_crf / count_num_expected_crf if count_num_expected_crf > 0 else 0
        avg_micro_f1_crf = 2 * (avg_micro_precision_crf * avg_micro_recall_crf) / (
            avg_micro_precision_crf + avg_micro_recall_crf) if avg_micro_precision_crf + avg_micro_recall_crf > 0 else 0
        print(get_report({"labels": {
            MATERIAL_TC_TYPE: {"precision": avg_micro_precision_crf, "recall": avg_micro_recall_crf,
                               "f1": avg_micro_f1_crf,
                               "support": avg_support_crf}}}))


    elif os.path.isfile(input):
        input_path = Path(input)
        paragraphs, rel_ptrs_from, rel_ptrs_to = read_evaluation_file(str(input_path))
        expected_links = extract_links_same_paragraphs(paragraphs)
        predicted_links_rb = run_linking_rule_based(paragraphs)
        metrics_by_type_rb = compute_metrics_by_type(expected_links, predicted_links_rb, MATERIAL_TC_TYPE)
        print("== Rule based ==")
        print(get_report({"labels": {MATERIAL_TC_TYPE: metrics_by_type_rb}}))

        predicted_links_crf = run_linking_crf(paragraphs)
        metrics_by_type_crf = compute_metrics_by_type(expected_links, predicted_links_crf, MATERIAL_TC_TYPE)
        print("== CRF based ==")
        print(get_report({"labels": {MATERIAL_TC_TYPE: metrics_by_type_crf}}))
