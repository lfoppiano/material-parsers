import argparse
import logging
import os
from pathlib import Path

import numpy as np
from gensim.models import LdaModel, EnsembleLda
from gensim.parsing import strip_non_alphanum, strip_punctuation, remove_stopwords, strip_multiple_whitespaces
from gensim.parsing.preprocessing import split_on_space, strip_numeric

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

from gensim.corpora import Dictionary
from nltk.stem.wordnet import WordNetLemmatizer

lemmatizer = WordNetLemmatizer()


def preprocess_text(text):
    non_alphanum = strip_non_alphanum(text)
    alpha_only = strip_numeric(non_alphanum)
    punctuation = strip_punctuation(alpha_only)
    stopwords = remove_stopwords(punctuation)

    return strip_multiple_whitespaces(stopwords)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract keywords with LDA ensemble (Gensim)")

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

    dictionary = Dictionary()
    if recursive:
        for root, dirs, files in os.walk(input):
            for file_ in files:
                if not file_.lower().endswith(".txt"):
                    continue

                abs_path = os.path.join(root, file_)
                input_path_list.append(abs_path)

                output_path = abs_path.replace(str(input), str(output)).replace(".txt", ".json")
                output_path_list.append(output_path)

    else:
        input_path_list = list(Path(input).glob('*.txt'))
        output_path_list = [str(input_path).replace(str(input), str(output)).replace(".txt", ".json") for input_path in
                            input_path_list]

    docs_temp = []
    for idx, path in enumerate(input_path_list):
        with open(path, 'r') as fin:
            doc_as_text = " ".join([line.strip() for line in fin])
            preprocessed_text = preprocess_text(doc_as_text)
            tokenized_text = split_on_space(preprocessed_text)
            docs_temp.append(tokenized_text)

        if idx > 0 and idx % 100000 == 0:
            dictionary.add_documents([[lemmatizer.lemmatize(token) for token in doc_] for doc_ in docs_temp])
            docs_temp = []

    if len(docs_temp) > 0:
        dictionary.add_documents([[lemmatizer.lemmatize(token) for token in doc_] for doc_ in docs_temp])

    dictionary.filter_extremes(no_below=5, no_above=0.5)

    corpus = []
    for idx, path in enumerate(input_path_list):
        with open(path, 'r') as fin:
            doc_as_text = " ".join([line.strip() for line in fin])
            preprocessed_text = preprocess_text(doc_as_text)
            tokenized_text = split_on_space(preprocessed_text)
            document_as_bow = dictionary.doc2bow(tokenized_text)
            corpus.append(document_as_bow)

    topic_model_class = LdaModel

    ensemble_workers = 20
    num_models = ensemble_workers * 2

    distance_workers = ensemble_workers

    num_topics = 99
    passes = int(num_topics / 10 * 2)

    ensemble = EnsembleLda(
        corpus=corpus,
        id2word=dictionary,
        num_topics=num_topics,
        passes=passes,
        num_models=num_models,
        topic_model_class=LdaModel,
        ensemble_workers=ensemble_workers,
        distance_workers=distance_workers
    )

    print(len(ensemble.ttda))
    print(len(ensemble.get_topics()))

    shape = ensemble.asymmetric_distance_matrix.shape
    without_diagonal = ensemble.asymmetric_distance_matrix[~np.eye(shape[0], dtype=bool)].reshape(shape[0], -1)
    print(without_diagonal.min(), without_diagonal.mean(), without_diagonal.max())

    ensemble.recluster(eps=0.09, min_samples=2, min_cores=ensemble_workers)

    print(ensemble.get_topics())
