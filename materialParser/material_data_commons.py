from bs4 import Tag, BeautifulSoup


def readMaterialData(path):
    """
    This method parses the xml file in the form <materials><material>blablabla</material></materials> and extract
    the entities within the <material> tags

    :param path:
    :return: a list of dicts, each dicts has the element "raw", and "entities"
    """
    entities = []

    ## Loading evaluation data
    with open(path, 'r') as fp:
        doc = fp.read()

        soup = BeautifulSoup(doc, 'xml')

        for i, pTag in enumerate(soup.materials):
            if type(pTag) == Tag:
                item = {
                    'raw': str(pTag.get_text()),
                    'entities': {}
                }
                entities.append(item)
                for child in pTag.children:
                    if type(child) == Tag:
                        item['entities'][child.name] = child.get_text()
                        # print(child.get_text())
                        # print(child.name)

    return entities