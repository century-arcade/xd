#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from lxml import html, etree
from datetime import datetime
from xdfile.utils import info, debug, error
import xdfile

SPLIT_REBUS_TITLES = "CRYPTOCROSSWORD TIC-TAC-TOE".split()

class XWordInfoParseError(Exception):
    pass

# content is unicode()
def parse_xwordinfo(content, filename):
    content = content.decode('utf-8')

    REBUS_LONG_HANDS = {'NINE': '9',
                        'EIGHT': '8',
                        'SEVEN': '7',
                        'SIX': '6',
                        'FIVE': '5',
                        'FOUR': '4',
                        'THREE': '3',
                        'TWO': '2',
                        'ONE': '1',
                        'ZERO': '0',
                        'AUGHT': '0',
                        'AMPERSAND': '&',
                        'AND': '&',
                        'ASTERISK': '*',
                        'PERCENT': '%',
                        'STAR': '*',
                        'AT': '@',
                        'DOLLAR': '$',
                        'PLUS': '+',
                        'CENT': 'c',
                        # 'DASH': '-',
                        # 'DOT': '●'
                        }
    rsh = 'zyxwvutsrqponmlkjihgfedcba♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠Фθиλπφя+&%$@?*0987654321'
    REBUS_SHORT_HANDS = list(rsh)

    content = content.replace("<b>", "{*")
    content = content.replace("</b>", "*}")
    content = content.replace("<i>", "{/")
    content = content.replace("</i>", "/}")
    content = content.replace("<em>", "{/")
    content = content.replace("</em>", "/}")
    content = content.replace("<u>", "{_")
    content = content.replace("</u>", "_}")
    content = content.replace("<strike>", "{-")
    content = content.replace("</strike>", "-}")
    content = content.replace("’", "'")
    content = content.replace('“', '"')
    # content = content.replace('–', '-')

    if "CPHContent_" in content:
        xwiprefix = '#CPHContent_'
    else:
        xwiprefix = '#'

    root = html.fromstring(content)

    ## debug("ROOT: %s" % root)

    special_type = ''
    rebus = {}
    rebus_order = []

    xd = xdfile.xdfile('', filename)

    # get crossword info
    title = root.cssselect('#PuzTitle')[0].text.strip()
    try:
        subtitle = root.cssselect(xwiprefix + 'SubTitle')[0].text.strip()
        subtitle = ' [%s]' % subtitle
    except:
        subtitle = ""

    author = root.cssselect('.aegrid div')[1].text.strip()
    editor = root.cssselect('.aegrid div')[3].text.strip()
    
    copyright = root.cssselect(xwiprefix + 'Copyright')[0].text.strip()

    xd.set_header("Title", '%s%s' % (title, subtitle))
    xd.set_header("Author", author)
    xd.set_header("Editor", editor)
    xd.set_header("Copyright", copyright)

    # nyt title normally has date as e.g. January 1, 2020
    date_re = "(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}"
    try:
        m = re.search(date_re, subtitle if subtitle else title)
        date_string = m.group(0)
        date = datetime.strptime(date_string, "%B %d, %Y")
        xd.set_header("Date", date.strftime("%Y-%m-%d"))
    except:
        pass

    _process_notes(xd, xwiprefix, root) # add header for notes, if any

    puzzle_table = root.cssselect(xwiprefix + 'PuzTable tr') or root.cssselect('#PuzTable tr')

    for row in puzzle_table:
        row_data = ""
        for cell in row.cssselect('td'):
            # check if the cell is special - with a shade or a circle
            cell_class = cell.get('class')
            cell_type = ''
            if cell_class == 'shade':
                cell_type = 'shaded'
            elif cell_class == 'bigcircle':
                cell_type = 'circle'

            letter = cell.cssselect('div.letter')
            letter = (len(letter) and letter[0].text) or xdfile.BLOCK_CHAR

            # handle rebuses
            if letter == xdfile.BLOCK_CHAR:
                subst = cell.cssselect('div.subst2')
                subst = (len(subst) and subst[0].text) or ''
                if not subst:
                    subst = cell.cssselect('div.subst')
                    if subst:
                        if title in SPLIT_REBUS_TITLES:
                            subst = "/".join(list(subst[0].text))
                        else:
                            subst = subst[0].text
                    else: # check if color rebus
                        cell_string = etree.tostring(cell).decode('utf-8')
                        m = re.search("background-color:([A-Z]+);", cell_string)
                        if m:
                            subst = m.group(1)
                        else:
                            subst = ''

                if subst:
                    if subst not in rebus:
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

            row_data += letter
        xd.grid.append(row_data)

    if len(rebus):
        rebus = ["%s=%s" % (rebus[x], x.upper()) for x in rebus_order]
        xd.set_header("Rebus", ','.join(rebus))
    if special_type:
        xd.set_header("Special", special_type)

    across_div = root.cssselect('#ACluesPan') or root.cssselect(xwiprefix + 'ACluesPan')
    down_div = root.cssselect('#DCluesPan') or root.cssselect(xwiprefix + 'DCluesPan')

    if across_div and down_div: # normal puzzle
        _process_clues(xd, 'A', across_div) # add across clues
        _process_clues(xd, 'D', down_div) # add down clues
    elif across_div: # uniclue puzzle?
        _process_uniclues(xd, across_div)
    else: 
        raise XWordInfoParseError("No clue divs found.")

    return xd

