import argparse
import gzip
import json
import ntpath
import os
import traceback

# For converting the S2ORC

def process_content(json_data):
    sections = []
    for abstract in json_data["abstract"] if "abstract" in json_data else []:
        if "text" in abstract:
            paragraph = str.strip(abstract['text'])
            if len(paragraph) <= 2:
                continue

            if 'sentence_spans' in abstract:
                for sentence in abstract['sentence_spans'] if 'sentence_spans' in abstract else []:
                    sections.append(paragraph[sentence['start']:sentence['end']])
            else:
                sections.append(paragraph)

    for text_part in json_data["body_text"] if "body_text" in json_data else []:
        if 'text' in text_part:
            paragraph = str.strip(text_part['text'])
            if len(paragraph) <= 2:
                continue

            if 'sentence_spans' in text_part:
                for sentence in text_part['sentence_spans'] if 'sentence_spans' in text_part else []:
                    sections.append(paragraph[sentence['start']:paragraph['end']])
            else:
                sections.append(paragraph)

    return sections


def process_input_file(input_path, output_path, input_file_type):
    output_file = input_path.replace(input_file_type, ".txt")
    if output_path is not None:
        # output_path_dir_container = os.path.join(output_path, Path(input_path).stem)
        # if not os.path.exists(output_path_dir_container):
        #     os.makedirs(output_path_dir_container)

        output_file = os.path.join(output_path, ntpath.basename(input_path).replace(input_file_type, ".txt"))

    documents = []
    try:
        if gz:
            with gzip.open(input_path, mode="rt") as fp:
                for line in fp.readlines():
                    json_content = json.loads(line)
                    sections = process_content(json_content)
                    documents.append(sections)
        else:
            with open(input_path, 'r') as fp:
                for line in fp.readlines():
                    json_content = json.loads(line)
                    sections = process_content(json_content)
                    documents.append(sections)
    except Exception as e:
        print("Something went wrong. Skipping " + str(input_path) + ". ", e)
        traceback.print_exc()
        return

    with open(output_file, 'w') as outfile:
        for document in documents:
            doc = False
            for text in document:
                # text_ = text.replace('\n', '__BR__').replace('\t', '__TAB__')
                outfile.write(text)
                outfile.write('\n')
                doc = True

            if doc:
                outfile.write('\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract text from JSONL lossy files.")
    parser.add_argument("--json-repo", type=str, required=True,
                        help="path to the directory of JSONL files")
    parser.add_argument("--output", type=str,
                        help="path to an output directory where to write output. If not specified the file will be "
                             "written in the same directory as the input is taken.")
    parser.add_argument("--gz", help="read from GZ compressed files", action="store_true", default=False)

    args = parser.parse_args()
    json_repo = args.json_repo
    output_path = args.output
    gz = args.gz

    if not os.path.isdir(json_repo):
        print("the path to the JSON files is not valid: ", json_repo)
        exit(-1)
    else:
        input_extension = ".gz" if gz else ".jsonl"

        for root, dirs, files in os.walk(json_repo):
            for file_ in files:
                if not file_.lower().endswith(input_extension):
                    continue

                input_path = os.path.join(root, file_)
                process_input_file(input_path, output_path, input_extension)
