import logging

from  material_parsers.linking.relationships_resolver import SimpleResolutionResolver, \
    VicinityResolutionResolver
from tests.utils import prepare_doc

LOGGER = logging.getLogger(__name__)


class TestSimpleResolutionResolver:

    def test_simpleResolution_1(self):
        input = "It is also interesting to note that a Y-based ternary germanide, namely, Y 2 PdGe 3 , " \
                "crystallized in the hexagonal AlB 2 structure, was found to be a type-II superconductor " \
                "with transition temperature T C =3 K."

        spans = [("Y 2 PdGe 3", "<material>"), ("AlB 2", "<material>"), ("superconductor", "<tc>"),
                 ("T C", "<tcValue>"),
                 ("3 K", "<tcValue>")]
        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = SimpleResolutionResolver().find_relationships(materials, tc_values)

        print(relationships)


class TestVicinityResolutionResolver:

    def test_vicinityResolution_1(self):
        input = "It is also interesting to note that a Y-based ternary germanide, namely, Y 2 PdGe 3 , " \
                "crystallized in the hexagonal AlB 2 structure, was found to be a type-II superconductor " \
                "with transition temperature T C =3 K."

        spans = [("Y 2 PdGe 3", "<material>"), ("AlB 2", "<material>"), ("superconductor", "<tc>"),
                 ("T C", "<tcValue>"),
                 ("3 K", "<tcValue>")]
        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = SimpleResolutionResolver().find_relationships(materials, tc_values)

        print(relationships)

    def test_vicinityResolution_respectively_1(self):
        input = "In the best cases a transition temperature of 38 K (zero resistance point), 25 K (zero " \
                "resistance point) and 38 K (midpoint) were measured for CCO/STO, CCO/BCO and LSCO/LCO, " \
                "respectively."

        spans = [("38 K", "<tcValue>"), ("25 K", "<tcValue>"), ("38 K", "<tcValue>"),
                 ("CCO/STO", "<material>"), ("CCO/BCO", "<material>"), ("LSCO/LCO", "<material>")]
        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

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

        spans = [("critical temperature", "<tc>"), ("T C", "<tc>"), ("4.7 K", "<tcValue>"),
                 ("La 3 Ir 2 Ge 2", "<material>"),
                 ("La 3 Rh 2 Ge 2", "<material>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)

        assert len(relationships) == 1
        assert str(relationships[0][0]) == "La 3 Ir 2 Ge 2"
        assert str(relationships[0][1]) == "4.7 K"

    def test_vicinityResolution_respectively_3(self):
        input = "Ba 1−x K x BiO 3−δ (BKBO) and BaPb 1−x Bi x O 3−δ (BPBO) are two such compounds that show T c 's " \
                "of 30 K [1] and 13 K [2], respectively, with carrier concentrations as low as 2×10 " \
                "21 cm −3 ."

        spans = [("Ba 1−x K x BiO 3−δ (BKBO)", "<material>"), ("BaPb 1−x Bi x O 3−δ (BPBO)", "<material>"),
                 ("T c", "<tc>"), ("30 K", "<tcValue>"), ("13 K", "<tcValue>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)
        assert len(relationships) == 2

        assert str(relationships[0][0]) == "Ba 1−x K x BiO 3−δ (BKBO)"
        assert str(relationships[0][1]) == "30 K"

        assert str(relationships[1][0]) == "BaPb 1−x Bi x O 3−δ (BPBO)"
        assert str(relationships[1][1]) == "13 K"

    def test_vicinityResolution_respectively_4(self):
        input = "In this paper, we look at the Bi-based materials that have the chemical formula " \
                "Bi 2 Sr 2 Ca n-1 Cu n O 2n+4 (BiSCCO) where n=1, 2, 3 gives the first three members of this " \
                "class: Bi 2 Sr 2 CuO 6 , Bi 2 Sr 2 CaCu 2 O 8 and Bi 2 Sr 2 Ca 2 Cu 3 O 10 , with critical " \
                "temperatures ( ) T c of 20 K, 85 K and 110 K respectively."

        spans = [("Bi 2 Sr 2 Ca n-1 Cu n O 2n+4 (BiSCCO)", "<material>"),
                 ("Bi 2 Sr 2 CuO 6", "<material>"), ("Bi 2 Sr 2 CaCu 2 O 8", "<material>"),
                 ("Bi 2 Sr 2 Ca 2 Cu 3 O 10", "<material>"),
                 ("T c", "<tc>"), ("20 K", "<tcValue>"), ("85 K", "<tcValue>"), ("110 K", "<tcValue>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)
        assert len(relationships) == 3

        assert str(relationships[0][0]) == "Bi 2 Sr 2 CuO 6"
        assert str(relationships[0][1]) == "20 K"

        assert str(relationships[1][0]) == "Bi 2 Sr 2 CaCu 2 O 8"
        assert str(relationships[1][1]) == "85 K"

        assert str(relationships[2][0]) == "Bi 2 Sr 2 Ca 2 Cu 3 O 10"
        assert str(relationships[2][1]) == "110 K"

    # def test_vicinityResolution_2(self):
    #     input = "The T C of the film differs from bulk YBCO [T C bulk ¼ 90:2 K (Ref. 22)] which is most likely " \
    #             "due to large lattice mismatches between the MgO substrate and the YBCO film, giving rise to slight " \
    #             "stoichiometric and crystalline defects, finite size effects, and residual strain."
    #
    #     spans = [("critical temperature", "<tc>"), ("T C", "<tc>"), ("4.7 K", "<tcValue>"), ("La 3 Ir 2 Ge 2", "<material>"),
    #              ("La 3 Rh 2 Ge 2", "<material>")]
    #
    #     doc = prepare_doc(input, spans)
    #
    #     materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
    #     tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]
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

        spans = [("LaTl 3", "<material>"), ("T c", "<tc>"), ("1.6 K", "<tcValue>"),
                 ("LaPb 3", "<material>"), ("T c", "<tc>"), ("4.1 K", "<tcValue>"),
                 ("ThPb 3", "<material>"), ("T c", "<tc>"), ("5.6 K", "<tcValue>"),
                 ("La (Tl 1−x Pb x ) 3", "<material>"), ("(La 1−x Th x )Pb 3", "<material>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)

        assert len(relationships) == 3

    ## Unfortunately this test passes and the result is correct, but the algorithm got it by chance.
    ## The penalisation due to a comma, after MnSi is applied wrongly -- but I don't know what else to do there...
    def test_vicinityResolution_4(self):
        input = "The investigated MnSi films are in a thickness regime where the magnetic transition " \
                "temperature T c assumes a thickness-independent enhanced value of 43 K as compared with " \
                "that of bulk MnSi, where T c ≈ 29 K. A detailed refinement of the EXAFS data reveals that " \
                "the Mn positions are unchanged, whereas the Si positions vary along the out-of-plane " \
                "direction, alternating in orientation from unit cell to unit cell."

        spans = [("MnSi films", "<material>"), ("T c", "<tc>"), ("43 K", "<tcValue>"),
                 ("MnSi", "<material>"), ("T c", "<tc>"), ("29 K", "<tcValue>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)

        assert len(relationships) == 2

        assert str(relationships[0][0]) == "MnSi films"
        assert str(relationships[0][1]) == "43 K"

        assert str(relationships[1][0]) == "MnSi"
        assert str(relationships[1][1]) == "29 K"

    def test_vicinityResolution_5(self):
        input = "In fact, apart from the very recent discovery of the occurrence of a superconducting " \
                "phase at 200 K in sulfur hydride systems under ultrahigh pressures (up to 150 GPa) , " \
                "the highest T c materials found up until now can be grouped into two families: the " \
                "cuprates, with T c of up to 164 K [5] (in HgBa 2 Ca 2 Cu 3 O 9 at 30 GPa), and " \
                "Fe-pnictides and -chalcogenides (FPC) with T c of up to 55 K [6]."

        spans = [("200 K", "<tcValue>"), ("sulfur hydride", "<material>"), ("highest T c", "<tc>"),
                 ("cuprates", "<class>"), ("T c", "<tc>"), ("up to 164 K", "<tcValue>"),
                 ("HgBa 2 Ca 2 Cu 3 O 9", "<material>"), ("Fe-pnictides and -chalcogenides", "<class>"),
                 ("T c", "<tc>"), ("up to 55 K", "<tcValue>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)

        assert len(relationships) == 2
        assert str(relationships[0][0]) == "sulfur hydride"
        assert str(relationships[0][1]) == "200 K"

        assert str(relationships[1][0]) == "HgBa 2 Ca 2 Cu 3 O 9"
        assert str(relationships[1][1]) == "up to 164 K"

    def test_vicinityResolution_6(self):
        input = "Superconductivity has been discovered in metal diborides like MgB 2 (T c =39 K ), (Mo 0.96 Zr 0.04 ) " \
                "0.85 B 2 (T c =8.2 K ), NbB 2 (T c =5.2 K [3]) and various other ternary borides ."

        spans = [("MgB 2", "<material>"), ("T c", "<tc>"), ("39 K", "<tcValue>"),
                 ("(Mo 0.96 Zr 0.04 ) 0.85 B 2", "<material>"), ("T c", "<tc>"), ("8.2 K", "<tcValue>"),
                 ("NbB 2", "<material>"), ("T c", "<tc>"), ("5.2 K", "<tcValue>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)
        assert len(relationships) == 3

        assert str(relationships[0][0]) == "MgB 2"
        assert str(relationships[0][1]) == "39 K"

        assert str(relationships[1][0]) == "(Mo 0.96 Zr 0.04 ) 0.85 B 2"
        assert str(relationships[1][1]) == "8.2 K"

        assert str(relationships[2][0]) == "NbB 2"
        assert str(relationships[2][1]) == "5.2 K"

    # def test_vicinityResolution_7(self):
    #     input = "Tc varies from 2.7 K in CsFe2As2 to 38 K in A1−xKxFe2As2 (A = Ba, Sr). Meanwhile, superconductivity " \
    #             "could also be induced in the parent phase by high pressure or by replacing some of the Fe by Co. " \
    #             "More excitingly, large single crystals could be obtained by the Sn flux method in this family to " \
    #             "study the rather low melting temperature and the intermetallic characteristics."
    #
    #     spans = [("Tc", "<tc>"), ("2.7 K", "<tcValue>"), ("CsFe2As2", "<material>")]
    #
    #     doc = prepare_doc(input, spans)
    #
    #     materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
    #     tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]
    #
    #     relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)
    #     assert len(relationships) == 2
    #
    #     assert str(relationships[0][0]) == "CsFe2As2"
    #     assert str(relationships[0][1]) == "2.7 K"

    def test_vicinityResolution_missingOneEntity_1(self):
        input = "Superconductivity has been discovered in metal diborides like MgB 2 (T c =39 K ), (Mo 0.96 Zr 0.04 ) " \
                "0.85 B 2 (T c =8.2 K ), NbB 2 (T c =5.2 K [3]) and various other ternary borides ."

        spans = [("MgB 2", "<material>"), ("T c", "<tc>"),
                 ("(Mo 0.96 Zr 0.04 ) 0.85 B 2", "<material>"), ("T c", "<tc>"), ("8.2 K", "<tcValue>"),
                 ("NbB 2", "<material>"), ("T c", "<tc>"), ("5.2 K", "<tcValue>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)
        assert len(relationships) == 2

        assert str(relationships[0][0]) == "(Mo 0.96 Zr 0.04 ) 0.85 B 2"
        assert str(relationships[0][1]) == "8.2 K"

        assert str(relationships[1][0]) == "NbB 2"
        assert str(relationships[1][1]) == "5.2 K"

    ## This test simulate that one of the entities is not extracted, unfortunately the result is wrong, but
    ## there is not really way around it...
    def test_vicinityResolution_respectively_missingEntities_1(self):
        input = "Ba 1−x K x BiO 3−δ (BKBO) and BaPb 1−x Bi x O 3−δ (BPBO) are two such compounds that show T c 's " \
                "of 30 K [1] and 13 K [2], respectively, with carrier concentrations as low as 2×10 " \
                "21 cm −3 ."

        spans = [("BaPb 1−x Bi x O 3−δ (BPBO)", "<material>"),
                 ("T c", "<tc>"), ("30 K", "<tcValue>"), ("13 K", "<tcValue>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        relationships = VicinityResolutionResolver().find_relationships(doc, materials, tc_values)
        assert len(relationships) == 1

        assert str(relationships[0][0]) == "BaPb 1−x Bi x O 3−δ (BPBO)"
        assert str(relationships[0][1]) == "30 K"

    def test_find_closer_to_pivot(self):
        input = "Havinga et al systematically changed n from 3.00 to 4.00 by synthesizing LaTl 3" \
                " (n=3.00, T c =1.6 K), LaPb 3 (n=3.75, T c =4.1 K), and " \
                "ThPb 3 (n=4.00, T c =5.6 K) and the solid solutions " \
                "La (Tl 1−x Pb x ) 3 and (La 1−x Th x )Pb 3 ."

        spans = [("LaTl 3", "<material>"), ("T c", "<tc>"), ("1.6 K", "<tcValue>"),
                 ("LaPb 3", "<material>"), ("T c", "<tc>"), ("4.1 K", "<tcValue>"),
                 ("ThPb 3", "<material>"), ("T c", "<tc>"), ("5.6 K", "<tcValue>"),
                 ("La (Tl 1−x Pb x ) 3", "<material>"), ("(La 1−x Th x )Pb 3", "<material>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

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

        spans = [("LaTl 3", "<material>"), ("T c", "<tc>"), ("1.6 K", "<tcValue>"),
                 ("LaPb 3", "<material>"), ("T c", "<tc>"), ("4.1 K", "<tcValue>"),
                 ("ThPb 3", "<material>"), ("T c", "<tc>"), ("5.6 K", "<tcValue>"),
                 ("La (Tl 1−x Pb x ) 3", "<material>"), ("(La 1−x Th x )Pb 3", "<material>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        target = VicinityResolutionResolver()
        previous = target.find_previous_entity(materials[1], tc_values)

        assert previous is not None
        assert previous.text == "1.6 K"

        all_entities = list(filter(lambda w: w.ent_type_ != "", doc))

        previous = target.find_previous_entity(materials[1], all_entities)

        assert previous is not None
        assert previous.text == "1.6 K"

        previous = target.find_previous_entity(materials[0], all_entities)
        assert previous is None

        previous = target.find_previous_entity(tc_values[0], tc_values, "<material>")
        assert previous is None

        previous = target.find_previous_entity(tc_values[0], all_entities, "<material>")
        assert previous != None
        assert previous.text == "LaTl 3"

    def test_find_following_entity(self):
        input = "Havinga et al systematically changed n from 3.00 to 4.00 by synthesizing LaTl 3" \
                " (n=3.00, T c =1.6 K), LaPb 3 (n=3.75, T c =4.1 K), and " \
                "ThPb 3 (n=4.00, T c =5.6 K) and the solid solutions " \
                "La (Tl 1−x Pb x ) 3 and (La 1−x Th x )Pb 3 ."

        spans = [("LaTl 3", "<material>"), ("T c", "<tc>"), ("1.6 K", "<tcValue>"),
                 ("LaPb 3", "<material>"), ("T c", "<tc>"), ("4.1 K", "<tcValue>"),
                 ("ThPb 3", "<material>"), ("T c", "<tc>"), ("5.6 K", "<tcValue>"),
                 ("La (Tl 1−x Pb x ) 3", "<material>"), ("(La 1−x Th x )Pb 3", "<material>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        target = VicinityResolutionResolver()
        following = target.find_following_entity(materials[1], tc_values)

        assert following is not None
        assert following.text == "4.1 K"

        all_entities = list(filter(lambda w: w.ent_type_ != "", doc))

        following = target.find_following_entity(materials[2], all_entities)

        assert following is not None
        assert following.text == "T c"

        following = target.find_following_entity(materials[4], all_entities)
        assert following is None

        following = target.find_following_entity(tc_values[0], tc_values, "<material>")
        assert following is None

        following = target.find_following_entity(tc_values[2], all_entities, "<material>")
        assert following is not None
        assert following.text == "La (Tl 1−x Pb x ) 3"

    def test_calculate_distances(self):
        input = "Havinga et al systematically changed n from 3.00 to 4.00 by synthesizing LaTl 3" \
                " (n=3.00, T c =1.6 K), LaPb 3 (n=3.75, T c =4.1 K), and " \
                "ThPb 3 with T c =5.6 K and the solid solutions " \
                "La (Tl 1−x Pb x ) 3 and (La 1−x Th x )Pb 3 ."

        spans = [("LaTl 3", "<material>"), ("T c", "<tc>"), ("1.6 K", "<tcValue>"),
                 ("LaPb 3", "<material>"), ("T c", "<tc>"), ("4.1 K", "<tcValue>"),
                 ("ThPb 3", "<material>"), ("T c", "<tc>"), ("5.6 K", "<tcValue>"),
                 ("La (Tl 1−x Pb x ) 3", "<material>"), ("(La 1−x Th x )Pb 3", "<material>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        target = VicinityResolutionResolver()

        distances = target.calculate_distances(materials, tc_values, doc)

        assert len(distances) == 5
        assert distances[materials[0]][tc_values[0]] == 7.5
        assert distances[materials[1]][tc_values[1]] == 7.5
        assert distances[materials[2]][tc_values[2]] == 18

    def test_calculate_distances_2(self):
        input = "Havinga et al systematically changed n from 3.00 to 4.00 by synthesizing LaTl 3. " \
                "T c = 1.6 K is then found in LaPb 3."

        spans = [("LaTl 3", "<material>"), ("T c", "<tc>"), ("1.6 K", "<tcValue>"),
                 ("LaPb 3", "<material>")]

        doc = prepare_doc(input, spans)

        materials = [entity for entity in filter(lambda w: w.ent_type_ in ['<material>'], doc)]
        tc_values = [entity for entity in filter(lambda w: w.ent_type_ in ['<tcValue>'], doc)]

        target = VicinityResolutionResolver()

        distances = target.calculate_distances(materials, tc_values, doc)

        assert len(distances) == 2
        assert distances[materials[0]][tc_values[0]] == 27.0
        assert distances[materials[1]][tc_values[0]] == 23.5
