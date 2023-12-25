import logging

from material_parsers.linking.linking_evaluation import compute_metrics_by_type, tokenize_chunk
from material_parsers.linking.linking_module import RuleBasedLinker

LOGGER = logging.getLogger(__name__)


class TestLinkingModule:
    def test_compute_metrics(self):
        link_predicted = [
            (1, 2, RuleBasedLinker.MATERIAL_TC_TYPE),
            (3, 4, RuleBasedLinker.MATERIAL_TC_TYPE),
            (6, 7, RuleBasedLinker.MATERIAL_TC_TYPE)]

        link_expected = [
            (2, 1, RuleBasedLinker.MATERIAL_TC_TYPE),
            (3, 4, RuleBasedLinker.TC_PRESSURE_TYPE),
            (6, 7, RuleBasedLinker.MATERIAL_TC_TYPE)]

        output = compute_metrics_by_type(link_expected, link_predicted, RuleBasedLinker.MATERIAL_TC_TYPE)

        assert output['precision'] == 0.6666666666666666
        assert output['recall'] == 1.0
        assert output['f1'] == 0.8

    def test_tokenize_chunk(self):
        text = "This is a text I want to tokenize."
        offset = 0
        tokenized_chunks, new_offset = tokenize_chunk(text, offset)

        assert len(tokenized_chunks) == 16
        assert tokenized_chunks[2]['offset'] == 5
