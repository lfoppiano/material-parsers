from pathlib import Path
from keybert import KeyBERT
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract keywords")

    parser.add_argument("--input", help="Input file or directory", required=True)
    parser.add_argument("--output", default=None,
                        help="Output directory")
    parser.add_argument("--recursive", action="store_true", default=False,
                        help="Process input directory recursively. If input is a file, this parameter is ignored. ")

    args = parser.parse_args()

    input = args.input
    output = args.output
    recursive = args.recursive

    input_path_list = []
    output_path_list = []

    if recursive:   
        for root, dirs, files in os.walk(input):
            for dir in dirs:
                abs_path_dir = os.path.join(root, dir)
                output_path = abs_path_dir.replace(str(input), str(output))
                if not os.path.exists(output_path):
                    os.makedirs(output_path)

                for file_ in files:
                    if not file_.lower().endswith(".txt"):
                        continue

                    abs_path = os.path.join(root, file_)
                    input_path_list.append(abs_path)
                    output_path_list.append(os.path.join(output_path, file_))

    else:
        input_path_list = list(Path(input).glob('*.txt'))
        output_path_list = [str(input_path).replace(str(input), str(output)) for input_path in
                            input_path_list]

    kw_model = KeyBERT()
    
    for idx, path in enumerate(input_path_list):
        print("Processing: ", path)
        with open(path, 'r') as fin:
            doc_as_text = " ".join([line.strip() for line in fin])
            keywords = kw_model.extract_keywords(doc_as_text, keyphrase_ngram_range=(1, 1), stop_words=[], use_mmr=False, use_maxsum=False, nr_candidates=20, top_n=5)

            with open(output_path_list[idx], 'w') as fp:
                for keyword in keywords:
                    fp.write(keyword + "\n")
