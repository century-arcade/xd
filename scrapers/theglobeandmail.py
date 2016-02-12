from lxml import etree

from puzzle import Clue
from puzzle import Constants
from puzzle import Crossword
from scrapers import basescraper


class theglobeandmail(basescraper):
    RAW_CONTENT_TYPE = 'xml'
    DATE_FORMAT = '%y%m%d'

    POSSIBLE_META_DATA = ['Title', 'Author', 'Editor', 'Copyright', 'Category']

    def build_crossword(self, content):
        root = etree.fromstring(content)

        # init crossword
        rows = int(root.xpath('//crossword/Height')[0].attrib['v'])
        cols = int(root.xpath('//crossword/Width')[0].attrib['v'])
        crossword = Crossword(rows, cols)

        # add meta data
        for item in theglobeandmail.POSSIBLE_META_DATA:
            try:
                text = root.xpath('//crossword/' + item)[0].attrib['v']
                if text:
                    crossword.add_meta_data('%s: %s' %(item, text))
            except:
                pass

        # add puzzle
        puzzle = crossword.puzzle
        all_answers = root.xpath('//crossword/AllAnswer')[0].attrib['v']
        y = 0
        index = 0
        while index < len(all_answers):
            row = all_answers[index:index+cols]
            puzzle[y] = list(row)
            y += 1
            index += cols
        crossword.set_puzzle(puzzle)

        # add clues
        clue_types = ('across', 'down')
        for clue_type in clue_types:
            for clue in root.xpath('//crossword/'+clue_type)[0].getchildren():
                number = int(clue.attrib['cn'])
                text = clue.attrib['c'].strip()
                type = getattr(Constants, clue_type.upper())
                solution = clue.attrib['a'].strip()
                crossword.add_clue(Clue(number, type, text, solution))

        return crossword


class theglobeandmail_universal(theglobeandmail):
    FILENAME_PREFIX = 'theglobeandmail_universal'
    DAILY_PUZZLE_URL = 'http://v1.theglobeandmail.com/v5/content/puzzles/crossword_universal/source/fcx%s-data.xml'


class theglobeandmail_canadian(theglobeandmail):
    FILENAME_PREFIX = 'theglobeandmail_canadian'
    DAILY_PUZZLE_URL = 'http://v1.theglobeandmail.com/v5/content/puzzles/crossword_canadian/source/can%s-data.xml'