def _process_notes(xd, xwiprefix, root):
    note_div = root.cssselect('#notepad') or root.cssselect(xwiprefix + 'NotepadDiv')
    if note_div:
        note_div_string = etree.tostring(note_div[0]).decode('utf-8')
        note_div_string = note_div_string.replace("<br/>", "\n")
        note_div_string = note_div_string.replace("{*Notepad:*}", "\n")
        note_div_string = note_div_string.replace("&#13;", "\n")
        note_div_string = note_div_string.strip()
        note_div = html.fromstring(note_div_string)
        note_text = note_div.text_content()
        note_text = note_text.replace("\n", "   ")
        note_text = note_text.strip()
        xd.set_header("Notes", note_text)
    elif root.cssselect(xwiprefix + 'UnicluePan'):
        note_text = ("This was published as a uniclue puzzle in print. " +
        "All the clues appear in a single list, combining Across and Down. " + 
        "When two answers share a number, they also share a clue.")
        xd.set_header("Notes", note_text) 

def _process_clues(xd, clueprefix, clues_div):
    error_text = 'Parsing %s clues failed. ' % ('Across' if clueprefix == 'A' else 'Down')
    numclue_divs = clues_div[0].cssselect('.numclue div')
    if len(numclue_divs) % 2 != 0:
        raise XWordInfoParseError(error_text + 
            'Either the number of numbers does not match the ' +
            'number of clues, or there are additional unknown divs.')
    for i in range(0, len(numclue_divs), 2):
        num = numclue_divs[i].text
        clue_div = numclue_divs[i + 1]
        clue_end = clue_div.text.rfind(' :')
        if clue_end < 0:
            raise XWordInfoParseError(error_text + 
                'Malformed clue for number %s.' % num)
        clue = clue_div.text[:clue_end]
        anchor = clue_div.cssselect('a')
        if len(anchor) != 1:
            raise XWordInfoParseError(error_text + 
                'Not exactly one anchor in clue div for number %s.' % num)
        else:
            answer = anchor[0].text
            xd.clues.append(((clueprefix, num), clue, answer))

def _process_uniclues(xd, clues_div):
    error_text = 'Parsing suspected uniclues failed. '
    grid_answers = xd.iteranswers()
    down_clues = []
    numclue_divs = clues_div[0].cssselect('.numclue div')
    if len(numclue_divs) % 2 != 0:
        raise XWordInfoParseError(error_text + 
            'Either the number of numbers does not match the ' +
            'number of clues, or there are additional unknown divs.')
    for i in range(0, len(numclue_divs), 2):
        num = numclue_divs[i].text
        clue_div = numclue_divs[i + 1]
        clue_end = clue_div.text.rfind(' :')
        if clue_end < 0:
            raise XWordInfoParseError(error_text + 
                'Malformed clue for number %s.' % num)
        clue = clue_div.text[:clue_end]
        anchor = clue_div.cssselect('a')
        if not anchor or len(anchor) > 2:
            raise XWordInfoParseError(error_text + 
                'Neither 1 nor 2 anchors in clue div for number %s.' % num)
        for a in anchor:
            answer = a.text
            direction, grid_num, _ = next(grid_answers)
            if direction == 'A':
                xd.clues.append(((direction, grid_num), clue, answer))
            else:
                down_clues.append(((direction, grid_num), clue, answer))
    for clue in down_clues:
        xd.clues.append(clue)

if __name__ == "__main__":
    import sys
    from .utils import find_files
    for fn, contents in find_files(*sys.argv[1:]):
        xd = parse_xwordinfo(contents, fn)
        print("--- %s ---" % fn)
        print(xd.to_unicode())
