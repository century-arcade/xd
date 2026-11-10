"""This is test_xdfile.py"""

import datetime

from xdfile.utils import parse_pathname, parse_date_from_filename, parse_pubid, dated_xdid
from xdfile.xdfile import xdfile as XDFile

test_selection = 'nyt1955-01-01.xd'


def test_filename():
    base = parse_pathname(test_selection).base
    assert base == 'nyt1955-01-01'


def test_parse_date():
    date = parse_date_from_filename(test_selection)
    assert isinstance(date, datetime.date)
    assert date.strftime('%a %b %d %Y') == 'Sat Jan 01 1955'


def test_parse_pubid():
    pubid = parse_pubid(test_selection)
    assert pubid == 'nyt'


def test_parse_pubid_with_digits():
    # xdids and .xd files follow the xdid forms, so a pubid may hold digits
    assert parse_pubid('club72-0001') == 'club72'
    assert parse_pubid('indie/croce/club72-0001.xd') == 'club72'
    assert parse_pubid('7xw2021-01-01.xd') == '7xw'
    assert parse_pubid('tpfa4-001') == 'tpfa4'
    assert parse_pubid('nytpack-16023.xd') == 'nytpack'
    assert parse_pubid('nytsp2006-02-03.xd.stub') == 'nytsp'
    assert parse_pubid('lat2019-10-11a.xd') == 'lat'
    assert parse_pubid('beq-0001') == 'beq'
    assert parse_pubid('nediger-219_5.xd') == 'nediger'
    assert parse_pubid('cc1992-av09.xd') == 'cc'            # year and issue
    assert parse_pubid('bg-unshelved-0a1b2c-name.xd') == 'bg'


def test_pubid_ending_in_digit_takes_a_hyphen():
    # ... before a date too, so even a pubid that ends in a year is readable
    assert parse_pubid('club72-2020-01-01.xd') == 'club72'
    assert parse_pubid('tpfa2024-2025-03-01') == 'tpfa2024'
    assert parse_pubid('tpfa2024-001.xd') == 'tpfa2024'
    assert parse_pubid('tpfa2024-unshelved-0a1b2c-name.xd') == 'tpfa2024'
    assert parse_pubid('club722015-06-01.xd') == 'club72'      # older form, no hyphen
    assert dated_xdid('nyt', '1955-01-01') == 'nyt1955-01-01'
    assert dated_xdid('7xw', '2021-01-01') == '7xw2021-01-01'
    assert dated_xdid('club72', '2020-01-01') == 'club72-2020-01-01'
    xd = XDFile('Title: t\n\n\nA\n\n\nA1. c ~ A\n', 'club72-2020-01-01.xd')
    assert xd.date() == '2020-01-01'
    assert xd.xdid() == 'club72-2020-01-01'


def test_parse_pubid_source_filenames():
    # a source file's name is only a hint: digits after the letters aren't the pubid
    assert parse_pubid('usun230101-data.xml') == 'usun'
    assert parse_pubid('nyt161225.puz') == 'nyt'
    assert parse_pubid('ss1-2.puz') == 'ss'
    assert parse_pubid('wsj2020-01-01.puz') == 'wsj'


SAMPLE_XD = """\
Title: Test Puzzle
Author: Test Author
Date: 2024-01-01


ABC
D#E
FGH


A1. First across ~ ABC
A3. Second across ~ FGH

D1. First down ~ ADF
D2. Second down ~ CE
D3. Third down ~ BEH
"""


def test_no_blank_clue_on_roundtrip():
    """Parsing and re-emitting an .xd file should not add blank clues."""
    xd = XDFile(SAMPLE_XD, filename='test2024-01-01.xd')
    for pos, clue, answer in xd.clues:
        assert pos != ('', ''), "Blank clue entry should not be added during parsing"
        assert answer != '', "Every clue should have an answer"


def test_roundtrip_stable():
    """Parsing and re-emitting an .xd file should produce identical output."""
    xd = XDFile(SAMPLE_XD, filename='test2024-01-01.xd')
    output = xd.to_unicode()
    xd2 = XDFile(output, filename='test2024-01-01.xd')
    output2 = xd2.to_unicode()
    assert output == output2, "Round-trip should be stable"


def test_to_unicode_collapses_newlines_in_clues():
    """to_unicode() must collapse newlines in clue text so output is valid .xd."""
    xd = XDFile(SAMPLE_XD, filename='test2024-01-01.xd')
    # Inject a clue with embedded newlines (simulating converter output)
    xd.clues[0] = (('A', 1), '"He got up in his rings\nand fancy ___"', 'ABC')
    output = xd.to_unicode()
    for line in output.splitlines():
        if line.startswith('A1.'):
            assert 'rings and fancy' in line
            assert '\n' not in line
            break
    else:
        assert False, "A1 clue not found in output"
    # Verify the output parses cleanly
    xd2 = XDFile(output, filename='test2024-01-01.xd')
    assert xd2.get_answer('A1') == 'ABC'


def test_number_slug():
    from xdfile.xdfile import number_slug
    assert number_slug('7') == '007'
    assert number_slug(1234) == '1234'
    assert number_slug('219.5') == '219_5'
    assert number_slug('12-B') == '12_B'


def test_xdid_non_integer_number():
    xd = XDFile('Title: T\nNumber: 219.5\n\n\nAB\nCD\n\n\nA1. x ~ AB\n',
                'gxd/indie/nediger/nediger-219_5.xd')
    assert xd.xdid() == 'nediger-219_5'
