import re

from lxml import html

from constants import REBUS_SHORT_HANDS, REBUS_LONG_HANDS
from puzzle import Clue
from puzzle import Constants
from puzzle import Crossword
from scrapers import basescraper


class xwordinfo(basescraper):
    FILENAME_PREFIX = 'xwordinfo'
    RAW_CONTENT_TYPE = 'html'
    DAILY_PUZZLE_URL = 'http://www.xwordinfo.com/PS?date=%s'
    DATE_FORMAT = '%-m/%-d/%Y'

    PT_CLUE = re.compile(r'(\d+)\. (.*) :')
    SPLIT_REBUS_TITLES = "CRYPTOCROSSWORD TIC-TAC-TOE".split()

    def build_crossword(self, content):
        # replace quick mark-ups
        content = content.replace('<b>', '**')
        content = content.replace('</b>', '**')
        content = content.replace('<i>', '//')
        content = content.replace('</i>', '//')
        content = content.replace('<em>', '//')
        content = content.replace('</em>', '//')
        content = content.replace('<u>', '__')
        content = content.replace('</u>', '__')

        root = html.fromstring(content)

        special_type = ''
        rebus = {}
        rebus_order = []
        puzzle = []

        puzzle_table = root.cssselect('#CPHContent_PuzTable tr') or \
            root.cssselect('#PuzTable tr')
        for row in puzzle_table:
            row_data = []
            for cell in row.cssselect('td'):
                # check if the cell is special - with a shade or a circle
                cell_class = cell.get('class')
                cell_type = ''
                if cell_class == 'bigshade':
                    cell_type = 'GRAY'
                elif cell_class == 'bigcircle':
                    cell_type = 'CIRCLE'

                letter = cell.cssselect('div.letter')
                letter = (len(letter) and letter[0].text) or '.'

                # handle rebuses
                if letter == '.':
                    subst = cell.cssselect('div.subst')
                    subst = (len(subst) and subst[0].text) or ''
                    if not subst:
                        subst = cell.cssselect('div.subst')
                        if subst:
                            if title in splitRebusTitles:
                                subst = "/".join(list(subst[0].text))
                            else:
                                subs = subst[0].text

                    if subst:
                        if not subst in rebus:
                            if subst in REBUS_LONG_HANDS:
                                rebus_val = REBUS_LONG_HANDS[subst]
                                if rebus_val in REBUS_SHORT_HANDS:
                                    REBUS_SHORT_HANDS.remove(rebus_val)
                            else:
                                rebus_val = REBUS_SHORT_HANDS.pop()
                            rebus[subst] = rebus_val
                            rebus_order.append(subst)
                        letter = rebus[subst]

                if cell_type:
                    # the special cell's letter should be represented in lower case
                    letter = letter.lower()
                    if not special_type:
                        # hopefully there shouldn't be both shades and circles in
                        # the same puzzle - if that is the case, only the last value
                        # will be put up in the header
                        special_type = cell_type

                row_data.append(letter)
            puzzle.append(row_data)

        # init crossword
        rows = len(puzzle)
        cols = len(puzzle[0])
        crossword = Crossword(rows, cols)

        # add puzzle
        crossword.set_puzzle(puzzle)

        # add meta data
        title = root.cssselect('#CPHContent_TitleLabel')[0].text.strip()
        subtitle = ''
        try:
            subtitle = root.cssselect('#CPHContent_SubTitleLabel')[0].text.strip()
            subtitle = ' [%s]' %subtitle
        except:
            pass
        crossword.add_meta_data('Title: %s%s' %(title, subtitle))
        author = root.cssselect('#CPHContent_AuthorLabel')[0].text.strip()
        crossword.add_meta_data('Author: %s' %author)
        editor = root.cssselect('#CPHContent_EditorLabel')[0].text.strip()
        crossword.add_meta_data('Editor: %s' %editor)
        if len(rebus):
            rebus = ["%s=%s" %(rebus[x], x.upper()) for x in rebus_order]
            crossword.add_meta_data('Rebus: %s' %(','.join(rebus)))
        if special_type:
            crossword.add_meta_data('Special Type: %s' %special_type)

        # add clues
        across_clues = self._fetch_clues(Constants.ACROSS, root, rebus)
        down_clues = self._fetch_clues(Constants.DOWN, root, rebus)
        clues = across_clues + down_clues
        for clue in clues:
            crossword.add_clue(clue)

        return crossword

    def _fetch_clues(self, type, root, rebus):
        if type == Constants.ACROSS:
            css_identifier = '#CPHContent_AcrossClues'
        elif type == Constants.DOWN:
            css_identifier = '#CPHContent_DownClues'

        clues = []
        text = number = solution = None
        for content in root.cssselect(css_identifier)[0].itertext():
            content = content.strip()
            if text:
                # replace rebuses with appropriate identifiers (numbers)
                for item in rebus:
                    if item in content:
                        content = content.replace(item, str(index+1))

                solution = content
                clues.append(Clue(number, type, text, solution))
                text = number = solution = None
            else:
                match = re.match(xwordinfo.PT_CLUE, content)
                number = int(match.group(1))
                text = match.group(2)
        return clues
