import logging

from relationships_resolver import SimpleResolutionResolver, VicinityResolutionResolver
from tests.test_utils import prepare_doc

LOGGER = logging.getLogger(__name__)


class TestSimpleResolutionResolver:

    def test_simpleResolution_1(self):
        input = "It is also interesting to note that a Y-based ternary germanide, namely, Y 2 PdGe 3 , " \
                "crystallized in the hexagonal AlB 2 structure, was found to be a type-II superconductor " \
                "with transition temperature T C =3 K."

        spans = [("Y 2 PdGe 3", "material"), ("AlB 2", "material"), ("superconductor", "tc"), ("T C", "tcvalue"),
                 ("3 K", "tcvalue")]
        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]

        relationships = SimpleResolutionResolver().find_relationships(materials, tc_values)

        print(relationships)


class TestVicinityResolutionResolver:

    def test_vicinityResolution_1(self):
        input = "It is also interesting to note that a Y-based ternary germanide, namely, Y 2 PdGe 3 , " \
                "crystallized in the hexagonal AlB 2 structure, was found to be a type-II superconductor " \
                "with transition temperature T C =3 K."

        spans = [("Y 2 PdGe 3", "material"), ("AlB 2", "material"), ("superconductor", "tc"), ("T C", "tcvalue"),
                 ("3 K", "tcvalue")]
        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]

        relationships = SimpleResolutionResolver().find_relationships(materials, tc_values)

        print(relationships)

    def test_vicinityResolution_respectively_1(self):
        input = "In the best cases a transition temperature of 38 K (zero resistance point), 25 K (zero " \
                "resistance point) and 38 K (midpoint) were measured for CCO/STO, CCO/BCO and LSCO/LCO, " \
                "respectively."

        spans = [("38 K", "tcvalue"), ("25 K", "tcvalue"), ("38 K", "tcvalue"),
                 ("CCO/STO", "material"), ("CCO/BCO", "material"), ("LSCO/LCO", "material")]
        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)

        assert len(relationships) == 3
        assert str(relationships[0][0]) == "CCO/STO"
        assert str(relationships[0][1]) == "38 K"

        assert str(relationships[1][0]) == "CCO/BCO"
        assert str(relationships[1][1]) == "25 K"

        assert str(relationships[2][0]) == "LSCO/LCO"
        assert str(relationships[2][1]) == "38 K"

    def test_vicinityResolution_respectively_2(self):
        input = "The critical temperature T C = 4.7 K discovered for La 3 Ir 2 Ge 2 in this work is by about 1.2 K " \
                "higher than that found for La 3 Rh 2 Ge 2 ."

        spans = [("critical temperature", "tc"), ("T C", "tc"), ("4.7 K", "tcvalue"), ("La 3 Ir 2 Ge 2", "material"),
                 ("La 3 Rh 2 Ge 2", "material")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)

        assert len(relationships) == 1
        assert str(relationships[0][0]) == "La 3 Ir 2 Ge 2"
        assert str(relationships[0][1]) == "4.7 K"


    # def test_vicinityResolution_2(self):
    #     input = "The T C of the film differs from bulk YBCO [T C bulk ¼ 90:2 K (Ref. 22)] which is most likely " \
    #             "due to large lattice mismatches between the MgO substrate and the YBCO film, giving rise to slight " \
    #             "stoichiometric and crystalline defects, finite size effects, and residual strain."
    #
    #     spans = [("critical temperature", "tc"), ("T C", "tc"), ("4.7 K", "tcvalue"), ("La 3 Ir 2 Ge 2", "material"),
    #              ("La 3 Rh 2 Ge 2", "material")]
    #
    #     doc = prepare_doc(input, spans)
    #
    #     materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
    #     tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]
    #
    #     relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)
    #
    #     assert len(relationships) == 1
    #     assert str(relationships[0][0]) == "La 3 Ir 2 Ge 2"
    #     assert str(relationships[0][1]) == "4.7 K"
