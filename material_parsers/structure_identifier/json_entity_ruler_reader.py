#!/usr/bin/env python
# coding: utf8

"""Example of defining a knowledge base in spaCy

Compatible with: spaCy v3.1.0
Last tested with: v3.1.0
"""
from __future__ import unicode_literals, print_function

import json
import re
import time
from itertools import permutations
from pathlib import Path

import plac
import spacy
from spacy.pipeline import EntityRuler


def process_paragraph(tokens):
    output_tokens = []
    output_spaces = []
    first = True
    skip = False

    for index, token in enumerate(tokens):
        if skip:
            skip = False
            continue
        if first:
            if not token['text'] == ' ':
                output_tokens.append(token['text'])
                if index + 1 < len(tokens):
                    if tokens[index + 1]['text'] == ' ':
                        output_spaces.append(True)
                        skip = True
                    else:
                        output_spaces.append(False)
                else:
                    output_spaces.append(False)
            else:
                output_tokens.append(' ')
                output_spaces.append(False)
            first = False
        else:
            if not token['text'] == ' ':
                if token['text'].isalpha():
                    output_tokens.append(token['text'])
                    if index + 1 < len(tokens):
                        if tokens[index + 1]['text'] == ' ':
                            output_spaces.append(True)
                            skip = True
                        else:
                            output_spaces.append(False)
                    else:
                        output_spaces.append(False)
                else:
                    output_tokens.append(token['text'])
                    if index + 1 < len(tokens):
                        if tokens[index + 1]['text'] == ' ':
                            output_spaces.append(True)
                            skip = True
                        else:
                            output_spaces.append(False)
                    else:
                        output_spaces.append(False)
            else:
                output_tokens.append(token['text'])
                if index + 1 < len(tokens):
                    if tokens[index + 1]['text'] == ' ':
                        output_spaces.append(True)
                        skip = True
                    else:
                        output_spaces.append(False)
                else:
                    output_spaces.append(False)

    reconstructed_tokens = []
    reconstructed_index = 0
    for x in range(0, len(output_tokens)):
        reconstructed_tokens.append(output_tokens[x])
        if tokens[reconstructed_index]['text'] != reconstructed_tokens[reconstructed_index]:
            print("Mismatch between", tokens[reconstructed_index]['text'], "and",
                  reconstructed_tokens[reconstructed_index])
        reconstructed_index += 1

        if output_spaces[x]:
            reconstructed_tokens.append(" ")
            if tokens[reconstructed_index]['text'] != " ":
                print("Mismatch space, got instead", tokens[reconstructed_index]['text'])
            reconstructed_index += 1

    if not len(output_tokens) == len(output_spaces):
        print("Something wrong in the final length check! len(outputTokens) = " + str(
            len(output_tokens)) + ", len(outputSpaces) = " + str(len(output_spaces)))

    return output_tokens, output_spaces


@plac.annotations(
    model=(
        "Model name, should have pretrained word embeddings",
        "positional", None, str),
    input_file=("Patterns input file", "option", "i", Path),
    name=("name", "positional", None, str,
          ["space-groups", "crystal-structure"]),
    output_dir=("Optional output directory", "option", "o", Path),
)
def main(model, input_file, name, output_dir=None):
    nlp = spacy.load(model)  # load existing spaCy model
    print("Loaded model '%s'" % model)

    processing_map = {
        "space-groups": SpaceGroupsReader(nlp),
        "crystal-structure": CrystalStructureReader(nlp)
    }

    if name not in processing_map:
        raise ValueError(
            "The kb_name does not exists in our mapping: " + str(name))

    # check the length of the nlp vectors
    if "vectors" not in nlp.meta or not nlp.vocab.vectors.size:
        raise ValueError(
            "The `nlp` object should have access to pretrained word vectors, "
            " cf. https://spacy.io/usage/models#languages."
        )

    reader = processing_map.get(name)

    print("Loading patterns for", name)
    start_time = time.time()

    # Reading the CSV file
    patterns = reader.read_file(input_file)

    patterns_with_labels = [{'label': name if 'label' not in pattern else pattern['label'], 'pattern': pattern['pattern']} for pattern in
                            patterns]
    print("Finished creating patterns. Elapsed:", time.time() - start_time, " patterns:", len(patterns_with_labels))

    # Creating the entity ruler
    entity_ruler = EntityRuler(nlp, overwrite_ents=False, validate=True, phrase_matcher_attr='LOWER')

    ## Since we don't need the tagger, we disable all the pipeline.
    other_pipes = [p for p in nlp.pipe_names]

    with nlp.disable_pipes(*other_pipes):
        entity_ruler.add_patterns(patterns_with_labels)

    # save model to output directory
    if output_dir is not None:
        output_dir = Path(output_dir)
        if not output_dir.exists():
            output_dir.mkdir()

        entity_ruler_path = output_dir
        entity_ruler.to_disk(entity_ruler_path)
        print()
        print("Saved entity ruler to", entity_ruler_path)


