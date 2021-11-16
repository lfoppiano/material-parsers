import os

from bs4 import Tag, BeautifulSoup


def read_material_data(path):
    """
    This method parses the xml file in the form <materials><material>blablabla</material></materials> and extract
    the entities within the <material> tags

    :param path:
    :return: a list of dicts, each dicts has the element "raw", and "entities"
    """
    files_out = []
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for file_ in files:
                if not file_.lower().endswith(".tei.xml"):
                    continue

                files_out.append(os.path.join(root, file_))

    else:
        files_out = [path]

    entities = []
    for file in files_out:
        entities += read_material_data_from_file(file)

    return entities


def read_material_data_from_file(path):
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
