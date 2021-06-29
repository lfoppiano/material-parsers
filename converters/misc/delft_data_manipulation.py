import argparse
import os
import sys
from pathlib import Path

import spacy


def extract_log(log_file):
    paragraphs = []
    accumulator = []
    paragraph = {}

    with open(log_file, 'r') as file:
        for line in file:
            line = line.strip('\n')
            if len(line) == 0:
                if len(accumulator) > 0:
                    words = [a[0] + "" for a in accumulator]
                    # text = ''.join(
                    #     [words[i] + (' ' if words[i] not in delimiters else '') for i in range(0, len(words))])
                    text = " ".join(words)
                    paragraph['text'] = text.strip()
                    paragraph['data'] = accumulator
                    paragraphs.append(paragraph)

                    accumulator = []
                    paragraph = {}
            else:
                splits = line.split(' ')
                splits[len(splits) - 1].replace("\n", "")
                accumulator.append(splits)

    return paragraphs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Delft data manipulation")

    parser.add_argument("--input", help="Input file", required=True, type=Path)
    parser.add_argument("--output", help="Output directory", required=False, default=None, type=Path)
    parser.add_argument("--action", choices=["replace-other-with-pos", "change-tokenization"], required=False,
                        default="replace-other-with-pos")

    args = parser.parse_args()
    input_file = args.input
    output_dir = args.output

    if not os.path.exists(input_file):
        print("The file", input_file, "does not exists. Exiting.")
        sys.exit(-1)

    if not os.path.isfile(str(input_file)):
        print("The file", input_file, "does is not a file. Exiting.")
        sys.exit(-1)

    paragraphs = extract_log(input_file)

    nlp = spacy.load("en_core_sci_lg")

    for paragraph in paragraphs:
        text = paragraph['text']
        doc = nlp(text)

        pos = [token.pos_ for token in doc]
        if len(paragraph['data']) != len(pos):
            print("Tokens:", len(paragraph['data']), "POS: ", len(pos))

        first = True
        for idx in range(0, len(paragraph['data'])):
            if first:
                new_pos = "I-<" + pos[idx] + ">"
                first = False
            else:
                if pos[idx] != pos[idx-1]:
                    new_pos = "I-<" + pos[idx] + ">"
                else:
                    new_pos = "<" + pos[idx] + ">"
            # print(paragraph['data'][idx][0], "-> ", doc[idx])

            if paragraph['data'][idx][-1] == "<other>":
                paragraph['data'][idx][-1] = new_pos

    with open(os.path.join(output_dir, input_file.stem + ".pos.out"), 'w') as fw:
        for paragraph in paragraphs:
            for line in paragraph['data']:
                fw.write(" ".join(line))
                fw.write("\n")
            fw.write("\n\n")
            fw.flush()
