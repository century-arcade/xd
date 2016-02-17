#!/usr/bin/env python

from urllib import unquote
from lxml import etree

import xdfile

def parse_uxml(content):
    content = content.replace(" & ", " &amp; ")
    content = content.replace("''", '&quot;')
    POSSIBLE_META_DATA = ['Title', 'Author', 'Editor', 'Copyright', 'Category']

    root = etree.fromstring(content.decode("iso-8859-1"))

    # init crossword
    rows = int(root.xpath('//crossword/Height')[0].attrib['v'])
    cols = int(root.xpath('//crossword/Width')[0].attrib['v'])
    xd = xdfile.xdfile()

    # add meta data
    for item in POSSIBLE_META_DATA:
        try:
            text = root.xpath('//crossword/' + item)[0].attrib['v']
            if text:
                xd.headers.append((item, unquote(text)))
        except:
            pass

    # add puzzle
    all_answers = root.xpath('//crossword/AllAnswer')[0].attrib['v']
    all_answers = all_answers.replace('-', xdfile.BLOCK_CHAR)
    index = 0
    while index < len(all_answers):
        row = all_answers[index:index+cols]
        xd.grid.append(u"".join(row))
        index += cols

    # add clues
    for clue_type in ('across', 'down'):
        for clue in root.xpath('//crossword/'+clue_type)[0].getchildren():
            number = int(clue.attrib['cn'])
            text = unquote(clue.attrib['c'].strip())
            solution = clue.attrib['a'].strip()
            xd.clues.append(((clue_type[0].upper(), number), text, solution))

    return xd

if __name__ == "__main__":
    xdfile.main_parse(parse_uxml)

