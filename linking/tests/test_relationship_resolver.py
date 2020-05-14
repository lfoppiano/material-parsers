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

    def test_vicinityResolution_3(self):
        input = "Havinga et al systematically changed n from 3.00 to 4.00 by synthesizing LaTl 3" \
                " (n=3.00, T c =1.6 K), LaPb 3 (n=3.75, T c =4.1 K), and " \
                "ThPb 3 (n=4.00, T c =5.6 K) and the solid solutions " \
                "La (Tl 1−x Pb x ) 3 and (La 1−x Th x )Pb 3 ."

        spans = [("LaTl 3", "material"), ("T c", "tc"), ("1.6 K", "tcvalue"),
                 ("LaPb 3", "material"), ("T c", "tc"), ("4.1 K", "tcvalue"),
                 ("ThPb 3", "material"), ("T c", "tc"), ("5.6 K", "tcvalue"),
                 ("La (Tl 1−x Pb x ) 3", "material"), ("(La 1−x Th x )Pb 3", "material")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)

        assert len(relationships) == 3

    def test_find_closer_to_pivot(self):
        input = "Havinga et al systematically changed n from 3.00 to 4.00 by synthesizing LaTl 3" \
                " (n=3.00, T c =1.6 K), LaPb 3 (n=3.75, T c =4.1 K), and " \
                "ThPb 3 (n=4.00, T c =5.6 K) and the solid solutions " \
                "La (Tl 1−x Pb x ) 3 and (La 1−x Th x )Pb 3 ."

        spans = [("LaTl 3", "material"), ("T c", "tc"), ("1.6 K", "tcvalue"),
                 ("LaPb 3", "material"), ("T c", "tc"), ("4.1 K", "tcvalue"),
                 ("ThPb 3", "material"), ("T c", "tc"), ("5.6 K", "tcvalue"),
                 ("La (Tl 1−x Pb x ) 3", "material"), ("(La 1−x Th x )Pb 3", "material")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]

        target = VicinityResolutionResolver()
        closer_entity = target.find_closer_to_pivot(materials[0], tc_values)

        assert closer_entity != None
        assert closer_entity.text == "1.6 K"

        closer_entity = target.find_closer_to_pivot(materials[1], tc_values)
        assert closer_entity != None
        assert closer_entity.text == "1.6 K"

    def test_find_previous_entity(self):
        input = "Havinga et al systematically changed n from 3.00 to 4.00 by synthesizing LaTl 3" \
                " (n=3.00, T c =1.6 K), LaPb 3 (n=3.75, T c =4.1 K), and " \
                "ThPb 3 (n=4.00, T c =5.6 K) and the solid solutions " \
                "La (Tl 1−x Pb x ) 3 and (La 1−x Th x )Pb 3 ."

        spans = [("LaTl 3", "material"), ("T c", "tc"), ("1.6 K", "tcvalue"),
                 ("LaPb 3", "material"), ("T c", "tc"), ("4.1 K", "tcvalue"),
                 ("ThPb 3", "material"), ("T c", "tc"), ("5.6 K", "tcvalue"),
                 ("La (Tl 1−x Pb x ) 3", "material"), ("(La 1−x Th x )Pb 3", "material")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]

        target = VicinityResolutionResolver()
        previous = target.find_previous_entity(materials[1], tc_values)

        assert previous is not None
        assert previous.text == "1.6 K"

        all_entities = list(filter(lambda w: w.ent_type_ is not "", doc))

        previous = target.find_previous_entity(materials[1], all_entities)

        assert previous is not None
        assert previous.text == "1.6 K"

        previous = target.find_previous_entity(materials[0], all_entities)
        assert previous is None

        previous = target.find_previous_entity(tc_values[0], tc_values, "material")
        assert previous is None

        previous = target.find_previous_entity(tc_values[0], all_entities, "material")
        assert previous != None
        assert previous.text == "LaTl 3"

    def test_find_following_entity(self):
        input = "Havinga et al systematically changed n from 3.00 to 4.00 by synthesizing LaTl 3" \
                " (n=3.00, T c =1.6 K), LaPb 3 (n=3.75, T c =4.1 K), and " \
                "ThPb 3 (n=4.00, T c =5.6 K) and the solid solutions " \
                "La (Tl 1−x Pb x ) 3 and (La 1−x Th x )Pb 3 ."

        spans = [("LaTl 3", "material"), ("T c", "tc"), ("1.6 K", "tcvalue"),
                 ("LaPb 3", "material"), ("T c", "tc"), ("4.1 K", "tcvalue"),
                 ("ThPb 3", "material"), ("T c", "tc"), ("5.6 K", "tcvalue"),
                 ("La (Tl 1−x Pb x ) 3", "material"), ("(La 1−x Th x )Pb 3", "material")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]

        target = VicinityResolutionResolver()
        following = target.find_following_entity(materials[1], tc_values)

        assert following is not None
        assert following.text == "4.1 K"

        all_entities = list(filter(lambda w: w.ent_type_ is not "", doc))

        following = target.find_following_entity(materials[2], all_entities)

        assert following is not None
        assert following.text == "T c"

        following = target.find_following_entity(materials[4], all_entities)
        assert following is None

        following = target.find_following_entity(tc_values[0], tc_values, "material")
        assert following is None

        following = target.find_following_entity(tc_values[2], all_entities, "material")
        assert following is not None
        assert following.text == "La (Tl 1−x Pb x ) 3"


    def test_calculate_distances(self):
        input = "Havinga et al systematically changed n from 3.00 to 4.00 by synthesizing LaTl 3" \
                " (n=3.00, T c =1.6 K), LaPb 3 (n=3.75, T c =4.1 K), and " \
                "ThPb 3 with T c =5.6 K and the solid solutions " \
                "La (Tl 1−x Pb x ) 3 and (La 1−x Th x )Pb 3 ."

        spans = [("LaTl 3", "material"), ("T c", "tc"), ("1.6 K", "tcvalue"),
                 ("LaPb 3", "material"), ("T c", "tc"), ("4.1 K", "tcvalue"),
                 ("ThPb 3", "material"), ("T c", "tc"), ("5.6 K", "tcvalue"),
                 ("La (Tl 1−x Pb x ) 3", "material"), ("(La 1−x Th x )Pb 3", "material")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]

        target = VicinityResolutionResolver()

        distances = target.calculate_distances(materials, tc_values, doc)

        assert len(distances) == 5
        assert distances[materials[0]][tc_values[0]] == 4.0
        assert distances[materials[1]][tc_values[1]] == 4.0


    def test_calculate_distances_2(self):
        input = "Havinga et al systematically changed n from 3.00 to 4.00 by synthesizing LaTl 3. " \
                "T c = 1.6 K is then found in LaPb 3."

        spans = [("LaTl 3", "material"), ("T c", "tc"), ("1.6 K", "tcvalue"),
                 ("LaPb 3", "material")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['material'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['tcvalue'], doc)]

        target = VicinityResolutionResolver()

        distances = target.calculate_distances(materials, tc_values, doc)

        assert len(distances) == 2
        assert distances[materials[0]][tc_values[0]] == 27.0
        assert distances[materials[1]][tc_values[0]] == 23.5