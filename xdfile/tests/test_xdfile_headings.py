"""Section headings (spec 2.0): '## Metadata', '## Grid', '## Clues'."""
import textwrap

from xdfile.xdfile import xdfile


HEADINGLESS = textwrap.dedent("""\
    Title: T
    Author: A


    ABC
    D#E
    FGH


    A1. First ~ ABC
    A3. Second ~ FGH

    D1. Down one ~ ADF
    D2. Down two ~ CEH


    A note.
""")


def parse(text):
    return xdfile(text, filename="test2024-01-01.xd")


def sections(xd):
    return xd.headers, xd.grid, xd.clues


def test_headed_matches_headingless():
    headed = textwrap.dedent("""\
        ## Metadata

        Title: T
        Author: A

        ## Grid

        ABC
        D#E
        FGH

        ## Clues

        A1. First ~ ABC
        A3. Second ~ FGH

        D1. Down one ~ ADF
        D2. Down two ~ CEH
    """)
    assert sections(parse(headed)) == sections(parse(HEADINGLESS))


def test_order_unimportant():
    headed = textwrap.dedent("""\
        ## Clues
        A1. First ~ ABC
        A3. Second ~ FGH
        D1. Down one ~ ADF
        D2. Down two ~ CEH
        ## Grid
        ABC
        D#E
        FGH
        ## Metadata
        Title: T
        Author: A
    """)
    assert sections(parse(headed)) == sections(parse(HEADINGLESS))


def test_heading_names_case_insensitive():
    headed = "##   METADATA\nTitle: T\n  ## grid\nAB\n## ClUeS\nA1. x ~ AB\n"
    xd = parse(headed)
    assert xd.headers == {"Title": "T"}
    assert xd.grid == ["AB"]
    assert xd.clues == [(("A", 1), "x", "AB")]


def test_blank_lines_do_not_change_sections():
    headed = "## Metadata\n\n\n\nTitle: T\n\n\n\nAuthor: A\n## Grid\nAB\n\n\n\nCD\n## Clues\nA1. x ~ AB\n"
    xd = parse(headed)
    assert xd.headers == {"Title": "T", "Author": "A"}
    assert xd.grid == ["AB", "CD"]


def test_other_sections_ignored():
    headed = textwrap.dedent("""\
        ## Metadata
        Title: T
        ## Notes
        Not part of any section the spec defines.
        ## Grid
        AB
        ## Design
        O { background: circle }
        ## Clues
        A1. x ~ AB
    """)
    xd = parse(headed)
    assert xd.headers == {"Title": "T"}
    assert xd.grid == ["AB"]
    assert xd.clues == [(("A", 1), "x", "AB")]
    assert xd.notes == ""


def test_lines_before_first_heading_ignored():
    headed = "stray line\n## Metadata\nTitle: T\n## Grid\nAB\n## Clues\nA1. x ~ AB\n"
    xd = parse(headed)
    assert xd.headers == {"Title": "T"}
    assert xd.notes == ""


def test_grid_rows_starting_with_hashes_are_not_headings():
    text = "Title: T\n\n\n##AB\nCD##\n\n\nA1. x ~ CD\n"
    xd = parse(text)
    assert xd.grid == ["##AB", "CD##"]


def test_unknown_heading_alone_keeps_implicit_parsing():
    # Only a metadata/grid/clues heading switches a file to explicit mode.
    text = HEADINGLESS.replace("A note.", "## Notes\nA note.")
    xd = parse(text)
    assert sections(xd) == sections(parse(HEADINGLESS))


def test_headed_file_writes_headingless():
    headed = "## Metadata\nTitle: T\nAuthor: A\n## Grid\nABC\nD#E\nFGH\n## Clues\nA1. First ~ ABC\nA3. Second ~ FGH\nD1. Down one ~ ADF\nD2. Down two ~ CEH\n"
    expected = parse(HEADINGLESS.replace("\n\n\nA note.\n", "\n"))
    assert parse(headed).to_unicode() == expected.to_unicode()
