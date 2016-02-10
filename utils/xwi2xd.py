#!/usr/bin/python
# -*- coding: utf-8 -*-

# pip install lxml

import re
import codecs

from os import linesep as EOL
from lxml import html, etree
from datetime import date, datetime, timedelta
import sys
import os
import os.path

BLOCK_CHAR = '#'
ANSWER_SEP = '~'

splitRebusTitles = "CRYPTOCROSSWORD TIC-TAC-TOE".split()

rebus_longhands = {
        'NINE': '9',
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
#        'DASH': '-',
#        'DOT': '●',
}

def stringify_children(node):
    s = node.text
    if s is None:
        s = ''
    for child in node:
        s += etree.tostring(child, encoding='unicode')
    return s

def html_to_xd(html_content):
    rebus_shorthands = list(u"♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠Фθиλπφя+&%$@?*zyxwvutsrqponmlkjihgfedcba0987654321")

    def format_clue(wholeclue):
        idx_answer = wholeclue.rfind(':') + 1
        answer = wholeclue[idx_answer:].strip()
        clue = wholeclue[:idx_answer]
        clue = clue[:-1].strip()
        assert clue, wholeclue
        if clue[-1] == "`": # a weird backtick
            clue = clue[:-1]
        clue.replace("`", "'")
        return "%s %s %s" % (clue.strip(), ANSWER_SEP, answer)

    def fetch_clues(css_identifier, clue_prefix):
        all_clues = []

        clue = ""
        for L in doc.cssselect(css_identifier)[0].itertext():
            if len(L) == 0: continue
            elif re.match(r'(\d+)\. .*', L):
                if clue:
                    all_clues.append(clue_prefix + format_clue(clue))

                clue = L
            else:
                clue += " " + L

        all_clues.append(clue_prefix + format_clue(clue))
        return all_clues

    if "CPHContent_" in html_content:
        xwiprefix = '#CPHContent_'
    else:
        xwiprefix = '#'

    doc = html.fromstring(html_content)

    # additional headers
    rebus = { }
    rebus_order = [ ]
    special_type = ''

    # get crossword info
    title = doc.cssselect(xwiprefix + 'TitleLabel')[0].text.strip()
    try:
        subtitle = doc.cssselect(xwiprefix + 'SubTitleLabel')[0].text.strip()
    except:
        subtitle = ""
    author = doc.cssselect(xwiprefix + 'AuthorLabel')[0].text.strip()
    editor = doc.cssselect(xwiprefix + 'EditorLabel')[0].text.strip()
    try:
        notepad = stringify_children(doc.cssselect(xwiprefix + 'NotepadDiv')[0])
    except:
        notepad = ""

    notepad = notepad.replace("<br/>", "\n")
    notepad = notepad.replace("<b>Notepad:</b>", "\n")
    notepad = notepad.replace("&#13;", "\n")
    notepad = notepad.strip()

    nShortsUsed = 0


    # capture the puzzle as it is
    puzzle = []
    puztable = doc.cssselect(xwiprefix + 'PuzTable tr')
    if not puztable:
        puztable = doc.cssselect('#PuzTable tr') # new format

    for row in puztable:
        row_data = []
        for cell in row.cssselect('td'):
            # check if the cell is special - with a shade or a circle
            cell_class = cell.get('class')
            cell_type = ''
            if cell_class == 'bigshade':
                cell_type = 'shaded'
            elif cell_class == 'bigcircle':
                cell_type = 'circle'

            letter = cell.cssselect('div.letter')
            letter = (len(letter) and letter[0].text) or BLOCK_CHAR

            # handle rebuses
            if letter == BLOCK_CHAR:
                subst = cell.cssselect('div.subst2')
                subst = (len(subst) and subst[0].text) or ''
                if not subst:
                    subst = cell.cssselect('div.subst')
                    if subst:
                        if title in splitRebusTitles:
                            subst = "/".join(list(subst[0].text))
                        else:
                            subst = subst[0].text
                    else:
                        subst = ''

                if subst:
                    if not subst in rebus:
                        if subst in rebus_longhands:
                            rebus[subst] = rebus_longhands[subst]
                            rebus_order.append(subst)
                            if rebus_longhands[subst] in rebus_shorthands:
                                rebus_shorthands.remove(rebus_longhands[subst]) 
                        else:
                            rebus[subst] = rebus_shorthands.pop()
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

    # capture the clues
    try:
        down = fetch_clues(xwiprefix + 'DownClues', 'D')
        across = fetch_clues(xwiprefix + 'AcrossClues', 'A')
    except:
        across = fetch_clues(xwiprefix + 'AcrossClues', '')  # uniclue puzzles
        down = None
    # build XD content with the data we have
    xd_content = u''

    xd_content += 'Title: %s' % title
    if subtitle:
        xd_content += " [%s]" % subtitle

    xd_content += EOL
    xd_content += 'Author: %s' % author + EOL
    xd_content += 'Editor: %s' % editor + EOL
    if len(rebus):
        rebus = ["%s=%s" %(rebus[k],k.upper()) for k in rebus_order ]
        xd_content += 'Rebus: %s' %(','.join(rebus)) + EOL
    if special_type:
        xd_content += 'Special: %s' % special_type + EOL

    xd_content += EOL + EOL # two EOLs state change to grid
    xd_content += EOL.join([" " + ''.join(row) for row in puzzle]) + EOL
    xd_content += EOL + EOL # two EOLs change state to clues
    xd_content += EOL.join(across) + EOL
    xd_content += EOL
    if down:
        xd_content += EOL.join(down) + EOL

    xd_content += EOL

    if notepad:
        xd_content += EOL + EOL # change state to notepad 
        xd_content += "---" + EOL + notepad

    return xd_content

# parse and save puzzles in XD format files
def translate_bulk():
    import zipfile

    srczf = zipfile.ZipFile(sys.argv[1], 'r')
    outzf = zipfile.ZipFile(sys.argv[2], 'w', zipfile.ZIP_DEFLATED)

    all_xd = { }
    for zi in srczf.infolist():
        m = re.search(r'([a-z]+)((\d{4})-(\d{2})-(\d{2})).html', zi.filename)
        if m:
            tag, datestr, year, month, day = m.groups()
            outzi = zipfile.ZipInfo()
            outzi.date_time = [ max(int(year), 1980), int(month), int(day), 12, 0, 0 ]
            outzi.filename = "crosswords-%s/%s/%s.xd" % (tag, year, datestr)
            outzi.external_attr = 0444 << 16L
            print "\r%s" % outzi.filename

            xd_data = codecs.decode(srczf.read(zi), 'utf-8')
            xd_data = html_to_xd(xd_data)
            outzi.file_size = len(xd_data)
            outzi.compress_type = zipfile.ZIP_DEFLATED
            outzi.volume = 0
            outzf.writestr(outzi, codecs.encode(xd_data, 'utf-8'))

    print


def translate_one():
    src, dest = sys.argv[1:]

    print "Creating... " + dest
    xd_content = html_to_xd(codecs.open(src, "r", "utf-8").read())

    # write out the XD content to a file
    with codecs.open(dest, 'w', "utf-8") as local_file:
        local_file.write(xd_content)

#translate_bulk()
translate_one()

