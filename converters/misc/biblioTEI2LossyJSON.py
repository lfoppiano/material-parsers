'''
    Converts the bibliographic data in TEI to Lossy JSON
'''

# add packages
import argparse
import asyncio
import json
import os.path
from pathlib import Path

from bs4 import BeautifulSoup

# create tag list
tag2attr = {
    "addrline": None,
    # "author": None,
    "biblscope": "unit",
    "date": "when",
    "editor": None,
    "idno": "type",
    "note": None,
    "ptr": "type",
    "publisher": None,
    "pubplace": None,
    "title": "level",
    "abstract": None
}

tag_list = list(tag2attr.keys())


async def fetch_author(auth):
    """
    Return author attributes in dict
    :param auth: bs4.BeautifulSoup
    :return: dict
    """
    auth_ = {}
    for name_part in ["first", "middle"]:
        if auth.find("forename", {"type": name_part}):
            name = auth.find("forename", {"type": name_part}).get_text()
            auth_.update({name_part: name})
    for name_part in ["surname", "genname"]:
        if auth.find(name_part):
            name = auth.find(name_part).get_text()
            auth_.update({name_part: name})
    return auth_


async def fetch_authors(soup):
    """
    Return the list of author dict
    :param soup: bs4.element.Tag
    :return: List[dict]
    """
    if soup.find_all("author"):
        authors = [fetch_author(auth) for auth in soup.find_all("author") if fetch_author(auth)]
        return await asyncio.gather(*authors)


async def fetch_keywords(soup):
    """Get the keywords"""
    if soup.find_all("keywords"):
        keywords = [term.string.rstrip() for keywords in soup.find_all("keywords") for term in keywords if
                    (term.string.rstrip())]
        return keywords
    else:
        return []


async def fetch_tag(tag):
    """
    Return a dict for each tag with k the name of the tag and v the string of the tag
    :param tag: bs4.element.Tag
    :return: dict
    """
    assert tag.name in tag_list
    attr = tag2attr[tag.name]
    if attr and tag.string:
        if tag.name == "title":
            try:
                attr_type = "_" + tag["type"] if 'type' in tag else ''
                return {tag.name + attr_type + "_" + tag[attr]: tag.string}
            except KeyError:
                return {tag.name + "_" + attr: tag.string}
        elif tag.name == "date":
            try:
                return {tag.name: tag[attr]}
            except KeyError:
                return {tag.name: tag.string}
        else:
            try:
                return {tag[attr]: tag.string}
            except KeyError:  # handles cases like <idno>Pages 15 - 20</idno>
                return {tag.name: tag.string}
    else:
        return {tag.name: str.strip(tag.text)}


async def fetch_all_tags(id_, soup, id_name="npl_publn_id", output_file=None):
    """
    Return grobid ouptut as a json
    :param id_: str
    :param soup: 'bs4.BeautifulSoup'
    :param id_name: str
    :return: dict
    """
    tasks = []
    for tag_ in tag_list:
        for tag in soup.find_all(tag_):
            task = asyncio.create_task(fetch_tag(tag))
            tasks.append(task)
    task_authors = asyncio.create_task(fetch_authors(soup))
    task_keywords = asyncio.create_task(fetch_keywords(soup))

    tasks = await asyncio.gather(*tasks)
    await task_authors
    await task_keywords

    cit = {}

    for task in tasks:
        if len([value for value in task.values() if value]) > 0:
            cit.update(task)
    cit.update({"authors": task_authors.result()})
    cit.update({"keywords": task_keywords.result()})
    cit.update({id_name: id_})
    with open(output_file, 'w') as out:
        json.dump(cit, out)


def get_schema(primary_key="npl_publn_id", pk_type="number"):
    schema = {
        "type": "object",
        "properties": {
            primary_key: {"type": pk_type},
            "DOI": {"type": "string"},
            "ISSN": {"type": "string"},
            "ISSNe": {"type": "string"},
            "PMCID": {"type": "string"},
            "PMID": {"type": "string"},
            "authors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "first": {"type": "string"},
                        "middle": {"type": "string"},
                        "surname": {"type": "string"},
                        "genname": {"type": "string"},
                    },
                },
            },
            "target": {"type": "string"},
            "title_j": {"type": "string"},
            "title_abbrev_j": {"type": "string"},
            "title_m": {"type": "string"},
            "title_main_m": {"type": "string"},
            "title_main_a": {"type": "string"},
            "year": {"type": "number"},
            "issue": {"type": "number"},
            "volume": {"type": "number"},
            "from": {"type": "number"},
            "to": {"type": "number"},
            "abstract": {"type": "string"},
            "issues": {"type": "array"}
            # 'page': {"type": "string"},
            # 'type': {"type": "string"},
            # 'unit': {"type":},
            # 'when': {"type": "string"}
            # 'idno': {"type":},
        },
        "required": [primary_key],
    }
    return schema


def process_file(input_file: Path, output_file: Path):
    with open(input_file, 'r') as tei:
        soup = BeautifulSoup(tei, 'lxml')
        root = None
        for child in soup.tei.children:
            if child.name == 'teiheader':
                root = child

        # event_loop = asyncio.get_event_loop()
        asyncio.run(fetch_all_tags(str(input_file.name), root, output_file=output_file))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converter Bibliographic TEI files to JSON lossy format.")

    parser.add_argument("--input", help="Input file or directory", required=True)
    parser.add_argument("--output", required=False,
                        help="Output directory (omitted, outputs to the same directory/file with different extension)")
    parser.add_argument("--recursive", action="store_true", default=False,
                        help="Process input directory recursively. If input is a file, this parameter is ignored. ")

    args = parser.parse_args()

    input = args.input
    output = args.output
    recursive = args.recursive

    if os.path.isdir(input):
        path_list = []

        if recursive:
            for root, dirs, files in os.walk(input):
                for file_ in files:
                    if not file_.lower().endswith(".tei.xml"):
                        continue

                    abs_path = os.path.join(root, file_)
                    path_list.append(abs_path)

        else:
            path_list = Path(input).glob('*.tei.xml')

        for path in path_list:
            print("Processing: ", path)
            output_filename = Path(path).stem
            parent_dir = Path(path).parent
            if os.path.isdir(str(output)):
                output_path = os.path.join(output, str(output_filename)) + ".json"
            else:
                output_path = os.path.join(parent_dir, output_filename + ".json")

            process_file(Path(path), Path(output_path))

    elif os.path.isfile(input):
        input_path = Path(input)
        output_filename = input_path.stem
        output_path = os.path.join(output, str(output_filename) + ".json")
        process_file(input_path, Path(output_path))
