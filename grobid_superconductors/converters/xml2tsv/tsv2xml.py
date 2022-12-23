# transform tei annotation into prodigy annotations
import argparse
import os
import re
from html import escape
from pathlib import Path

from bs4 import BeautifulSoup
from webanno_tsv import webanno_tsv_read_file


def process_file_new(file):
    doc = webanno_tsv_read_file(file)
    output = {'paragraphs': [], 'rel_source_dest': [], 'rel_dest_source': []}

    spans_ = []
    tokens_ = []
    current_paragraph = {'text': "", 'spans': [], 'tokens': [], 'section': 'body'}

    for sentence in doc.sentences:
        tokens = doc.sentence_tokens(sentence)

        previous_token_end = 0
        addition = 0
        for token in tokens:
            # if previous_token_end > 0 and previous_token_end != token.start:
            #     tokens_.append(
            #         {
            #             'start': previous_token_end,
            #             'end': token.start,
            #             'text': " ",
            #             'id': ""
            #         }
            #     )
            #     addition += 1

            tokens_.append(
                {
                    'start': token.start,
                    'end': token.end,
                    'text': token.text,
                    'id': token.idx
                }
            )
            previous_token_end = token.end

        for annotation in doc.match_annotations(sentence=sentence, layer='webanno.custom.Xml'):
            pass

        for annotation in doc.match_annotations(sentence=sentence, layer='webanno.custom.Materials'):
            annotation_tokens = annotation.tokens
            start_offset = annotation_tokens[0].start
            end_offset = annotation_tokens[-1].end

            start_index = annotation_tokens[0].idx
            end_index = annotation_tokens[-1].idx

            label = annotation.label
            text = annotation.text

            current_span = {
                'start': start_offset,
                'end': end_offset,
                'token_start': start_index,
                'token_end': end_index,
                'label': label,
                'text': text,
                'tagIndex': annotation.label_id,
                'relationships': []
            }

            spans_.append(current_span)

        current_paragraph['text'] = sentence.text
        current_paragraph['spans'] = spans_
        current_paragraph['tokens'] = tokens_
        current_paragraph['section'] = "body"
        output['paragraphs'].append(current_paragraph)

        spans_ = []
        tokens_ = []
        current_paragraph = {'text': "", 'spans': [], 'tokens': [], 'section': 'body'}

    return output


