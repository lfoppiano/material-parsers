import argparse
import json
import os
import re
from html import escape
from pathlib import Path

from bs4 import BeautifulSoup, Tag, NavigableString
from supermat.supermat_tei_parser import get_children_list
from tqdm import tqdm

from material_parsers.commons.grobid_client_generic import GrobidClientGeneric
from material_parsers.commons.grobid_tokenizer import tokenizeSimple
from material_parsers.linking.data_model import to_dict_span, to_dict_token
from material_parsers.linking.linking_module import RuleBasedLinker, CriticalTemperatureClassifier

# these are duplicated with constants in RuleBasedLinker because these are easier for command line
MATERIAL_TC_LINK_NAME = "material-tc"
TC_PRESSURE_LINK_NAME = "tc-pressure"
TC_ME_METHOD_LINK_NAME = "tc-me_method"

CRF_ALGO = "crf"
RB_ALGO = "rule-based"


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

    children_tag = get_children_list(soup, verbose=False)
    # list containing text and the dictionary with all the annotations
    paragraphs = []

    # indicate for each pointer, the destination of the link
    rel_ptrs_to = {}
    rel_ptrs_from = {}

    # indicate for each id the related object
    spans_ids = {}
    for child_tag in children_tag:
        for sentence in child_tag:
            sentence_text = ''
            tokens = []
            spans = []
            off_token = 0

            # contains the relations within the same paragraph
            rel_paragraph_ptrs_to = {}
            rel_paragraph_ptrs_from = {}
            spans_paragraph_ids = {}

            for item in sentence.contents:
                if type(item) == NavigableString:
                    sentence_text += str(item)
                    local_tokens, off_token = tokenize_chunk(item.string, off_token)
                    tokens.extend(local_tokens)

                elif type(item) is Tag:
                    sentence_text += str(item.text)
                    entity_class = '<' + str(item.attrs['type']) + '>'

                    token_start = len(tokens)
                    local_tokens, off_token = tokenize_chunk(item.text, off_token)
                    tokens.extend(local_tokens)
                    token_end = token_start + len(local_tokens)

                    id = None
                    if 'xml:id' in item.attrs:
                        id = item.attrs['xml:id']

                    span = to_dict_span(item.text, entity_class, id, offset_start=local_tokens[0]['offset'],
                                        offset_end=local_tokens[0]['offset'] + len(item.text), token_start=token_start,
                                        token_end=token_end)

                    if id not in spans_ids:
                        spans_ids[span['id']] = entity_class
                        spans_paragraph_ids[span['id']] = entity_class

                    if 'corresp' in item.attrs:
                        ptr_raw = item.attrs['corresp']

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
                    # else:
                    # print("The link is pointing outside the current paragraph, therefore is going to be ignored. ")

            paragraph = {'text': sentence_text, 'spans': spans, 'tokens': tokens,
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


def extract_links_same_sentence(paragraphs):
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
                global_links.append((source_id, target_id, RuleBasedLinker.get_link_type(source_type, target_type)))

    return global_links


class GeneralEvaluator:
    pass


class CrfLinkerEvaluation(GeneralEvaluator):

    def __init__(self, config_path, linker_type):
        self.material_parsers_client = GrobidClientGeneric(config_path=config_path, ping=True)
        self.linker_type = linker_type[1:-1]

    def run_linking(self, paragraphs):
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
                output_text += escape(paragraph['text'][offset: span['offset_start']])
                offset = span['offset_start']
                output_text += span['type'].replace(">", " id='" + str(span['id']) + "'>")
                if span['text'].endswith(" "):
                    output_text += escape(span['text'][0:-1]) + span['type'].replace("<", "</") + " "
                else:
                    output_text += escape(span['text']) + span['type'].replace("<", "</")

                offset += len(span['text'])

            output_text += escape(paragraph['text'][offset:])

            output = json.loads(
                self.material_parsers_client.process({"text": output_text, "type": self.linker_type}, 'linker'))

            predicted_links.extend(extract_predicted_links(output[0]))

        return predicted_links


class RuleBasedLinkerEvaluation(GeneralEvaluator):
    def __init__(self, source, destination):
        self.source = source
        self.destination = destination

        self.rb_linker = RuleBasedLinker(source, destination)
        self.tc_classifier = None

        self.entities_types = [self.source, self.destination]

        if self.source == "<tcValue>" or self.destination == "<tcValue>":
            self.tc_classifier = CriticalTemperatureClassifier()
            self.entities_types.remove("<tcValue>")

    def run_linking(self, sentences):
        predicted_links = []

        for sentence in sentences:
            sentence_marked = sentence
            if self.tc_classifier is not None:
                sentence_marked = self.tc_classifier.mark_temperatures_paragraph(sentence)

            for marked_spans in sentence_marked['spans'] if 'spans' in sentence_marked else []:
                if marked_spans['type'] in self.entities_types or marked_spans['linkable']:
                    for s_ in filter(lambda s: str(s['id']) == marked_spans['id'], sentence['spans']):
                        s_['linkable'] = True

            output_paragraph = self.rb_linker.process_paragraph(sentence)

            # TODO: understand this
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


def extract_predicted_links(sentence):
    predicted_links = []
    for span in sentence['spans'] if 'spans' in sentence else []:
        for link in span['links'] if 'links' in span else []:
            targetId = link['targetId']
            targetType = link['targetType']

            sourceId = span['id']
            sourceType = span['type']

            targets_in_paragraph = [span_['id'] for span_ in sentence['spans'] if
                                    str(span_['id']) == str(targetId)]
            link_type = RuleBasedLinker.get_link_type(sourceType, targetType)
            if len(targets_in_paragraph) > 0 and (targetId, sourceId, link_type) not in predicted_links:
                predicted_links.append((sourceId, targetId, link_type))

    return predicted_links


def compute_metrics(expected_links, predicted_links, link_type=None):
    output = {'labels': {}, 'macro': {}, 'micro': {}}
    if link_type:
        output['labels'][link_type] = compute_metrics_by_type(expected_links, predicted_links, link_type)
    else:
        for link_type in [RuleBasedLinker.MATERIAL_TC_TYPE, RuleBasedLinker.TC_PRESSURE_TYPE,
                          RuleBasedLinker.TC_ME_METHOD_TYPE]:
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
    name_width = max([len(e) for e in evaluation['labels'].keys()]) if 'labels' in evaluation else 0

    last_line_heading = {
        'micro': 'all (micro avg.)',
        'macro': 'all (macro avg.)'
    }
    width = max(name_width, len(last_line_heading['micro']), digits)

    headers = ["precision", "recall", "f1-score", "support"]
    head_fmt = u'{:>{width}s} ' + u' {:>9}' * len(headers)
    report = head_fmt.format(u'', *headers, width=width)
    report += u'\n\n'

    row_fmt = u'{:>{width}s} ' + u' {:>9.{digits}f}' * 3 + u' {:>9.{digits}f}\n'

    if 'labels' in evaluation:
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
    parser = argparse.ArgumentParser(
        description="Linking evaluation")

    parser.add_argument("--input", help="Input file or directory", required=True, type=Path)
    parser.add_argument("--method", help="Select the algorithm to evaluate", choices=[CRF_ALGO, RB_ALGO, "all"],
                        required=True, type=str)
    parser.add_argument("--task", help="Which task to evaluate",
                        choices=[MATERIAL_TC_LINK_NAME, TC_PRESSURE_LINK_NAME, TC_ME_METHOD_LINK_NAME, "all"],
                        type=str, required=True)
    parser.add_argument("--grobid-config", help="Grobid superconductors YAML configuration", type=str, required=False)

    args = parser.parse_args()
    input = args.input
    methods = [CRF_ALGO, RB_ALGO] if args.method == "all" else [args.method]
    task = args.task
    tasks = [MATERIAL_TC_LINK_NAME, TC_PRESSURE_LINK_NAME, TC_ME_METHOD_LINK_NAME] if task == "all" else [task]
    grobid_config = args.grobid_config

    tasks_map = {
        # Source, destination
        MATERIAL_TC_LINK_NAME: ("<tcValue>", "<material>", RuleBasedLinker.MATERIAL_TC_TYPE),
        TC_PRESSURE_LINK_NAME: ("<pressure>", "<tcValue>", RuleBasedLinker.TC_PRESSURE_TYPE),
        TC_ME_METHOD_LINK_NAME: ("<tcValue>", "<me_method>", RuleBasedLinker.TC_ME_METHOD_TYPE),
    }

    methods_map = {
        'rule-based': RuleBasedLinkerEvaluation(tasks_map[task][0], tasks_map[task][1])
    }

    if CRF_ALGO in methods:
        methods_map[CRF_ALGO] = CrfLinkerEvaluation(grobid_config, tasks_map[task][2])

    expected_links_map = {}
    files_map = {}
    metrics_map = {}

    if os.path.isdir(input):
        for root, dirs, files in os.walk(input):
            for file_ in files:
                if not file_.lower().endswith(".xml"):
                    continue
                abs_path = os.path.join(root, file_)
                # print("Processing: " + str(abs_path))
                paragraphs, rel_ptrs_from, rel_ptrs_to = read_evaluation_file(str(abs_path))
                expected_links = extract_links_same_sentence(paragraphs)

                expected_links_map[abs_path] = expected_links
                files_map[abs_path] = {
                    'paragraphs': paragraphs,
                    'relations_from': rel_ptrs_from,
                    'relations_to': rel_ptrs_to
                }

        file_count = len(files_map.keys())

        for method in methods:
            metrics_map[method] = {
                'avg_counters': {
                    'avg_num_correct': 0,
                    'avg_num_wrong': 0,
                    'count_num_expected': 0
                },
                'avg_metrics': {
                    'avg_macro_precision': 0,
                    'avg_macro_recall': 0,
                    'avg_macro_f1': 0,
                    'avg_support': 0
                },
                'files': []
            }

            for path in tqdm(files_map.keys()):
                impl = methods_map.get(method)

                expected_links = expected_links_map[path]
                predicted_links = impl.run_linking(files_map[path]['paragraphs'])

                ## MICRO AVERAGE
                counters_by_type = compute_counters_by_type(expected_links, predicted_links, tasks_map[task][2])
                metrics_map[method]['avg_counters']['avg_num_correct'] += counters_by_type['num_correct']
                metrics_map[method]['avg_counters']['avg_num_wrong'] += counters_by_type['num_wrong']
                metrics_map[method]['avg_counters']['count_num_expected'] += counters_by_type['num_expected']

                ## MACRO AVERAGE
                metrics_by_type = compute_metrics_by_type(expected_links, predicted_links, tasks_map[task][2])
                # print(get_report({"labels": {RuleBasedLinker.MATERIAL_TC_TYPE: metrics_by_type_rb}}))

                metrics_map[method]['avg_metrics']['avg_macro_precision'] += metrics_by_type['precision']
                metrics_map[method]['avg_metrics']['avg_macro_recall'] += metrics_by_type['recall']
                metrics_map[method]['avg_metrics']['avg_macro_f1'] += metrics_by_type['f1']
                metrics_map[method]['avg_metrics']['avg_support'] += metrics_by_type['support']

                metrics_map[method]['files'].append(
                    {'counters': counters_by_type, 'metrics': metrics_by_type, 'predicted': predicted_links})

            # Compute average metrics
            metrics_map[method]['avg_metrics']['avg_support'] = metrics_map[method]['avg_metrics'][
                                                                    'avg_support']

            # Macro average
            metrics_map[method]['avg_metrics']['avg_macro_precision'] = metrics_map[method]['avg_metrics'][
                                                                            'avg_macro_precision'] / file_count if file_count > 0 else 0
            metrics_map[method]['avg_metrics']['avg_macro_recall'] = metrics_map[method]['avg_metrics'][
                                                                         'avg_macro_recall'] / file_count if file_count > 0 else 0
            metrics_map[method]['avg_metrics']['avg_macro_f1'] = metrics_map[method]['avg_metrics'][
                                                                     'avg_macro_f1'] / file_count if file_count > 0 else 0

            # Micro average
            metrics_map[method]['avg_metrics']['avg_micro_precision'] = metrics_map[method]['avg_counters'][
                                                                            'avg_num_correct'] / (
                                                                            metrics_map[method]['avg_counters'][
                                                                                'avg_num_correct'] +
                                                                            metrics_map[method]['avg_counters'][
                                                                                'avg_num_wrong']) if \
                metrics_map[method]['avg_counters']['avg_num_correct'] + metrics_map[method]['avg_counters'][
                    'avg_num_wrong'] > 0 else 0
            metrics_map[method]['avg_metrics']['avg_micro_recall'] = metrics_map[method]['avg_counters'][
                                                                         'avg_num_correct'] / \
                                                                     metrics_map[method]['avg_counters'][
                                                                         'count_num_expected'] if \
                metrics_map[method]['avg_counters']['count_num_expected'] > 0 else 0
            metrics_map[method]['avg_metrics']['avg_micro_f1'] = 2 * (
                metrics_map[method]['avg_metrics']['avg_micro_precision'] * metrics_map[method]['avg_metrics'][
                'avg_micro_recall']) / (
                                                                     metrics_map[method]['avg_metrics'][
                                                                         'avg_micro_precision'] +
                                                                     metrics_map[method]['avg_metrics'][
                                                                         'avg_micro_recall']) if \
                metrics_map[method]['avg_metrics']['avg_micro_precision'] + metrics_map[method]['avg_metrics'][
                    'avg_micro_recall'] > 0 else 0

            report_data = {
                "labels": {
                    tasks_map[task][2] + " macro avg.": {
                        "precision": metrics_map[method]['avg_metrics']['avg_macro_precision'],
                        "recall": metrics_map[method]['avg_metrics']['avg_macro_recall'],
                        "f1": metrics_map[method]['avg_metrics']['avg_macro_f1'],
                        "support": metrics_map[method]['avg_metrics']['avg_support']
                    },
                    tasks_map[task][2] + " micro avg.": {
                        "precision": metrics_map[method]['avg_metrics']['avg_micro_precision'],
                        "recall": metrics_map[method]['avg_metrics']['avg_micro_recall'],
                        "f1": metrics_map[method]['avg_metrics']['avg_micro_f1'],
                        "support": metrics_map[method]['avg_metrics']['avg_support']
                    }
                }
            }

            print(method)
            print(get_report(report_data, digits=4, include_avgs=[]))

    elif os.path.isfile(input):
        input_path = Path(input)
        paragraphs, rel_ptrs_from, rel_ptrs_to = read_evaluation_file(str(input_path))
        expected_links = extract_links_same_sentence(paragraphs)
        for method in methods:
            file_count = 0
            impl = methods_map.get(method)
            predicted_links = impl.run_linking(paragraphs)
            metrics_by_type = compute_metrics_by_type(expected_links, predicted_links, tasks_map[task][2])

            print(method)
            print(get_report({"labels": {tasks_map[task][2]: metrics_by_type}}))
