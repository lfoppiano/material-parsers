import os.path
from html import escape
from os import listdir, path
from collections import namedtuple
import argparse
from pathlib import Path

from blingfire import text_to_sentences
from bs4 import BeautifulSoup
from tqdm import tqdm

from material_parsers.commons.ann_parser import ANNParser

XML_TEMPLATE = """<tei xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <fileDesc xml:id="_0">
            <titleStmt/>
            <publicationStmt>
                <publisher>Yamaguchi, Kyosuke; Asahi, Ryoji; Sasaki, Yutaka (2021), “SC-CoMIcs (Superconductivity Corpus for Materials Infomatics)”, Mendeley Data, V2, doi: 10.17632/xc9fjz2p3h.2</publisher>
                <availability>
                    <licence target="https://creativecommons.org/licenses/by-nc/3.0/">
                        <p>CC BY NC 3.0</p>
                    </licence>
                </availability>
            </publicationStmt>
        </fileDesc>
        <encodingDesc>
            <appInfo>
                <application version="0.4.0" ident="grobid-superconductors">
                    <ref target="https://github.com/lfoppiano/grobid-superconductors">A machine learning software for extracting materials and their properties from scientific literature.</ref>
                </application>
            </appInfo>
        </encodingDesc>
        <profileDesc>
            <abstract/>            
        </profileDesc>
    </teiHeader>
    <text xml:lang="en">
        <body/>
    </text>
</tei>"""


def read_input_folder(input_dir):
    """Read multiple annotation files from a given input folder"""
    file_list = listdir(input_dir)
    annotation_files = sorted([file for file in file_list if file.endswith('.ann')])

    file_pair_list = []
    file_pair = namedtuple('file_pair', ['ann', 'text'])
    # The folder is assumed to contain *.ann and *.txt files with the 2 files of a pair having the same file name
    for file in annotation_files:
        if file.replace('.ann', '.txt') in file_list:
            file_pair_list.append(
                file_pair(path.join(input_dir, file), path.join(input_dir, file.replace('.ann', '.txt'))))
        else:
            raise f"{file} does not have a corresponding text file"

    return file_pair_list


def write_output(datas, output, split_sentences=False):
    for parsed_file, content in tqdm(datas.items(), desc="Writing output files"):
        raw_spans = [ent + (label,) for label, entities in content['ent'].items() for ent in entities]
        spans = sorted(raw_spans, key=lambda x: x[1])
        text = content['text']
        # tokens = text.split()

        output_text = ""
        if split_sentences:
            sentences = text_to_sentences(text).split("\n")
            sentence_offset = 0
            for sentence in sentences:
                spans_within_current_sentence = filter(lambda x: x[1] >= sentence_offset and x[
                    2] < sentence_offset + len(sentence), spans)
                output_text += (
                    '<s>' + inject_spans_in_text(sentence, spans_within_current_sentence, sentence_offset) + '</s>')
                sentence_offset += len(sentence) + 1  # assumption there is a space after the period
        else:
            output_text = [inject_spans_in_text(text, spans)]

        if len(output_text) > 0:
            with open(os.path.join(output, parsed_file.replace(".ann", ".tei.xml")), 'w') as fo:
                soup = BeautifulSoup(XML_TEMPLATE, 'xml')
                tag = BeautifulSoup('<p>' + output_text + '</p>', 'xml')
                soup.teiHeader.profileDesc.abstract.append(tag)

                fo.write(str(soup))
                fo.flush()


def inject_spans_in_text(text, spans, sentence_offset=0):
    last_pos = 0
    text_with_spans = ""
    for type_, offset_start, offset_end, ent_text, label in spans:
        text_with_spans += escape(
            text[last_pos: offset_start - sentence_offset]) + '<rs type="' + label + '">' + escape(
            ent_text) + '</rs>'
        last_pos = offset_end - sentence_offset
    text_with_spans += escape(text[last_pos:])
    return text_with_spans


def modify_entities(parsed_files):
    for parsed_file, content in tqdm(parsed_files.items(), desc="Converting to SuperMat"):
        entity_dict = content['ent']
        converted_entity_dict = {}

        # material
        if "Element" in entity_dict:
            converted_entity_dict['material'] = entity_dict['Element']

        if "Main" in entity_dict:
            if 'material' in converted_entity_dict:
                converted_entity_dict['material'].extend(entity_dict['Main'])
            else:
                converted_entity_dict['material'] = entity_dict['Main']
        # tc
        if "SC" in entity_dict:
            converted_entity_dict['tc'] = entity_dict['SC']

        # me_method
        if "Property" in entity_dict:
            for value_ent in entity_dict['Property']:
                ent_text = value_ent[3]
                if 'resistivity' in ent_text or 'susceptibility' in ent_text or 'specific heat' in ent_text:
                    if 'me_method' not in converted_entity_dict:
                        converted_entity_dict['me_method'] = []
                    converted_entity_dict['me_method'].append(value_ent)

        # tcValue / pressure
        if "Value" in entity_dict:
            for value_ent in entity_dict['Value']:
                ent_text = value_ent[3]
                if ent_text.endswith("Pa") or ent_text.endswith("bar"):
                    if 'pressure' not in converted_entity_dict:
                        converted_entity_dict['pressure'] = []
                    converted_entity_dict['pressure'].append(value_ent)

                if ent_text.endswith("K"):
                    if 'tcValue' not in converted_entity_dict:
                        converted_entity_dict['tcValue'] = []
                    converted_entity_dict['tcValue'].append(value_ent)

        content['ent'] = converted_entity_dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True,
                        help="Input directory where the ScComics's standoff annotations (ann and txt files) are stored")

    parser.add_argument("--output", type=Path, required=True,
                        help="Output directory where the XML TEI format files are saved")

    parser.add_argument("--sentences", action="store_true", required=False, default=False,
                        help="Split input files in sentences using BlingFire.")

    parser.add_argument("--supermat", action="store_true", required=False, default=False,
                        help="Output entities and labels following superMat guidelines (https://supermat.readthedocs.io).")

    args = parser.parse_args()

    parsed_files = ANNParser(args.input, ignore_rel=True).parse()

    if args.supermat:
        modify_entities(parsed_files)

    write_output(parsed_files, args.output, args.sentences)
