import re

from lxml import etree

from puzzle import Clue
from puzzle import Constants
from puzzle import Crossword
from scrapers import basescraper
import string


class latimes(basescraper):
    FILENAME_PREFIX = 'latimes'
    RAW_CONTENT_TYPE = 'xml'
    DAILY_PUZZLE_URL = 'http://cdn.games.arkadiumhosted.com/latimes/assets/DailyCrossword/la%s.xml'
    DATE_FORMAT = '%y%m%d'

    def build_crossword(self, content):
        ns = {
            'puzzle': 'http://crossword.info/xml/rectangular-puzzle'
        }
        content = content.replace("<b>", "**")
        content = content.replace("</b>", "**")
        content = content.replace("<i>", "//")
        content = content.replace("</i>", "//")
        content = content.replace("<em>", "//")
        content = content.replace("</em>", "//")
        content = content.replace("<u>", "__")
        content = content.replace("</u>", "__")
        root = etree.fromstring(content)

        # init crossword
        grid = root.xpath('//puzzle:crossword/puzzle:grid', namespaces=ns)[0]
        rows = int(grid.attrib['height'])
        cols = int(grid.attrib['width'])
        crossword = Crossword(rows, cols)

        # add meta data
        for metadata in root.xpath('//puzzle:metadata', namespaces=ns)[0]:
            text = metadata.text and metadata.text.strip()
            title = re.sub('\{[^\}]*\}', '', metadata.tag.title())
            if text:
                crossword.add_meta_data('%s: %s' %(title, text))

        # add puzzle
        puzzle = crossword.puzzle
        for cell in grid.xpath('./puzzle:cell', namespaces=ns):
            x = int(cell.attrib['x']) - 1
            y = int(cell.attrib['y']) - 1
            if 'solution' in cell.attrib:
                value = cell.attrib['solution']
            if 'type' in cell.attrib and cell.attrib['type'] == 'block':
                value = Constants.BLOCK_CHAR
            puzzle[y][x] = value
        crossword.set_puzzle(puzzle)

        # add clues
        word_map = {}
        for word in root.xpath('//puzzle:crossword/puzzle:word', namespaces=ns):
            word_map[word.attrib['id']] = (word.attrib['x'], word.attrib['y'])

        for clues in root.xpath('//puzzle:crossword/puzzle:clues', namespaces=ns):
            type = clues.xpath('./puzzle:title', namespaces=ns)[0]
            type = "".join(x for x in etree.tostring(type, method='text').upper() if x in string.uppercase)
            type = getattr(Constants, type)

            for clue in clues.xpath('./puzzle:clue', namespaces=ns):
                word_id = clue.attrib['word']
                number = int(clue.attrib['number'])
                text = "".join(clue.itertext()).encode('utf-8').strip()
                solution = self._get_solution(word_id, word_map, puzzle)
                crossword.add_clue(Clue(number, type, text, solution))

        return crossword

    def _get_solution(self, word_id, word_map, puzzle):
        def get_numbers_in_range(range_as_string, separator):
            start, end = (int(num) for num in range_as_string.split(separator))
            # reduce 1 to stick to a 0-based index list
            start = start - 1
            end = end - 1
            return range(start, end+1)

        x, y = word_map[word_id]
        word = ''
        if '-' in x:
            word = (puzzle[int(y)-1][i] for i in get_numbers_in_range(x, '-'))
        elif '-' in y:
            word = (puzzle[i][int(x)-1] for i in get_numbers_in_range(y, '-'))
        else:
            word = (puzzle[int(x)-1][int(y)-1])
        return ''.join(word)
