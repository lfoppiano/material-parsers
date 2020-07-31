import logging

from linking_evaluation import compute_metrics, compute_metrics_by_type, get_report
from linking_module import MATERIAL_TC_TYPE, TC_PRESSURE_TYPE

LOGGER = logging.getLogger(__name__)


class TestLinkingModule:
    def test_compute_metrics(self):
        link_predicted = [(1, 2, MATERIAL_TC_TYPE), (3, 4, MATERIAL_TC_TYPE), (6, 7, MATERIAL_TC_TYPE)]
        link_expected = [(2, 1, MATERIAL_TC_TYPE), (3, 4, TC_PRESSURE_TYPE), (6, 7, MATERIAL_TC_TYPE)]

        output = compute_metrics_by_type(link_expected, link_predicted, MATERIAL_TC_TYPE)

        assert output['precision'] == 0.6666666666666666
        assert output['recall'] == 1.0
        assert output['f1'] == 0.8
