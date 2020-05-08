import logging
from functools import wraps

from grobid_tokenizer import tokenize
from linking_module import convert_to_spacy, init_doc

# derived from https://github.com/elifesciences/sciencebeam-trainer-delft/tree/develop/tests

LOGGER = logging.getLogger(__name__)


def log_on_exception(f: callable) -> callable:
    """
    Wraps function to log error on exception.
    That is useful for tests that log a lot of things,
    and pytest displaying the test failure at the top of the method.
    (there doesn't seem to be an option to change that)
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.exception('failed due to %s', repr(e))
            raise

    return wrapper


def prepare_doc(input, input_spans):
    words, spaces, spans = get_tokens(input, input_spans)

    doc = init_doc(words, spaces, spans)

    return doc


def get_tokens(input, input_spans):
    input_tokens, offsets = tokenize(input)
    tokens = [{"text": input_tokens[idx], "offsetStart": offsets[idx][0], "offsetEnd": offsets[idx][1]} for idx in
              range(0, len(input_tokens))]
    spans = calculate_spans(input, input_spans, tokens=tokens)

    words, spaces, spans = convert_to_spacy(tokens, spans)

    return words, spaces, spans


def calculate_spans(input, spans, tokens=None):
    calculated_spans = []

    last_span_offset = 0
    for index, span in enumerate(spans):
        if span[0] in input:
            span_start_offset = input.index(span[0], last_span_offset)
            span_end_offset = span_start_offset + len(span[0])
            calculated_span = {
                "id": index,
                "text": input[span_start_offset:span_end_offset],
                "offsetStart": span_start_offset,
                "offsetEnd": span_end_offset,
                "type": span[1],
                "boundingBoxes": [],
                "formattedText": ""
            }
            last_span_offset = span_end_offset
            if tokens is not None:
                indexes = [index for index, token in enumerate(tokens) if
                           token['offsetStart'] >= calculated_span['offsetStart'] and token['offsetEnd'] <=
                           calculated_span['offsetEnd']]

            calculated_span['tokenStart'] = indexes[0]
            calculated_span['tokenEnd'] = indexes[-1] + 1
            calculated_spans.append(calculated_span)

    return calculated_spans
