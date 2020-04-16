# transform tei annotation into prodigy annotations
import os
import sys
from html import escape
from sys import argv
from pathlib import Path


def processFile(file):
    output = {'paragraphs': [], 'rel_source_dest': [], 'rel_dest_source': []}

    spans = []
    tokens = []

    currentParagraph = {'text': "", 'spans': spans, 'tokens': tokens}

    inside = False

    with open(file) as fp:
        tokenPreviousPositionEnd = '-1'
        previousTagIndex = None
        previousTagValue = None
        tagIndex = None
        tagValue = None
        currentSpan = None
        tokenId = 0

        # If there are no relationships, the TSV has two column less.
        withRelationships = False
        relation_source_dest = {}
        relation_dest_source = {}
        for line in fp.readlines():
            if line.startswith("#Text") and not inside:  # Start paragraph
                currentParagraph['text'] = line.replace("#Text=", "")
                inside = True
                tokenId = 0

            elif not line.strip() and inside:  # End paragraph
                if currentSpan:
                    spans.append(currentSpan)

                output['paragraphs'].append(currentParagraph)
                currentParagraph = {'text': "", 'spans': [], 'tokens': []}

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
                    if line.startswith("#T_RL"):
                        withRelationships = True

                    print("Ignoring " + line)
                    continue

                split = line.split('\t')
                annotationId = split[0]
                position = split[1]
                tokenPositionStart = position.split("-")[0]
                tokenPositionEnd = position.split("-")[1]

                if tokenPreviousPositionEnd != tokenPositionStart and tokenPreviousPositionEnd != '-1':  ## Add space in the middle #fingercrossed
                    tokens.append(
                        {'start': tokenPreviousPositionEnd, 'end': tokenPositionStart, 'text': " ", 'id': tokenId})
                    tokenId = tokenId + 1

                text = split[2]
                tokens.append({'start': tokenPositionStart, 'end': tokenPositionEnd, 'text': text, 'id': tokenId})

                tag = split[4].strip()
                tag = tag.replace('\\', '')
                if withRelationships:
                    relationship_name = split[5].strip()
                    relationship_references = split[6].strip()
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


xmlPrefix = """<tei xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <fileDesc xml:id="_1" />
        <encodingDesc/>
    </teiHeader>
    <text xml:lang="en">\n"""

xmlSuffix = "\t</text>\n</tei>"


def writeOutput(datas, output):
    paragraphs = []
    rel_dest_source = datas['rel_dest_source']
    rel_source_dest = datas['rel_source_dest']
    for data in datas['paragraphs']:
        tokens = data['tokens']
        spans = data['spans']
        text = data['text']
        paragraph = '\t\t<p>'

        spanIdx = 0

        for i, token in enumerate(tokens):
            if spanIdx < len(spans):
                span = spans[spanIdx]
                span_token_start = span['token_start']
                span_token_end = span['token_end']
                span_label = span['label']
            else:
                span = None

            if span is not None:
                if i < span_token_start:
                    paragraph += escape(token['text'])
                    continue
                    # paragraph += token['text']
                elif span_token_start <= i <= span_token_end:
                    if i == span_token_start:
                        tagLabel = '<' + span_label + '>'
                        pointers = ''
                        identifier = ''
                        if span['tagIndex'] in rel_source_dest:
                            first = True
                            for dest in rel_source_dest[span['tagIndex']]:
                                if first:
                                    first = False
                                    pointers = ' ptr="#' + dest
                                else:
                                    pointers += ',#' + dest
                            pointers += '"'

                        if span['tagIndex'] in rel_dest_source:
                            identifier = ' id="' + span['tagIndex'] + '"'

                        if pointers is not '' or identifier is not '':
                            tagLabel = '<' + span_label + identifier + pointers + '>'

                        paragraph += tagLabel
                    paragraph += escape(token['text'])
                    if i == span_token_end:
                        # paragraph += token['text']
                        paragraph += '</' + span_label + '>'
                        spanIdx += 1

            else:
                paragraph += escape(token['text'])

        paragraph += '</p>\n'
        paragraphs.append(paragraph)

    with open(output, 'w') as fo:
        fo.write(xmlPrefix)
        for paragraphObj in paragraphs:
            fo.write(paragraphObj)
        fo.write(xmlSuffix)
        fo.flush()

if __name__ == '__main__':
    if len(argv) != 3:
        print("Invalid parameters. Usage: python tsv2xml_webanno.py input_file output_file")
        sys.exit(-1)

    input = argv[1]
    output = argv[2]

    if os.path.isdir(input):
        path_list = Path(input).glob('*.tsv')
        for path in path_list:
            print("Processing: ", path)
            output_filename = path.stem
            data = processFile(path)
            writeOutput(data, os.path.join(output, str(output_filename) + ".tei.xml"))
    elif os.path.isfile(input):
        input_path = Path(input)
        data = processFile(input_path)
        output_filename = input_path.stem
        writeOutput(data, os.path.join(output, str(output_filename) + ".tei.xml"))
