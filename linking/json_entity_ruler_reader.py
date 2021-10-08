#!/usr/bin/env python
# coding: utf8

"""Example of defining a knowledge base in spaCy

Compatible with: spaCy v3.1.0
Last tested with: v3.1.0
"""
from __future__ import unicode_literals, print_function

import json
import time
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
        "space-groups": JSONReader(nlp),
        "crystal-structure": JSONReader(nlp)
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

    patterns_with_labels = [{'label': name, 'pattern': pattern['pattern']} for pattern in patterns]
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

        entity_ruler_path = output_dir / "el"
        entity_ruler.to_disk(entity_ruler_path)
        print()
        print("Saved entity ruler to", entity_ruler_path)


class BaseReader:

    def __init__(self, nlp):
        self.nlp = nlp
        self.pattern_set = set()


class JSONReader(BaseReader):
    entity_name = "JSON Reader"

    def read_file(self, input_file: Path):
        """Read input file - this is the main method of the class that returns a list of extracted patterns"""
        patterns = []

        data = []
        with open(input_file, 'r') as file:
            data = json.load(file)

        if not data:
            return patterns

        for item in data:
            # text = self.nlp(item)
            items = [item]
            tmp_items = []
            if '_' in item:
                tmp_items.append(item.replace("_", " "))
                tmp_items.append(item.replace("_", ""))

            if '/' in item:
                for tmp_item in tmp_items.copy():
                    tmp_items.append(tmp_item.replace("/", " /"))
                    tmp_items.append(tmp_item.replace("/", " / "))
                    tmp_items.append(tmp_item.replace("/", "/ "))

            items.extend(tmp_items)
            patterns_created = [{"pattern": str(item)} for item in items]
            for pattern_created in patterns_created:
                if 'pattern' in pattern_created and str(pattern_created['pattern']) not in self.pattern_set:
                    patterns.append(pattern_created)
                    self.pattern_set.add(str(pattern_created['pattern']))

        return patterns


if __name__ == "__main__":
    plac.call(main)