class BaseReader:

    def __init__(self, nlp):
        self.nlp = nlp
        self.pattern_set = set()


class CrystalStructureReader(BaseReader):
    entity_name = "CrystalStructureReader"
    regex_elements = re.compile(r'([A-Za-z]{1,2})([0-9.]{0,3})')

    def read_file(self, input_file: Path):
        patterns = []

        data = []
        with open(input_file, 'r') as file:
            data = json.load(file)

        if not data:
            return patterns

        compounds = []
        for item in data:
            name = item['name'] if 'name' in item else ''
            type = item['type'] if 'type' in item else None
            if not name:
                print("Name is empty or None, skipping it. ")
                continue

            if "(" in name:
                pass
            elif "[" in name:
                pass
            else:
                local_compound = []
                ## Split by space then extract compounds
                split = name.split(" ")
                for element in split:
                    match = self.regex_elements.match(element)
                    if match.group():
                        local_compound.append((match.group(1), match.group(2)))
                compounds.append(local_compound)

            patterns_created = []
            for c in compounds:
                tmp_patterns = []
                for perm in permutations(c):

                    ## without spaces
                    pattern = ""
                    for ele in perm:
                        pattern += ele[0] + ele[1]
                    # tmp_patterns.append({"pattern": pattern})
                    tmp_patterns.append({"pattern": pattern + "-type"})
                    tmp_patterns.append({"pattern": pattern + "- type"})
                    tmp_patterns.append({"pattern": pattern + " - type"})
                    tmp_patterns.append({"pattern": pattern + " -type"})

                    ## with spaces between any element (including atom charge)
                    pattern = ""
                    first = True
                    for ele in perm:
                        if first:
                            first = False
                        else:
                            pattern += " "
                        if ele[1]:
                            pattern += ele[0] + " " + ele[1]
                        else:
                            pattern += ele[0]
                    # tmp_patterns.append({"pattern": pattern})
                    tmp_patterns.append({"pattern": pattern + "-type"})
                    tmp_patterns.append({"pattern": pattern + "- type"})
                    tmp_patterns.append({"pattern": pattern + " - type"})
                    tmp_patterns.append({"pattern": pattern + " -type"})

                    ## with spaces between any element 
                    pattern = ""
                    first = True
                    for ele in perm:
                        if first:
                            first = False
                        else:
                            pattern += " "
                        if ele[1]:
                            pattern += ele[0] + ele[1]
                        else:
                            pattern += ele[0]
                    # tmp_patterns.append({"pattern": pattern})
                    tmp_patterns.append({"pattern": pattern + "-type"})
                    tmp_patterns.append({"pattern": pattern + "- type"})
                    tmp_patterns.append({"pattern": pattern + " - type"})
                    tmp_patterns.append({"pattern": pattern + " -type"})
                patterns_created.extend(tmp_patterns)

            for pattern_created in patterns_created:
                if 'pattern' in pattern_created and str(pattern_created['pattern']) not in self.pattern_set:
                    patterns.append(pattern_created)
                    self.pattern_set.add(str(pattern_created['pattern']))

        return patterns


class SpaceGroupsReader(BaseReader):
    entity_name = "SpaceGroup Reader"

    def read_file(self, input_file: Path):
        patterns = []
        structure_types = set()

        data = []
        with open(input_file, 'r') as file:
            data = json.load(file)

        if not data:
            return patterns

        for item in data:
            name = item['name'] if 'name' in item else ''
            type = item['type'] if 'type' in item else None
            if type:
                structure_types.add(type)

            if not name:
                print("Name is empty or None, skipping it. ")
                continue

            items = [{'name': name, 'type': type}]
            tmp_items = []
            if '_' in name:
                tmp_items.append({'name': name.replace("_", " "), 'type': type})
                tmp_items.append({'name': name.replace("_", ""), 'type': type})

            if '/' in name:
                for tmp_item in tmp_items.copy():
                    tmp_items.append({'name': tmp_item['name'].replace("/", " /"), 'type': tmp_item['type']})
                    tmp_items.append({'name': tmp_item['name'].replace("/", " / "), 'type': tmp_item['type']})
                    tmp_items.append({'name': tmp_item['name'].replace("/", "/ "), 'type': tmp_item['type']})

            items.extend(tmp_items)
            patterns_created = [{"pattern": str(item['name']), "type": str(item['type'])} for item in items]
            for pattern_created in patterns_created:
                if 'pattern' in pattern_created and str(pattern_created['pattern']) not in self.pattern_set:
                    patterns.append(pattern_created)
                    self.pattern_set.add(str(pattern_created['pattern']))

            for structure_type in structure_types:
                patterns.append({"pattern": str(structure_type), "label": "lattice-type"})

        return patterns


if __name__ == "__main__":
    plac.call(main)
