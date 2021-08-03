def span_to_dict(span):
    converted_span = {
        'text': span.text,
        'formattedText': span._.formattedText,
        'type': span.ent_type_,
        'offsetStart': span.idx,
        'offsetEnd': span.idx + len(span.text),
        'tokenStart': span.i,
        'tokenEnd': span.i + len(span),
        'id': span._.id,
        'boundingBoxes': span._.bounding_boxes,
        'links': span._.links,
        'linkable': span._.linkable
    }

    return converted_span


def token_to_dict(token):
    converted_token = {
        'text': token.text,
        'offset': token.idx,
        'formattedText': token._.formattedText,
        'linkable': token._.linkable
    }
    # converted_token['style']
    # converted_token['font'] = span.ent_type_
    # converted_token['fontSize'] = span.i

    return converted_token


def to_dict_link(target_id, target_text, target_type, type= None):
    link = {
        "targetId": target_id,
        "targetText": target_text,
        "targetType": target_type,
        "type": type
    }
    return link


def to_dict_token(text="", offset=-1):
    token = {
        "text": text,
        "formattedText": "",
        "font": "",
        "style": "",
        "offset": offset,
        "fontSize": "",
        "linkable": False
    }

    return token


def to_dict_span(text, type, id=None, offsetStart=-1, offsetEnd=-1, tokenStart=-1, tokenEnd=-1):
    converted_span = {
        "id": id,
        "text": str(text),
        "formattedText": "",
        "type": type,
        "offsetStart": offsetStart,
        "offsetEnd": offsetEnd,
        "tokenStart": tokenStart,
        "tokenEnd": tokenEnd,
        "boundingBoxes": [],
        "links": [],
        "source": '',
        "linkable": False
    }

    if id is None:
        id = compute_id(converted_span)
        converted_span['id'] = id

    return converted_span


def compute_id(span):
    output = [span['text'], span['type'], span['offsetStart'], span['offsetEnd'], span['tokenStart'], span['tokenEnd'],
              span['source']]

    output = [str(o) for o in output]

    return hash("".join(output))
