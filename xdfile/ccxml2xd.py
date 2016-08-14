# -*- coding: utf-8 -*- 
#!/usr/bin/env python3

import string
import re
from lxml import etree
import xdfile
from xdfile.utils import escape, consecutive, xml_escape_table, rev_xml_escape_table, error


HEADER_RENAMES = {
    'Creator': 'Author'
}

# data is bytes()
def parse_ccxml(data, filename):
    content = data.decode('utf-8', errors='replace')
    content = escape(content, xml_escape_table)
    content = consecutive(content)
    content = re.sub(r'(=["]{2}([^"]+?)["]{2})+',r'="&quot;\2&quot;"', content) # Replace double quotes
    content_xml = content.encode('utf-8')

    ns = {
        'puzzle': 'http://crossword.info/xml/rectangular-puzzle'
    }
    try:
        root = etree.fromstring(content_xml)
    except Exception as e:
        error('Exception %s' % e)
        error(content)
        exit

    # init crossword
    grid = root.xpath('//puzzle:crossword/puzzle:grid', namespaces=ns)
    if not grid:
        return None

    grid = grid[0]
    rows = int(grid.attrib['height'])
    cols = int(grid.attrib['width'])

    xd = xdfile.xdfile('', filename)

    # add metadata
    for metadata in root.xpath('//puzzle:metadata', namespaces=ns)[0]:
        text = metadata.text and metadata.text.strip()
        title = re.sub('\{[^\}]*\}', '', metadata.tag.title())
        title = escape(title, rev_xml_escape_table)
        if text:
            text = escape(text, rev_xml_escape_table)
            xd.set_header(HEADER_RENAMES.get(title, title), text)

    # add puzzle
    puzzle = []
    for i in range(rows):
        puzzle.append([" "] * cols)

    for cell in grid.xpath('./puzzle:cell', namespaces=ns):
        x = int(cell.attrib['x']) - 1
        y = int(cell.attrib['y']) - 1
        if 'solution' in cell.attrib:
            value = cell.attrib['solution']
        if 'type' in cell.attrib and cell.attrib['type'] == 'block':
            value = xdfile.BLOCK_CHAR
        puzzle[y][x] = value

    xd.grid = ["".join(row) for row in puzzle]

    # add clues
    word_map = {}
    for word in root.xpath('//puzzle:crossword/puzzle:word', namespaces=ns):
        word_map[word.attrib['id']] = (word.attrib['x'], word.attrib['y'])

    for clues in root.xpath('//puzzle:crossword/puzzle:clues', namespaces=ns):
        type = clues.xpath('./puzzle:title', namespaces=ns)[0]
        type = "".join(chr(x) for x in etree.tostring(type, method='text').upper() if chr(x) in string.ascii_uppercase)
        type = type[0]

        for clue in clues.xpath('./puzzle:clue', namespaces=ns):
            word_id = clue.attrib['word']
            number = int(clue.attrib['number'])
            text = "|".join(clue.itertext()).strip()
            text = escape(text, rev_xml_escape_table)
            solution = get_solution(word_id, word_map, puzzle)
            xd.clues.append(((type, number), text, solution))

    return xd


def get_solution(word_id, word_map, puzzle):
    def get_numbers_in_range(range_as_string, separator):
        start, end = (int(num) for num in range_as_string.split(separator))
        # reduce 1 to stick to a 0-based index list
        start = start - 1
        end = end - 1
        return list(range(start, end + 1))

    x, y = word_map[word_id]
    word = ''
    if '-' in x:
        word = (puzzle[int(y) - 1][i] for i in get_numbers_in_range(x, '-'))
    elif '-' in y:
        word = (puzzle[i][int(x) - 1] for i in get_numbers_in_range(y, '-'))
    else:
        word = (puzzle[int(x) - 1][int(y) - 1])
    return ''.join(word)

if __name__ == "__main__":
    xdfile.main_parse(parse_ccxml)
