import logging

from  material_parsers.material_parser.material2class import Material2Class

LOGGER = logging.getLogger(__name__)


class TestMaterial2Class:
    def test_1(self):
        clazz = Material2Class().get_class("LaFeO2")

        assert clazz == "Other oxides"

    def test_2(self):
        clazz = Material2Class().get_class("CuFrO2")

        assert clazz == "Cuprate"

    def test_3(self):
        clazz = Material2Class().get_class("CO2")

        assert clazz == "Carbides"

    def test_4(self):
        clazz = Material2Class().get_class("Te2U1")
        assert clazz == "Chalcogenides"
