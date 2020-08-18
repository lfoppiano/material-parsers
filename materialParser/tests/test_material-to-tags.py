from material2class import Material2Tags


class TestMaterial2Tags:
    def test_material2tags(self):
        target = Material2Tags()
        taxonomy = target.get_classes("LaFeO2")

        assert len(taxonomy.keys()) == 1
        assert taxonomy.keys()[0] == 'Oxides'
        assert len(taxonomy['Oxides']) == 1
        assert taxonomy['Oxides'][0] == 'Transition Metal-Oxides'

    def test_1(self):
        target = Material2Tags()
        taxonomy = target.get_classes("SrFeCu0.2")

        assert len(taxonomy.keys()) == 1
        assert taxonomy.keys()[0] == 'Alloys'
        assert len(taxonomy['Alloys']) == 0