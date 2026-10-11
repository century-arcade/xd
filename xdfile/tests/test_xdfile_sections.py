"""Explicit `## Section` headings in .xd files (spec 2.0+, v4 draft)."""

from xdfile.xdfile import xdfile as XDFile

FN = 'test2024-01-01.xd'

GRID = ['ABC', 'D#E', 'FGH']
CLUES = [
    (('A', 1), 'First across', 'ABC'),
    (('A', 3), 'Second across', 'FGH'),
    (('D', 1), 'First down', 'ADF'),
    (('D', 2), 'Second down', 'CE'),
    (('D', 3), 'Third down', 'BEH'),
]

HEADINGLESS = """\
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


Some notes here.
"""

METADATA = """\
Title: Test Puzzle
Author: Test Author
Date: 2024-01-01
"""

GRID_TEXT = """\
ABC
D#E
FGH
"""

CLUES_TEXT = """\
A1. First across ~ ABC
A3. Second across ~ FGH

D1. First down ~ ADF
D2. Second down ~ CE
D3. Third down ~ BEH
"""

DESIGN_TEXT = """\
O { background: circle }
S { background: shaded }

O..
.#S
..O
"""


def parse(text):
    return XDFile(text, filename=FN)


def assert_standard(xd):
    assert xd.get_header('Title') == 'Test Puzzle'
    assert xd.get_header('Author') == 'Test Author'
    assert xd.get_header('Date') == '2024-01-01'
    assert xd.grid == GRID
    assert xd.clues == CLUES


def test_headingless_unchanged():
    xd = parse(HEADINGLESS)
    assert_standard(xd)
    assert xd.notes == 'Some notes here.\n'
    assert xd.design == ''
    # no design section: output stays in the headingless form
    assert not any(line.startswith('##') for line in xd.to_unicode().splitlines())
    assert parse(xd.to_unicode()).to_unicode() == xd.to_unicode()


def test_headings_canonical_order():
    text = ("## Metadata\n\n" + METADATA + "\n## Grid\n\n" + GRID_TEXT +
            "\n## Clues\n\n" + CLUES_TEXT)
    xd = parse(text)
    assert_standard(xd)
    assert xd.notes == ''
    assert xd.design == ''


def test_headings_any_case():
    text = ("## METADATA\n" + METADATA + "##  grid\n" + GRID_TEXT +
            "## cLuEs\n" + CLUES_TEXT)
    assert_standard(parse(text))


def test_headings_any_order_and_blank_lines_ignored():
    # single blank lines inside sections and between them don't matter
    text = ("## Clues\n" + CLUES_TEXT + "\n\n\n## Grid\n" + GRID_TEXT +
            "\n\n## Metadata\n\nTitle: Test Puzzle\n\n\nAuthor: Test Author\nDate: 2024-01-01\n")
    assert_standard(parse(text))


def test_headings_indented():
    text = ("  ## Metadata\n" + METADATA + "    ## Grid\n" + GRID_TEXT +
            "\t## Clues\n" + CLUES_TEXT)
    assert_standard(parse(text))


def test_design_section_kept_raw():
    text = ("## Metadata\n" + METADATA + "\n## Grid\n" + GRID_TEXT +
            "\n## Clues\n" + CLUES_TEXT + "\n## Design\n\n" + DESIGN_TEXT + "\n\n")
    xd = parse(text)
    assert_standard(xd)
    assert xd.design == DESIGN_TEXT


def test_design_roundtrip_writes_headings():
    text = ("## Design\n" + DESIGN_TEXT + "## Metadata\n" + METADATA +
            "## Clues\n" + CLUES_TEXT + "## Grid\n" + GRID_TEXT +
            "## Notes\nA note.\n")
    xd = parse(text)
    out = xd.to_unicode()
    headings = [line for line in out.splitlines() if line.startswith('## ')]
    assert headings == ['## Metadata', '## Grid', '## Clues', '## Notes', '## Design']

    xd2 = parse(out)
    assert_standard(xd2)
    assert xd2.design == DESIGN_TEXT
    assert xd2.notes == xd.notes == 'A note.\n'
    assert xd2.to_unicode() == out


def test_design_text_not_cleaned():
    # to_unicode's character cleanup ('' -> ") must not touch the design
    design = "A { background-image: url('') }\n\nA..\n...\n...\n"
    xd = parse("## Metadata\n" + METADATA + "## Grid\n" + GRID_TEXT +
               "## Clues\n" + CLUES_TEXT + "## Design\n" + design)
    assert xd.design == design
    assert parse(xd.to_unicode()).design == design


def test_unknown_section_ignored():
    text = ("## Metadata\n" + METADATA + "\n## Solving Tips\nTitle: Not a header\nXYZ\n" +
            "A9. not a clue ~ NOPE\n\n## Grid\n" + GRID_TEXT + "\n## Clues\n" + CLUES_TEXT)
    xd = parse(text)
    assert_standard(xd)
    assert xd.notes == ''


def test_notes_section():
    text = ("## Metadata\n" + METADATA + "\n## Grid\n" + GRID_TEXT +
            "\n## Clues\n" + CLUES_TEXT + "\n## Notes\n\nFirst note.\n\nSecond: note.\n")
    xd = parse(text)
    assert_standard(xd)
    assert xd.notes == 'First note.\nSecond: note.\n'
    assert 'Second' not in xd.headers


def test_known_heading_needs_space_after_hashes():
    # '##GRID' is a plausible grid row, not a heading; file stays implicit
    text = "Title: T\n\n\n##GRID\n##GRID\n\n\nA3. x ~ GRID\n"
    xd = parse(text)
    assert xd.grid == ['##GRID', '##GRID']
    assert xd.clues == [(('A', 3), 'x', 'GRID')]


def test_lowercase_metadata_keys():
    text = ("## metadata\ntitle: Test Puzzle\nAUTHOR: Test Author\ndate: 2024-01-01\n"
            "rebus: 1=ONE\n## grid\n" + GRID_TEXT + "## clues\n" + CLUES_TEXT)
    xd = parse(text)
    assert_standard(xd)
    assert xd.get_header('Rebus') == '1=ONE'
    assert xd.rebus() == {'1': 'ONE'}
    assert xd.date() == '2024-01-01'
    # stored keys keep the file's spelling
    assert set(xd.headers) == {'title', 'AUTHOR', 'date', 'rebus'}


def test_lowercase_metadata_keys_headingless():
    xd = parse(HEADINGLESS.replace('Title:', 'title:').replace('Author:', 'author:'))
    assert_standard(xd)
    out = xd.to_unicode()
    assert out.startswith('title: Test Puzzle\nauthor: Test Author\n')


def test_set_header_updates_existing_key_case_insensitively():
    xd = parse(HEADINGLESS.replace('Title:', 'title:'))
    xd.set_header('Title', 'New Title')
    assert xd.headers == {'title': 'New Title', 'Author': 'Test Author', 'Date': '2024-01-01'}
    xd.set_header('TITLE', None)
    assert 'title' not in xd.headers
    assert xd.get_header('Title') == ''


def test_repeated_key_in_different_case_is_a_repeat():
    xd = parse("Title: A\ntitle: B\n\n\nAB\n\n\nA1. x ~ AB\n")
    assert xd.headers == {'Title': ['A', 'B']}
