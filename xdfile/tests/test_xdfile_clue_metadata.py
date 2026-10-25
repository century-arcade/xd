"""Clue metadata (spec 3.0): 'A1 ^Refs: A2 D4' on the line after its clue."""
import textwrap

from xdfile.xdfile import xdfile


def parse(text):
    return xdfile(text, filename="test2024-01-01.xd")


def puzzle(clues):
    return textwrap.dedent("""\
        Title: T


        ABC
        D#E
        FGH


    """) + textwrap.dedent(clues)


def test_metadata_attaches_to_clue_above():
    xd = parse(puzzle("""\
        A1. First ~ ABC
        A1 ^Refs: D1 D2
        A3. Second ~ FGH

        D1. Down one ~ ADF
        D2. Down two ~ CEH
    """))
    assert [pos for pos, _, _ in xd.clues] == [("A", 1), ("A", 3), ("D", 1), ("D", 2)]
    assert xd.clue_metadata == {0: [("Refs", "D1 D2")]}


def test_value_with_period_is_not_a_clue():
    xd = parse(puzzle("""\
        A1. First ~ ABC
        A1 ^Comment: Not in Webster's. Check
        A3. Second ~ FGH
    """))
    assert len(xd.clues) == 2
    assert xd.clue_metadata == {0: [("Comment", "Not in Webster's. Check")]}


def test_several_keys_keep_order_and_case():
    xd = parse(puzzle("""\
        A1. First ~ ABC
        A1 ^Hard: Opening
        A1 ^easy: Alphabet start
    """))
    assert xd.clue_metadata == {0: [("Hard", "Opening"), ("easy", "Alphabet start")]}


def test_uniclue_reference():
    xd = parse(puzzle("""\
        1. First ~ ABC
        1 ^Refs: 3
    """))
    assert xd.clue_metadata == {0: [("Refs", "3")]}


def test_metadata_not_after_its_clue_is_ignored():
    xd = parse(puzzle("""\
        A9 ^Refs: D1
        A1. First ~ ABC
        A3 ^Refs: D1
        A3. Second ~ FGH
    """))
    assert [pos for pos, _, _ in xd.clues] == [("A", 1), ("A", 3)]
    assert xd.clue_metadata == {}


def test_caret_in_clue_text_is_still_a_clue():
    xd = parse(puzzle("""\
        A1. Exponent ^2: square ~ ABC
    """))
    assert xd.clues == [(("A", 1), "Exponent ^2: square", "ABC")]
    assert xd.clue_metadata == {}


def test_round_trip():
    text = puzzle("""\
        A1. First ~ ABC
        A1 ^Refs: D1
        A3. Second ~ FGH

        D1. Down one ~ ADF
        D1 ^Hard: Alphabet soup
        D1 ^Easy: Letters
        D2. Down two ~ CEH
    """)
    out = parse(text).to_unicode()
    assert "A1. First ~ ABC\nA1 ^Refs: D1\nA3. Second ~ FGH" in out
    assert "D1. Down one ~ ADF\nD1 ^Hard: Alphabet soup\nD1 ^Easy: Letters\nD2." in out
    again = parse(out)
    assert again.clues == parse(text).clues
    assert again.clue_metadata == parse(text).clue_metadata


def test_headed_file():
    xd = parse(textwrap.dedent("""\
        ## Metadata

        Title: T

        ## Grid

        ABC
        D#E
        FGH

        ## Clues

        A1. First ~ ABC
        A1 ^Refs: D1
    """))
    assert xd.clue_metadata == {0: [("Refs", "D1")]}


def test_corpus_cache_keeps_metadata():
    import json
    from xdfile.xdfile import _xd_to_dict, _dict_to_xd

    xd = parse(puzzle("""\
        A1. First ~ ABC
        A1 ^Refs: D1
    """))
    back = _dict_to_xd(json.loads(json.dumps(_xd_to_dict(xd))))
    assert back.clue_metadata == xd.clue_metadata

    old = _xd_to_dict(xd)
    del old['clue_metadata']  # a cache written before this field existed
    assert _dict_to_xd(old).clue_metadata == {}
