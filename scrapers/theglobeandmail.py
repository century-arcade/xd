from lxml import etree

from crossword import Clue
from crossword import Constants
from crossword import Crossword
from utils import URLUtils
from utils import DateUtils
from errors import ContentDownloadError
from errors import NoCrosswordError


class theglobeandmail(object):
    FILENAME_PREFIX = 'theglobeandmail'
    RAW_CONTENT_TYPE = 'xml'
    DAILY_PUZZLE_URL = 'http://v1.theglobeandmail.com/v5/content/puzzles/crossword_canadian/source/can%s-data.xml'
    DATE_FORMAT = '%y%m%d'

    def get_content(self, date):
        date = DateUtils.to_string(date, theglobeandmail.DATE_FORMAT)
        url = theglobeandmail.DAILY_PUZZLE_URL %date
        try:
            content = URLUtils.get_content(url)
        except ContentDownloadError:
            raise NoCrosswordError('Date: %s; URL: %s' %(date, url))
        return content

    def build_crossword(self, content):
        root = etree.fromstring(content)

        # init crossword
        rows = int(root.xpath('//crossword/Height')[0].attrib['v'])
        cols = int(root.xpath('//crossword/Width')[0].attrib['v'])
        crossword = Crossword(rows, cols)

        # add meta data
        title = root.xpath('//crossword/Title')[0].attrib['v']
        crossword.add_meta_data('%s: %s' %('Title', title))
        author = root.xpath('//crossword/Author')[0].attrib['v']
        crossword.add_meta_data('%s: %s' %('Author', author))

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
        for clue in root.xpath('//crossword/across')[0].getchildren():
            number = int(clue.attrib['cn'])
            text = clue.attrib['c']
            solution = clue.attrib['a']
            crossword.add_clue(Clue(number, Constants.ACROSS, text, solution))
        for clue in root.xpath('//crossword/down')[0].getchildren():
            number = int(clue.attrib['cn'])
            text = clue.attrib['c']
            solution = clue.attrib['a']
            crossword.add_clue(Clue(number, Constants.DOWN, text, solution))

        return crossword
