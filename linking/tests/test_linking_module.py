import logging

from linking_module import RuleBasedLinker, CriticalTemperatureClassifier, SpacyPipeline
from test_utils import prepare_doc, get_tokens, get_tokens_and_spans

LOGGER = logging.getLogger(__name__)


class TestSpacyPipeline:
    def test_get_sentence_boundaries(self):
        input = "The relatively high superconducting transition tempera- ture in La 3 Ir 2 Ge 2 is noteworthy. " \
                "Recently, the isostructural compound La 3 Rh 2 Ge 2 was reported to be a superconducting material " \
                "with critical temperature T C = 3.5 K. This value was considered to be the highest in the series of " \
                "several La-based superconducting germanides, such as LaGe 2 , LaPd 2 Ge 2 , LaPt 2 Ge 2 , and " \
                "LaIr 2 Ge 2 ͑see Ref. 21 and refer- ences therein͒. The critical temperature T C = 4.7 K discov- ered " \
                "for La 3 Ir 2 Ge 2 in this work is by about 1.2 K higher than that found for La 3 Rh 2 Ge 2 . It is " \
                "also interesting to note that a Y-based ternary germanide, namely, Y 2 PdGe 3 , crystallized in the " \
                "hexagonal AlB 2 structure, was found to be a type-II su- perconductor with transition temperature " \
                "T C =3 K. The re- sults of band calculations for this system 25,26 reveal that the Y-4d density of " \
                "states dominates the Fermi level, and thus the superconductivity in this compound is believed to " \
                "origi- nate from Y-4d electrons. In the present case of La 3 Ir 2 Ge 2 or La 3 Rh 2 Ge 2 , " \
                "explanation of their superconductivity requires the knowledge of density of La-5d, Ir-5d ͑or Rh-4d͒, " \
                "and Ge- 4p states. Hence band-structure calculations are necessary. "

        spans = []

        words, spaces, spans = get_tokens(input, spans)

        target = RuleBasedLinker()
        boundaries = target.get_sentence_boundaries(words, spaces)

        assert len(boundaries) == 8


class TestRuleBasedLinker:

    def test_linking_pressure(self):
        text = "The LaFe0.2 Sr 0.4 was discovered to be superconducting at 3K applying a pressure of 5Gpa."
        input_spans = [("LaFe0.2 Sr 0.4", "<material>"), ("superconducting", "<tc>"), ("3K", "<tcValue>"),
                       ("5Gpa", "<pressure>")]
        tokens, spans = get_tokens_and_spans(text, input_spans)

        paragraph = {
            "text": text,
            "spans": spans,
            "tokens": tokens
        }

        target = RuleBasedLinker(source="<pressure>", destination="<tcValue>")

        process_paragraph = target.process_paragraph(paragraph)

        print(process_paragraph)


