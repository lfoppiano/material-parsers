import logging

from linking_module import markCriticalTemperature, get_sentence_boundaries_pysbd
from tests.test_utils import prepare_doc, get_tokens

LOGGER = logging.getLogger(__name__)


class TestLinkingModule:
    def test_markCriticalTemperature_1(self):
        input = "We also plot in values of U 0 obtained from flux-creep in a BaFe 2−x Ni x As 2 crystal with " \
                "similar T c for H c-axis at T = 8 K and for H ab-planes at T = 13 K."

        spans = [("BaFe 2−x Ni x As 2 crystal", "material"), ("T c", "tc"), ("8 K", "tcvalue"), ("13 K", "tcvalue")]
        doc = prepare_doc(input, spans)

        doc2 = markCriticalTemperature(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature-tc'], doc2)]

        assert len(tcValues) == 0

    def test_markCriticalTemperature_2(self):
        input = "(Color online) Effect of electron irradiation on the low-temperature penetration depth ∆λ of two " \
                "samples of BaFe2(As1−xPx)2: (a) Tc0 = 28 K and (b) Tc0 = 29 K."

        spans = [("BaFe2(As1−xPx)2", "material"), ("Tc0", "tc"), ("28 K", "tcvalue"), ("Tc0", "tc"),
                 ("29 K", "tcvalue")]

        doc = prepare_doc(input, spans)
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

        doc = prepare_doc(input, spans)
        doc2 = markCriticalTemperature(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature-tc'], doc2)]

        assert len(tcValues) == 0

    def test_markCriticalTemperature_repulsion_for_Curie_temperature(self):
        input = "The corresponding magnetization loop recorded after ZFC to 5 K with the magnetic field " \
                "parallel to the a-b plane for a single La 2/3 Ca 1/3 MnO 3−x film of thickness ϳ200 nm on LSAT " \
                "is shown in A Curie temperature T C of about 220 K and a magnetic moment ͑T → 0 K͒ Ͼ 2 B per Mn ion " \
                "were derived from these curves."

        spans = [("5 K", "tcvalue"), ("La 2/3 Ca 1/3 MnO 3−x film", "material"), ("T C", "tc"), ("220 K", "tcvalue"), ]

        doc = prepare_doc(input, spans)
        doc2 = markCriticalTemperature(doc)

        tcValues = [entity for entity in filter(lambda w: w.ent_type_ in ['temperature-tc'], doc2)]

        assert len(tcValues) == 0

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

        boundaries = get_sentence_boundaries_pysbd(words, spaces)

        assert len(boundaries) == 6
