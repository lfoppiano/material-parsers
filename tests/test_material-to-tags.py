from  material_parsers.material_parser.material2class import Material2Tags


class TestMaterial2Tags:
    def test_material2Tags_Oxide(self):
        target = Material2Tags()
        taxonomy = target.get_classes("LaFeO2")

        assert len(taxonomy.keys()) == 1
        assert list(taxonomy.keys())[0] == 'Oxides'
        assert len(taxonomy['Oxides']) == 1
        assert taxonomy['Oxides'][0] == 'Transition Metal-Oxides'

    def test_material2Tags_Alloys(self):
        target = Material2Tags()
        taxonomy = target.get_classes("SrFeCu0.2")

        assert len(taxonomy.keys()) == 1
        assert list(taxonomy.keys())[0] == 'Alloys'
        assert len(taxonomy['Alloys']) == 0

    def test_material2Tags_mixedCombinations_0(self):
        target = Material2Tags()
        taxonomy = target.get_classes("CuFrO2")

        assert len(taxonomy.keys()) == 2
        first_level = sorted(list(taxonomy.keys()))
        assert first_level[0] == 'Cuprates'
        assert first_level[1] == 'Oxides'
        assert len(taxonomy['Oxides']) == 1
        assert len(taxonomy['Cuprates']) == 0

    def test_material2Tags_mixedCombinations_1(self):
        target = Material2Tags()
        taxonomy = target.get_classes("CuFrO2C")

        assert len(taxonomy.keys()) == 3
        first_level = sorted(list(taxonomy.keys()))

        assert first_level[0] == 'Carbides'
        assert first_level[1] == 'Cuprates'
        assert first_level[2] == 'Oxides'
        assert len(taxonomy['Carbides']) == 1
        assert len(taxonomy['Cuprates']) == 0
        assert len(taxonomy['Oxides']) == 1

    def test_material2Tags_mixedCombinations_2(self):
        target = Material2Tags()
        taxonomy = target.get_classes("CuFrO2H")

        assert len(taxonomy.keys()) == 3
        first_level = sorted(list(taxonomy.keys()))

        assert first_level[0] == 'Cuprates'
        assert first_level[1] == 'Hydrides'
        assert first_level[2] == 'Oxides'
        assert len(taxonomy['Cuprates']) == 0
        assert len(taxonomy['Hydrides']) == 0
        assert len(taxonomy['Oxides']) == 1

    def test_material2Tags_mixedCombinations_3(self):
        target = Material2Tags()
        taxonomy = target.get_classes("CuFrO2CH")

        assert len(taxonomy.keys()) == 4
        first_level = sorted(list(taxonomy.keys()))

        assert first_level[0] == 'Carbides'
        assert first_level[1] == 'Cuprates'
        assert first_level[2] == 'Hydrides'
        assert first_level[3] == 'Oxides'
        assert len(taxonomy['Cuprates']) == 0
        assert len(taxonomy['Carbides']) == 1
        assert len(taxonomy['Hydrides']) == 0
        assert len(taxonomy['Oxides']) == 1

    def test_material2Tags_mixedCombinations(self):
        target = Material2Tags()
        taxonomy = target.get_classes("CsFe2As2")

        assert len(taxonomy.keys()) == 2
        first_level = sorted(list(taxonomy.keys()))
        assert first_level[0] == 'Iron-pnictides'
        assert first_level[1] == 'Pnictides'
        assert len(taxonomy['Iron-pnictides']) == 0
        assert len(taxonomy['Pnictides']) == 0