class TestCriticalTemperatureClassifier:
    def test_markCriticalTemperature_simple_1(self):
        input = "The Tc of the BaClE2 is 30K."

        spans = [("Tc", "<tc>"), ("BaClE2", "<material>"), ("30K", "<tcValue>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 1
        assert tcValues[0].text == "30K"

    def test_markCriticalTemperature_simple_2(self):
        input = "The material BaClE2 superconducts at 30K."

        spans = [("BaClE2", "<material>"), ("superconducts", "<tc>"), ("30K", "<tcValue>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 1
        assert tcValues[0].text == "30K"

    def test_markCriticalTemperature_simple_3(self):
        input = "We are explaining some important notions. The material BaClE2 superconducts at 30K. What about going for a beer?"

        spans = [("<tc>", "<tc>"), ("BaClE2", "<material>"), ("30K", "<tcValue>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 1
        assert tcValues[0].text == "30K"

    def test_markCriticalTemperature_simple_4(self):
        input = "The material BaClE2 has Tc at 30K."

        spans = [("BaClE2", "<material>"), ("Tc", "<tc>"), ("30K", "<tcValue>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 1
        assert tcValues[0].text == "30K"

    def test_markCriticalTemperature_1(self):
        input = "We also plot in values of U 0 obtained from flux-creep in a BaFe 2−x Ni x As 2 crystal with " \
                "similar T c for H c-axis at T = 8 K and for H ab-planes at T = 13 K."

        spans = [("BaFe 2−x Ni x As 2 crystal", "<material>"), ("T c", "<tc>"), ("8 K", "<tcValue>"),
                 ("13 K", "<tcValue>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 0

    def test_markCriticalTemperature_2(self):
        input = "(Color online) Effect of electron irradiation on the low-temperature penetration depth ∆λ of two " \
                "samples of BaFe2(As1−xPx)2: (a) Tc0 = 28 K and (b) Tc0 = 29 K."

        spans = [("BaFe2(As1−xPx)2", "<material>"), ("Tc0", "<tc>"), ("28 K", "<tcValue>"), ("Tc0", "<tc>"),
                 ("29 K", "<tcValue>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 2

    def test_markCriticalTemperature_3(self):
        input = "It is also worth noticing that the T C of this structure is slightly lower (about 5 K lower) than " \
                "the T C for the 2×7 superlattice where the two BCO/CCO interfaces are far apart (seven unit " \
                "cells of CCO) and no sizeable intralayer interaction is expected.It is also worth noticing that " \
                "the T C of this structure is slightly lower (about 5 K lower) than the T C for the 2×7 " \
                "superlattice where the two BCO/CCO interfaces are far apart (seven unit cells of CCO) and no " \
                "sizeable intralayer interaction is expected."

        spans = [("BCO/CCO", "<material>"), ("CCO)", "<material>"), ("T C", "<tc>"), ("5 K", "<tcValue>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 0

    # def test_markCriticalTemperature_repulsion_for_Curie_temperature(self):
    #     input = "The corresponding magnetization loop recorded after ZFC to 5 K with the magnetic field " \
    #             "parallel to the a-b plane for a single La 2/3 Ca 1/3 MnO 3−x film of thickness ϳ200 nm on LSAT " \
    #             "is shown in A Curie temperature T C of about 220 K and a magnetic moment ͑T → 0 K͒ Ͼ 2 B per Mn ion " \
    #             "were derived from these curves."
    #
    #     spans = [("5 K", "<tcValue>"), ("La 2/3 Ca 1/3 MnO 3−x film", "<material>"), ("T C", "<tc>"), ("220 K", "<tcValue>"), ]
    #
    #     doc = prepare_doc(input, spans)
    #     doc2 = markCriticalTemperature(doc)
    #
    #     tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<temperature-tc>'], doc2)]
    #
    #     assert len(tcValues) == 0

    def test_markCriticalTemperature_relative_critical_temperature(self):
        input = "The R versus T curves (figure 2(c) for samples B1 and B2 (with 6 wt% Ag) show that the HIP process " \
                "increases T c by 0.8 K and reduces the resistance in the normal state by about 10%."

        spans = [("B1", "<material>"), ("B2 (with 6 wt% Ag)", "<material>"),
                 ("0.8 K", "<tcValue>"), ]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 0

    def test_markCriticalTemperature_relative_critical_temperature_2(self):
        input = "The critical temperature T C = 4.7 K discovered for La 3 Ir 2 Ge 2 in this work is by about 1.2 K " \
                "higher than that found for La 3 Rh 2 Ge 2 ."

        spans = [("critical temperature", "<tc>"), ("T C", "<tc>"), ("4.7 K", "<tcValue>"),
                 ("La 3 Ir 2 Ge 2", "<material>"),
                 ("La 3 Rh 2 Ge 2", "<material>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 1
        assert tcValues[0].text == "4.7 K"

    def test_markCriticalTemperature_relative_critical_temperature_3(self):
        input = "The material BaClE2 has Tc at 30K higher than 77K."

        spans = [("BaClE2", "<material>"), ("<tc>", "<tc>"), ("30K", "<tcValue>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 0

    def test_markCriticalTemperature_respectively_1(self):
        input = "The T C values for YBCO + BSO2%, YBCO + BSO2% + YOA, and YBCO + BSO2% + YOB fi lms are 89.7 K, 86.7 K, and 89.7 K respectively"

        spans = [("T C", "<tc>"),
                 ("YBCO + BSO2%", "<material>"), ("YBCO + BSO2% + YOA", "<material>"),
                 ("YBCO + BSO2% + YOB", "<material>"),
                 ("89.7 K", "<tcValue>"), ("86.7 K", "<tcValue>"), ("89.7 K", "<tcValue>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 3

        assert tcValues[0].text == "89.7 K"
        assert tcValues[1].text == "86.7 K"
        assert tcValues[2].text == "89.7 K"

    ## This test follows the current implementation, where we cannot say whether the Tc at the beginning of the sentence
    ## refers also to the value in the middle (38K)
    def test_markCriticalTemperature_complex_case(self):
        input = "Tc varies from 2.7 K in CsFe2As2 to 38 K in A1−xKxFe2As2 (A = Ba, Sr). Meanwhile, superconductivity " \
                "could also be induced in the parent phase by high pressure or by replacing some of the Fe by Co. " \
                "More excitingly, large single crystals could be obtained by the Sn flux method in this family to " \
                "study the rather low melting temperature and the intermetallic characteristics."

        spans = [("Tc", "<tc>"), ("2.7 K", "<tcValue>"), ("CsFe2As2", "<material>"),
                 ("38 K", "<tcValue>"), ("A1−xKxFe2As2", "<material>")]

        target = CriticalTemperatureClassifier()
        doc = prepare_doc(input, spans)
        doc2 = target.process_doc(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'] and w._.linkable is True, doc2)]

        assert len(tcValues) == 1

        assert tcValues[0].text == "2.7 K"

    def test_mark_temperatures_process(self):
        text = "The LaFe0.2 Sr 0.4 was discovered to be superconducting at 3K applying a pressure of 5Gpa."
        input_spans = [("LaFe0.2 Sr 0.4", "<material>"), ("superconducting", "<tc>"), ("3K", "<tcValue>"),
                       ("5Gpa", "<pressure>")]
        tokens, spans = get_tokens_and_spans(text, input_spans)

        paragraph = {
            "text": text,
            "spans": spans,
            "tokens": tokens
        }

        target = CriticalTemperatureClassifier()

        spans[0]['linkable'] = True
        process_paragraph = target.mark_temperatures_paragraph(paragraph)

        linkable_spans = [span for span in process_paragraph['spans'] if span['linkable'] is True]

        assert len(linkable_spans) == 2
        assert process_paragraph['spans'][0]['linkable'] is True
        assert process_paragraph['spans'][2]['linkable'] is True

class TestUtilitiesMethods:

    def test_covert_to_spacy(self):
        text = 'The measured T c \'s are 30, 37.7, 36, 27.5 and 20.3 K for x = 0.10, 0.15, 0.20, 0.22 and 0.24, re- spectively.'
        tokens = [{'text': 'The', 'offset': 0, 'linkable': False}, {'text': ' ', 'offset': 3, 'linkable': False}, {'text': 'measured', 'offset': 4, 'linkable': False}, {'text': ' ', 'offset': 12, 'linkable': False}, {'text': 'T', 'offset': 13, 'linkable': False}, {'text': ' ', 'offset': 14, 'linkable': False}, {'text': 'c', 'offset': 15, 'linkable': False}, {'text': ' ', 'offset': 16, 'linkable': False}, {'text': "'", 'offset': 17, 'linkable': False}, {'text': 's', 'offset': 18, 'linkable': False}, {'text': ' ', 'offset': 19, 'linkable': False}, {'text': 'are', 'offset': 20, 'linkable': False}, {'text': ' ', 'offset': 23, 'linkable': False}, {'text': '30', 'offset': 24, 'linkable': False}, {'text': ',', 'offset': 26, 'linkable': False}, {'text': ' ', 'offset': 27, 'linkable': False}, {'text': '37', 'offset': 28, 'linkable': False}, {'text': '.', 'offset': 30, 'linkable': False}, {'text': '7', 'offset': 31, 'linkable': False}, {'text': ',', 'offset': 32, 'linkable': False}, {'text': ' ', 'offset': 33, 'linkable': False}, {'text': '36', 'offset': 34, 'linkable': False}, {'text': ',', 'offset': 36, 'linkable': False}, {'text': ' ', 'offset': 37, 'linkable': False}, {'text': '27', 'offset': 38, 'linkable': False}, {'text': '.', 'offset': 40, 'linkable': False}, {'text': '5', 'offset': 41, 'linkable': False}, {'text': ' ', 'offset': 42, 'linkable': False}, {'text': 'and', 'offset': 43, 'linkable': False}, {'text': ' ', 'offset': 46, 'linkable': False}, {'text': '20', 'offset': 47, 'linkable': False}, {'text': '.', 'offset': 49, 'linkable': False}, {'text': '3', 'offset': 50, 'linkable': False}, {'text': ' ', 'offset': 51, 'linkable': False}, {'text': 'K', 'offset': 52, 'linkable': False}, {'text': ' ', 'offset': 53, 'linkable': False}, {'text': 'for', 'offset': 54, 'linkable': False}, {'text': ' ', 'offset': 57, 'linkable': False}, {'text': 'x', 'offset': 58, 'linkable': False}, {'text': ' ', 'offset': 59, 'linkable': False}, {'text': '=', 'offset': 60, 'linkable': False}, {'text': ' ', 'offset': 61, 'linkable': False}, {'text': '0', 'offset': 62, 'linkable': False}, {'text': '.', 'offset': 63, 'linkable': False}, {'text': '10', 'offset': 64, 'linkable': False}, {'text': ',', 'offset': 66, 'linkable': False}, {'text': ' ', 'offset': 67, 'linkable': False}, {'text': '0', 'offset': 68, 'linkable': False}, {'text': '.', 'offset': 69, 'linkable': False}, {'text': '15', 'offset': 70, 'linkable': False}, {'text': ',', 'offset': 72, 'linkable': False}, {'text': ' ', 'offset': 73, 'linkable': False}, {'text': '0', 'offset': 74, 'linkable': False}, {'text': '.', 'offset': 75, 'linkable': False}, {'text': '20', 'offset': 76, 'linkable': False}, {'text': ',', 'offset': 78, 'linkable': False}, {'text': ' ', 'offset': 79, 'linkable': False}, {'text': '0', 'offset': 80, 'linkable': False}, {'text': '.', 'offset': 81, 'linkable': False}, {'text': '22', 'offset': 82, 'linkable': False}, {'text': ' ', 'offset': 84, 'linkable': False}, {'text': 'and', 'offset': 85, 'linkable': False}, {'text': ' ', 'offset': 88, 'linkable': False}, {'text': '0', 'offset': 89, 'linkable': False}, {'text': '.', 'offset': 90, 'linkable': False}, {'text': '24', 'offset': 91, 'linkable': False}, {'text': ',', 'offset': 93, 'linkable': False}, {'text': ' ', 'offset': 94, 'linkable': False}, {'text': 're', 'offset': 95, 'linkable': False}, {'text': '-', 'offset': 97, 'linkable': False}, {'text': ' ', 'offset': 98, 'linkable': False}, {'text': 'spectively', 'offset': 99, 'linkable': False}, {'text': '.', 'offset': 109, 'linkable': False}]
        spans = [{'id': 3183758168641928847, 'text': 'T c ', 'type': '<tc>', 'offset_start': 13, 'offset_end': 17, 'token_start': 1, 'token_end': 2, 'boundingBoxes': [], 'links': [], 'linkable': False}, {'id': 2850964293203602307, 'text': '30', 'type': '<tcValue>', 'offset_start': 24, 'offset_end': 26, 'token_start': 4, 'token_end': 4, 'boundingBoxes': [], 'links': [], 'linkable': False}, {'id': -7289024069834629803, 'text': '37.7', 'type': '<tcValue>', 'offset_start': 28, 'offset_end': 32, 'token_start': 5, 'token_end': 7, 'boundingBoxes': [], 'links': [], 'linkable': False}, {'id': 414589195323464845, 'text': '36', 'type': '<tcValue>', 'offset_start': 34, 'offset_end': 36, 'token_start': 7, 'token_end': 8, 'boundingBoxes': [], 'links': [], 'linkable': False}, {'id': -6841720698725589771, 'text': '27.5 ', 'type': '<tcValue>', 'offset_start': 38, 'offset_end': 43, 'token_start': 9, 'token_end': 11, 'boundingBoxes': [], 'links': [], 'linkable': False}, {'id': -7747294031880326267, 'text': '20.3 ', 'type': '<tcValue>', 'offset_start': 47, 'offset_end': 52, 'token_start': 12, 'token_end': 14, 'boundingBoxes': [], 'links': [], 'linkable': False}, {'id': 'x14', 'text': 'x = 0.10', 'type': '<material>', 'offset_start': 58, 'offset_end': 66, 'token_start': 15, 'token_end': 19, 'boundingBoxes': [], 'links': [], 'linkable': True}, {'id': 'x15', 'text': '0.15', 'type': '<material>', 'offset_start': 68, 'offset_end': 72, 'token_start': 19, 'token_end': 22, 'boundingBoxes': [], 'links': [], 'linkable': True}, {'id': 'x16', 'text': '0.20', 'type': '<material>', 'offset_start': 74, 'offset_end': 78, 'token_start': 22, 'token_end': 24, 'boundingBoxes': [], 'links': [], 'linkable': True}, {'id': 'x17', 'text': '0.22 ', 'type': '<material>', 'offset_start': 80, 'offset_end': 85, 'token_start': 24, 'token_end': 26, 'boundingBoxes': [], 'links': [], 'linkable': True}, {'id': 'x18', 'text': '0.24', 'type': '<material>', 'offset_start': 89, 'offset_end': 93, 'token_start': 26, 'token_end': 29, 'boundingBoxes': [], 'links': [], 'linkable': True}]
        outputTokens, outputSpaces, outputSpans = SpacyPipeline.convert_to_spacy(tokens, spans)

        print("bao")
        for span in outputSpans:
            assert "".join(outputTokens[span['token_start']:span['token_end']]) == span['text']
            assert text[span['offset_start']:span['offset_end']] == span['text']
