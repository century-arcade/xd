#!/usr/bin/env python3

import re
from urllib.parse import unquote
from lxml import etree

import xdfile
from xdfile.utils import escape, consecutive, xml_escape_table, rev_xml_escape_table


def udecode(s):
    t = unquote(s)
    try:
        return str(t.decode("utf-8"))
    except:
        return str(t)


def parse_uxml(content, filename):
    POSSIBLE_META_DATA = ['Title', 'Author', 'Editor', 'Copyright', 'Category']

    try:
        content = content.decode("utf-8")
    except:
        try:
            content = content.decode("cp1252")
        except:
            pass  # last ditch effort, just try the original string

    content = escape(content, xml_escape_table)
    content = re.sub(r'(=["]{2}([^"]+?)["]{2})+',r'="&quot;\2&quot;"', content) # Replace double quotes

    try:
        root = etree.fromstring(content.encode("utf-8"))
    except:
        # TODO: catch the specific exception
        xml = re.search(r"<(\w+).*?</\1>", content, flags=re.DOTALL).group()
        root = etree.fromstring(xml)

    # init crossword
    # rows = int(root.xpath('//crossword/Height')[0].attrib['v'])
    cols = int(root.xpath('//crossword/Width')[0].attrib['v'])
    xd = xdfile.xdfile('', filename)

    # add meta data
    for item in POSSIBLE_META_DATA:
        elem = root.xpath('//crossword/' + item)
        if elem:
            text = elem[0].attrib['v']
            if text:
                text = escape(text, rev_xml_escape_table)
                xd.set_header(item, unquote(text))

    # add puzzle
    all_answers = root.xpath('//crossword/AllAnswer')[0].attrib['v']
    all_answers = all_answers.replace('-', xdfile.BLOCK_CHAR)
    index = 0
    while index < len(all_answers):
        row = all_answers[index:index + cols]
        xd.grid.append("".join(row))
        index += cols

    # add clues
    for clue_type in ('across', 'down'):
        for clue in root.xpath('//crossword/' + clue_type)[0].getchildren():
            number = int(clue.attrib['cn'])
            text = udecode(clue.attrib['c'].strip())
            text = escape(text, rev_xml_escape_table)
            solution = clue.attrib['a'].strip()
            xd.clues.append(((clue_type[0].upper(), number), text, solution))

    return xd

if __name__ == "__main__":
    xdfile.main_parse(parse_uxml)