def process_file(file):
    output = {'paragraphs': [], 'rel_source_dest': [], 'rel_dest_source': []}

    spans = []
    tokens = []

    currentParagraph = {'text': "", 'spans': spans, 'tokens': tokens, 'section': 'body'}

    inside = False

    with open(file) as fp:
        tokenPreviousPositionEnd = '-1'
        previousTagIndex = None
        previousTagValue = None
        tagIndex = None
        tagValue = None
        currentSpan = None
        tokenId = 0
        entitiesLayerFirstIndex = -1
        sectionLayerFirstIndex = -1
        hasDocumentStructure = False

        # If there are no relationships, the TSV has two column less.
        with_relationships = False
        relation_source_dest = {}
        relation_dest_source = {}
        spans_layers = 3
        layerTagsets = []
        relationship_layer_index = 5  # The usual value
        for line in fp.readlines():
            if line.startswith("#Text") and not inside:  # Start paragraph
                currentParagraph['text'] = line.replace("#Text=", "")
                inside = True
                tokenId = 0

            elif not line.strip() and inside:  # End paragraph
                if currentSpan:
                    spans.append(currentSpan)

                output['paragraphs'].append(currentParagraph)
                currentParagraph = {'text': "", 'spans': [], 'tokens': [], 'section': "body"}

                spans = currentParagraph['spans']
                tokens = currentParagraph['tokens']
                tokenPreviousPositionEnd = '-1'
                previousTagIndex = None
                previousTagValue = None
                tagIndex = None
                tagValue = None
                currentSpan = None

                inside = False
            else:
                if not inside:
                    ignored_layers = []
                    if line.startswith("#T_SP"):
                        layers = line.replace("\n", "").split('|')
                        layerName = layers[0].split('=')[1]
                        layerTagsets += layers[1:]
                        if layerName == 'webanno.custom.Section':
                            sectionLayerFirstIndex = spans_layers
                            hasDocumentStructure = True
                        else:
                            entitiesLayerFirstIndex = spans_layers
                            # entitiesLayerLabelIndex = entitiesLayerFirstIndex + 1

                        # layerTagsets = len(line.split('|')) - 1
                        # spans_layers += len(layerTagsets)

                    if line.startswith("#T_RL"):
                        with_relationships = True
                        if spans_layers > 0:
                            relationship_layer_index = spans_layers + len(layerTagsets)

                    print("Ignoring " + line)
                    continue

                line_split = line.split('\t')
                annotationId = line_split[0]
                position = line_split[1]
                tokenPositionStart = position.split("-")[0]
                tokenPositionEnd = position.split("-")[1]

                # if tokenPreviousPositionEnd != tokenPositionStart and tokenPreviousPositionEnd != '-1':  ## Add space in the middle #fingercrossed
                #     tokens.append(
                #         {'start': tokenPreviousPositionEnd, 'end': tokenPositionStart, 'text': " ", 'id': tokenId})
                #     tokenId = tokenId + 1

                text = line_split[2]
                tokens.append({'start': tokenPositionStart, 'end': tokenPositionEnd, 'text': text, 'id': tokenId})

                section = "body"
                if sectionLayerFirstIndex > -1:
                    section = line_split[sectionLayerFirstIndex].split('[')[0]

                currentParagraph['section'] = section
                tags = line_split[spans_layers:spans_layers + len(layerTagsets)]
                # We assume to have only one tag
                tag = "_"
                for idx, tag_ in enumerate(tags):
                    # Change 0 to 1 for the NEDO project
                    if idx not in [0, 3, 4] and tag_ != '_':
                        if not re.search("\\*\\[\d+\\]", tag_) and tag_ != '*':
                            tag = tag_.strip()
                            break
                        else:
                            # If we dont' find the tag, we try to see if it's hidden into ['*[83]|material[84]', 'process[83]|*[84]', '*[83]|*[84]', '_', '_']
                            matching = re.match("\\*\\[\d+\\]\\|([^\\[*\\]]+\\[\d+\\])", tag_)
                            if matching and len(matching.groups()) > 0:
                                tag = matching.group(1).strip()
                                break

                tag = tag.replace('\\', '')

                if with_relationships:
                    relationship_name = line_split[relationship_layer_index].strip()
                    relationship_references = line_split[relationship_layer_index + 1].strip()
                else:
                    relationship_name = '_'
                    relationship_references = '_'

                relationships = []  # list of tuple(source, destination)

                if relationship_name != '_' and relationship_references != '_':
                    # We ignore the name of the relationship for the moment
                    # names = relationship_name.split("|")

                    # We split by | as they are grouped as
                    # 2-162	1965-1969	YBCO	*[1]	material[1]	material-tc|material-tc	2-176[0_1]|2-179[0_1]
                    references = relationship_references.split("|")
                    for reference in references:
                        reference_split = reference.split('[')
                        if len(reference_split) == 1:
                            # no disambiguation ids, so I use
                            #   destination = layer-token (element 0)
                            #   source = layer-token of reference (elemnt 6)

                            source = reference
                            destination = annotationId
                        elif len(reference_split) > 1:
                            reference_source_tsv = reference_split[0]
                            source = reference_split[1].split('_')[0]
                            destination = reference_split[1].split('_')[1][:-1]

                            if source == '0':
                                source = reference_source_tsv
                            elif destination == '0':
                                destination = annotationId

                        relationships.append((source, destination))
                        if source not in relation_source_dest:
                            relation_source_dest[source] = [destination]
                        else:
                            relation_source_dest[source].append(destination)

                        if destination not in relation_dest_source:
                            relation_dest_source[destination] = [source]
                        else:
                            relation_dest_source[destination].append(source)

                if tag != '_' and not tag.startswith('*'):
                    if tag.endswith("]"):
                        tagValue = tag.split('[')[0]
                        tagIndex = tag.split('[')[1][:-1]
                    else:
                        tagValue = tag
                        tagIndex = -1

                    if tagIndex != -1:
                        if tagIndex != previousTagIndex:
                            if currentSpan:
                                spans.append(currentSpan)
                            currentSpan = {'start': tokenPositionStart, 'end': tokenPositionEnd, 'token_start': tokenId,
                                           'token_end': tokenId, 'label': tagValue, 'tagIndex': tagIndex,
                                           'relationships': relationships}
                        else:
                            if tagValue == previousTagValue:
                                currentSpan['end'] = tokenPositionEnd
                                currentSpan['token_end'] = tokenId
                            else:
                                if currentSpan:
                                    spans.append(currentSpan)
                                currentSpan = {'start': tokenPositionStart, 'end': tokenPositionEnd,
                                               'token_start': tokenId,
                                               'token_end': tokenId, 'label': tagValue, 'tagIndex': tagIndex,
                                               'relationships': relationships}
                    else:
                        if currentSpan:
                            spans.append(currentSpan)
                        currentSpan = {'start': tokenPositionStart, 'end': tokenPositionEnd, 'token_start': tokenId,
                                       'token_end': tokenId, 'label': tagValue, 'tagIndex': annotationId,
                                       'relationships': relationships}

                else:
                    if currentSpan:
                        spans.append(currentSpan)
                        currentSpan = None

                tokenId = tokenId + 1

                tokenPreviousPositionEnd = tokenPositionEnd  # copy the position end
                previousTagIndex = tagIndex  # index of the tag in the tsv
                previousTagValue = tagValue

        # print(output)
        # if not line.startswith(str(paragraph_index) + "-"):
        #     print("Something is wrong in the synchronisation " + str(paragraph_index) + " vs " + line[0:4])
        #     sys.exit(-255)

        # print(split)

    output['paragraphs'].append(currentParagraph)
    output['rel_dest_source'] = relation_dest_source
    output['rel_source_dest'] = relation_source_dest
    return output


