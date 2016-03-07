#!/usr/bin/env python

import re
from urllib import unquote
from lxml import etree

import xdfile

def udecode(s):
    t = unquote(s)
    try:
        return unicode(t.decode("utf-8"))
    except:
        return unicode(t)

def parse_uxml(content):
    POSSIBLE_META_DATA = ['Title', 'Author', 'Editor', 'Copyright', 'Category']

    try:
        content = content.decode("utf-8")
    except:
        try:
            content = content.decode("cp1252")
        except:
            pass # last ditch effort, just try the original string

    content = content.replace("&", "&amp;")
    content = content.replace('"<"', '"&lt;"')
    content = content.replace("''", '&quot;')
    content = content.replace("\x12", "'")  # ^R seems to be '
    content = content.replace("\x05", "'")  # ^E seems to be junk

    content = re.sub(r'=""(\S)', r'="&quot;\1', content) # one case has c=""foo"".  sheesh
    content = re.sub(r'(\.)""', r'\1&quot;"', content)

    try:
        root = etree.fromstring(content)
    except:
        xml = re.search(r"<(\w+).*?</\1>", content, flags=re.DOTALL).group()
        root = etree.fromstring(xml)

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
            text = udecode(clue.attrib['c'].strip())
            solution = clue.attrib['a'].strip()
            xd.clues.append(((clue_type[0].upper(), number), text, solution))

    return xd

if __name__ == "__main__":
    xdfile.main_parse(parse_uxml)

