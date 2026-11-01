# -*- coding: utf-8 -*-
"""Crossword Compiler XML -> .xd: rebus, circles, notes, blank and unnumbered clues."""

from xdfile.ccxml2xd import parse_ccxml

NS = 'xmlns="http://crossword.info/xml/crossword-compiler"'
PNS = 'xmlns="http://crossword.info/xml/rectangular-puzzle"'


def ccxml(cells, words, across, down, metadata='', root_attrs=NS, extra=''):
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<crossword-compiler %s><rectangular-puzzle %s alphabet="ABC">'
            '<metadata>%s</metadata><crossword><grid width="3" height="3">%s</grid>'
            '%s<clues ordering="normal"><title><b>Across</b></title>%s</clues>'
            '<clues ordering="normal"><title><b>Down</b></title>%s</clues>%s'
            '</crossword></rectangular-puzzle></crossword-compiler>'
            % (root_attrs, PNS, metadata, cells, words, across, down, extra)).encode('utf-8')


# C A T
# A # O
# B E E   (with a rebus TO in the top right... no: keep letters, mark rebus below)
CELLS = ('<cell x="1" y="1" solution="C" number="1"/><cell x="2" y="1" solution="A" number="2"/>'
         '<cell x="3" y="1" solution="T" number="2" background-shape="circle"/>'
         '<cell x="1" y="2" solution="A"/><cell x="2" y="2" type="block"/>'
         '<cell x="3" y="2" solution="O"/>'
         '<cell x="1" y="3" solution="B" number="3"/><cell x="2" y="3" solution="E"/>'
         '<cell x="3" y="3" solution="E" background-shape="circle"/>')
WORDS = ('<word id="1" x="1-3" y="1"/><word id="2" x="1-3" y="3"/>'
         '<word id="3" x="1" y="1-3"/><word id="4" x="3" y="1-3"/>')
ACROSS = ('<clue word="1" number="1" format="3">Feline <i>pet</i></clue>'
          '<clue word="2" number="3" format="3">Honey maker</clue>')
DOWN = ('<clue word="3" number="1" format="3">Taxi&#39;s cousin &#60;b&#62;&#60;/b&#62;</clue>'
        '<clue word="4" number="2" format="3">&#60;b&#62;&#60;/b&#62;</clue>')
META = ('<title>Tiny</title><creator>Jane Doe (edited by John Roe)</creator>'
        '<copyright>© 2026 Test</copyright>'
        '<description>First paragraph…\n\nSecond &#34;paragraph&#34;</description>')


def test_headers_notes_markup_and_circles():
    xd = parse_ccxml(ccxml(CELLS, WORDS, ACROSS, DOWN, META), 'tiny.xml')
    assert xd.get_header('Title') == 'Tiny'
    assert xd.get_header('Author') == 'Jane Doe'
    assert xd.get_header('Editor') == 'John Roe'
    assert xd.get_header('Special') == 'circle'
    assert xd.grid == ['CAt', 'A#O', 'BEe']
    assert xd.notes == 'First paragraph...\n\nSecond "paragraph"\n'
    clues = {pos: (text, ans) for pos, text, ans in xd.clues}
    assert clues[('A', 1)] == ('Feline pet', 'CAT')
    assert clues[('D', 1)] == ("Taxi's cousin", 'CAB')
    assert clues[("D", 2)] == ('', 'TOE')  # blank clue, published that way
    assert 'D2. ~ TOE' in xd.to_unicode()


def test_rebus_keys_avoid_circled_letters():
    cells = CELLS.replace('solution="O"', 'solution="ON" background-shape="circle"')
    xd = parse_ccxml(ccxml(cells, WORDS, ACROSS, DOWN, META), 'tiny.xml')
    # 't' and 'e' are circled letters, so the circled rebus takes 'a'
    assert xd.get_header('Rebus') == 'a=ON'
    assert xd.grid[1] == 'A#a'
    clues = {pos: ans for pos, _t, ans in xd.clues}
    assert clues[("D", 2)] == 'TONE'
    plain = CELLS.replace('solution="O"', 'solution="ON"')
    xd = parse_ccxml(ccxml(plain, WORDS, ACROSS, DOWN, META), 'tiny.xml')
    assert xd.get_header('Rebus') == '1=ON'
    assert xd.grid[1] == 'A#1'


def test_unnumbered_clues_get_standard_numbers():
    across = ACROSS.replace('number="1"', 'number=""').replace('number="3"', 'number=""')
    down = DOWN.replace('number="1"', 'number=""').replace('number="2"', 'number=""')
    xd = parse_ccxml(ccxml(CELLS, WORDS, across, down, META), 'tiny.xml')
    assert sorted(pos for pos, _t, _a in xd.clues) == [("A", 1), ("A", 3), ("D", 1), ("D", 2)]
    assert 'published without clue numbers' in xd.notes


def test_black_squares_with_letters_go_to_notes():
    cells = CELLS.replace('<cell x="2" y="2" type="block"/>',
                          '<cell x="2" y="2" solution="Z" number="0" background-color="#000000"/>')
    xd = parse_ccxml(ccxml(cells, WORDS, ACROSS, DOWN, META), 'tiny.xml')
    assert xd.grid[1] == 'A#O'
    assert 'row 2, column 2: Z' in xd.notes


def test_mojibake_and_applet_root():
    meta = META.replace("©", "Â©")  # UTF-8 read as latin-1
    xd = parse_ccxml(ccxml(CELLS, WORDS, ACROSS, DOWN, meta, root_attrs=''), 'tiny.xml')
    assert xd.get_header('Copyright') == '© 2026 Test'


def test_variety_puzzle_is_rejected():
    across = ACROSS
    down = DOWN
    data = ccxml(CELLS, WORDS, across, down, META).replace(b'<b>Down</b>', b'<b>Bands</b>')
    assert parse_ccxml(data, 'bands.xml') is None
