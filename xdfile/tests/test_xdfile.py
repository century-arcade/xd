"""This is test_xdfile.py"""

import datetime

import xdfile as xdfile
from xdfile.xdfile import xdfile as XDFile

test_selection = 'nyt1955-01-01.xd'


def test_filename():
    fname = parse_pathname(test_selection).base
    assert fname == 'nyt1955-01-01'


def test_parse_date():
    date = xdfile.parse_date_from_filename(test_selection)
    assert isinstance(date, tuple)
    assert date[0] == 'nyt'
    assert isinstance(date[1], datetime.date)
    assert date[1].strftime('%a %b %d %Y') == 'Sat Jan 01 1955'


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
