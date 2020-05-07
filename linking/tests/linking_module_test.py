import logging

from grobid_tokenizer import tokenize
from linking_module import markCriticalTemperature, convert_to_spacy, init_doc

LOGGER = logging.getLogger(__name__)


def prepare_input(input, input_spans):
    input_tokens, offsets = tokenize(input)
    tokens = [{"text": input_tokens[idx], "offsetStart": offsets[idx][0], "offsetEnd": offsets[idx][1]} for idx in
              range(0, len(input_tokens))]

    spans = calculate_spans(input, input_spans, tokens=tokens)
    words, spaces, spans = convert_to_spacy(tokens, spans)

    doc = init_doc(words, spaces, spans)

    return doc


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


class TestLinkingModule:
    def test_markCriticalTemperature_1(self):
        input = "We also plot in values of U 0 obtained from flux-creep in a BaFe 2−x Ni x As 2 crystal with " \
                "similar T c for H c-axis at T = 8 K and for H ab-planes at T = 13 K."

        spans = [("BaFe 2−x Ni x As 2 crystal", "material"), ("T c", "tc"), ("8 K", "tcvalue"), ("13 K", "tcvalue")]
        doc = prepare_input(input, spans)

        doc2 = markCriticalTemperature(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature-tc'], doc2)]

        assert len(tcValues) == 0

    def test_markCriticalTemperature_2(self):
        input = "(Color online) Effect of electron irradiation on the low-temperature penetration depth ∆λ of two " \
                "samples of BaFe2(As1−xPx)2: (a) Tc0 = 28 K and (b) Tc0 = 29 K."

        spans = [("BaFe2(As1−xPx)2", "material"), ("Tc0", "tc"), ("28 K", "tcvalue"), ("Tc0", "tc"),
                 ("29 K", "tcvalue")]

        doc = prepare_input(input, spans)
        doc2 = markCriticalTemperature(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature-tc'], doc2)]

        assert len(tcValues) == 2

    def test_markCriticalTemperature_3(self):
        input = "It is also worth noticing that the T C of this structure is slightly lower (about 5 K lower) than " \
                "the T C for the 2×7 superlattice where the two BCO/CCO interfaces are far apart (seven unit " \
                "cells of CCO) and no sizeable intralayer interaction is expected.It is also worth noticing that " \
                "the T C of this structure is slightly lower (about 5 K lower) than the T C for the 2×7 " \
                "superlattice where the two BCO/CCO interfaces are far apart (seven unit cells of CCO) and no " \
                "sizeable intralayer interaction is expected."

        spans = [("BCO/CCO", "material"), ("CCO)", "material"), ("T C", "tc"), ("5 K", "tcvalue")]

        doc = prepare_input(input, spans)
        doc2 = markCriticalTemperature(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature-tc'], doc2)]

        assert len(tcValues) == 0

    def test_markCriticalTemperature_repulsion_for_Curie_temperature(self):
        input = "The corresponding magnetization loop recorded after ZFC to 5 K with the magnetic field " \
                "parallel to the a-b plane for a single La 2/3 Ca 1/3 MnO 3−x film of thickness ϳ200 nm on LSAT " \
                "is shown in A Curie temperature T C of about 220 K and a magnetic moment ͑T → 0 K͒ Ͼ 2 B per Mn ion " \
                "were derived from these curves."

        spans = [("5 K", "tcvalue"), ("La 2/3 Ca 1/3 MnO 3−x film", "material"), ("T C", "tc"), ("220 K", "tcvalue"), ]

        doc = prepare_input(input, spans)
        doc2 = markCriticalTemperature(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature-tc'], doc2)]

        assert len(tcValues) == 0