xmlTemplate = """<tei xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <fileDesc xml:id="_0">
            <titleStmt/>
            <publicationStmt>
                <publisher>National Institute for Materials Science (NIMS), Tsukuba, Japan</publisher>
                <availability>
                    <licence target="http://nims.go.jp">
                        <p>Copyright National Institute for Materials Science (NIMS), Tsukuba, Japan</p>
                    </licence>
                </availability>
            </publicationStmt>
        </fileDesc>
        <encodingDesc>
            <appInfo>
                <application version="project.version" ident="grobid-superconductors">
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


def get_text_under_body(soup):
    children = soup.findChildren('text')
    return children[0] if children is not None and len(
        children) > 0 else None


def writeOutput(datas, output):
    paragraphs = []
    rel_dest_source = datas['rel_dest_source']
    rel_source_dest = datas['rel_source_dest']
    previous_token_end = 0
    for data in datas['paragraphs']:
        tokens = data['tokens']
        spans = data['spans']

        spans = prune_spans(spans)

        text = data['text']
        section = data['section']
        paragraph = ''

        spanIdx = 0
        first = True

        for i, token in enumerate(tokens):
            id = token['id']
            if not first and previous_token_end > 0 and previous_token_end != token['start']:
                paragraph += " "
                previous_token_end += 1

            first = False

            if spanIdx < len(spans):
                span = spans[spanIdx]
                span_token_start = span['token_start']
                span_token_end = span['token_end']
                span_label = span['label']
            else:
                span = None

            if span is not None:
                if id < span_token_start:
                    paragraph += escape(token['text'])

                    previous_token_end = token['end']
                    continue

                elif span_token_start <= id <= span_token_end:
                    if id == span_token_start:
                        tagLabel = '<rs type="' + span_label + '">'
                        pointers = ''
                        identifier = ''
                        if span['tagIndex'] in rel_source_dest:
                            first = True
                            for dest in rel_source_dest[span['tagIndex']]:
                                if first:
                                    first = False
                                    pointers = ' corresp="#x' + dest
                                else:
                                    pointers += ',#x' + dest
                            pointers += '"'

                        if span['tagIndex'] in rel_dest_source:
                            identifier = ' xml:id="x' + span['tagIndex'] + '"'

                        if pointers != '' or identifier != '':
                            tagLabel = '<rs type="' + span_label + '"' + identifier + pointers + '>'

                        paragraph += tagLabel
                    paragraph += escape(token['text'])
                    if id == span_token_end:
                        # paragraph += token['text']
                        paragraph += '</rs>'
                        spanIdx += 1

            else:
                paragraph += escape(token['text'])

            previous_token_end = token['end']
        paragraphs.append((section, paragraph))

    with open(output, 'w') as fo:
        soup = BeautifulSoup(xmlTemplate, 'xml')
        for section, paragraphObj in paragraphs:
            if section == 'title':
                tag = BeautifulSoup('<title>' + paragraphObj + '</title>', 'xml')
                soup.teiHeader.titleStmt.append(tag)
            elif section == 'abstract':
                tag = BeautifulSoup('<p>' + paragraphObj + '</p>', 'xml')
                soup.teiHeader.profileDesc.abstract.append(tag)
            elif section == 'keywords':
                tag = BeautifulSoup('<ab type="keywords">' + paragraphObj + '</ab>', 'xml')
                soup.teiHeader.profileDesc.append(tag)
            elif section == 'body':
                tag = BeautifulSoup('<p>' + paragraphObj + '</p>', 'xml')
                text_tag = get_text_under_body(soup)
                text_tag.body.append(tag)
            elif section == 'figureCaption' or section == 'tableCaption':
                tag = BeautifulSoup('<ab type="' + section + '">' + paragraphObj + '</ab>', 'xml')
                text_tag = get_text_under_body(soup)
                text_tag.body.append(tag)

        fo.write(str(soup))
        fo.flush()


def prune_spans(spans):
    to_remove = []
    for i in range(len(spans) - 1):
        if spans[i]['start'] == spans[i + 1]['start'] and spans[i]['end'] == spans[i + 1]['end']:
            to_remove.append(i + 1)
            spans[i]['label'] += "," + spans[i + 1]['label']
    if len(to_remove) > 0:
        for idx in sorted(to_remove, reverse=True):
            spans.pop(idx)

    return spans


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Converter TSV to XML (Grobid training data based on TEI)")

    parser.add_argument("--input", help="Input file or directory", required=True, type=Path)
    parser.add_argument("--output",
                        help="Output directory (if omitted, the output will be the same directory/file with different extension)",
                        required=False, type=Path, default=None)
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
                # Manage to create the directories
                for dir in dirs:
                    abs_path_dir = os.path.join(root, dir)
                    output_path = abs_path_dir.replace(str(input), str(output))
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)

                for file_ in files:
                    if not file_.lower().endswith(".tsv"):
                        continue

                    abs_path = os.path.join(root, file_)
                    output_filename = Path(abs_path).stem
                    parent_dir = Path(abs_path).parent
                    if os.path.isdir(str(output)):
                        output_ = Path(str(parent_dir).replace(str(input), str(output)))
                        output_filename_with_extension = str(output_filename) + ".tei.xml"
                        output_path = os.path.join(output_, output_filename_with_extension)
                    else:
                        output_path = os.path.join(parent_dir, output_filename + ".tei.xml")

                    path_list.append((abs_path, output_path))

        else:

            for abs_path in Path(input).glob('*.tsv'):
                abs_path_ = str(abs_path).replace(".tei", "")
                output_filename = Path(abs_path_).stem
                parent_dir = Path(abs_path_).parent
                if os.path.isdir(str(output)):
                    output_ = Path(str(parent_dir).replace(str(input), str(output)))
                    output_filename_with_extension = str(output_filename) + ".tei.xml"
                    output_path = os.path.join(output_, output_filename_with_extension)
                else:
                    output_path = os.path.join(output_, output_filename + ".tei.xml")

                path_list.append((abs_path, output_path))

        for input_path, output_path in path_list:
            print("Processing: ", input_path)
            data = process_file_new(input_path)
            writeOutput(data, output_path)

    elif os.path.isfile(input):
        input_path = Path(input)
        data = process_file_new(input_path)
        output_filename = input_path.stem
        writeOutput(data, os.path.join(output, str(output_filename) + ".tei.xml"))
