"""unit tests for ipuz2xd.py"""

import json

import pytest

from xdfile.ipuz2xd import parse_ipuz
from xdfile.xdfile import IncompletePuzzleParse, PuzzleParseError


def _ipuz(solution, puzzle=None, clues=None, **extra):
    h, w = len(solution), len(solution[0])
    d = {
        "version": "http://ipuz.org/v2",
        "kind": ["http://ipuz.org/crossword#1"],
        "dimensions": {"width": w, "height": h},
        "empty": ":",
        "solution": solution,
        "puzzle": puzzle if puzzle is not None else [[0] * w for _ in range(h)],
        "clues": clues if clues is not None else {},
    }
    d.update(extra)
    return json.dumps(d).encode("utf-8")


# A 3x3 with one block:  AB#
#                        CDE
#                        #FG
SOL = [["A", "B", "#"], ["C", "D", "E"], ["#", "F", "G"]]
PUZ = [[1, 2, "#"], [3, ":", 4], ["#", 5, ":"]]
CLUES = {
    "Across": [[1, "First"], {"number": 3, "clue": "Second"}, "5 Third"],
    "Down": [[1, "Down one"], [2, "Down two"], [4, "Down four"]],
}


def test_basic_grid_headers_and_clues():
    xd = parse_ipuz(_ipuz(SOL, PUZ, CLUES, title="T", author="Ann Author",
                          editor="Ed Itor", copyright="&copy; 2016 Pub"),
                    "pub2016-01-28.ipuz")
    assert xd.grid == ["AB#", "CDE", "#FG"]
    assert xd.get_header("Title") == "T"
    assert xd.get_header("Author") == "Ann Author"
    assert xd.get_header("Editor") == "Ed Itor"
    assert xd.get_header("Copyright") == "© 2016 Pub"
    assert xd.get_header("Date") == "2016-01-28"
    assert xd.clues == [
        (("A", 1), "First", "AB"),
        (("A", 3), "Second", "CDE"),
        (("A", 5), "Third", "FG"),
        (("D", 1), "Down one", "AC"),
        (("D", 2), "Down two", "BDF"),
        (("D", 4), "Down four", "EG"),
    ]


def test_clue_text_html_and_entities():
    clues = {"Across": [[1, "<i>Hamlet</i> &quot;quote&quot;"]], "Down": []}
    xd = parse_ipuz(_ipuz(SOL, PUZ, clues), "x.ipuz")
    assert xd.clues[0] == (("A", 1), '{/Hamlet/} "quote"', "AB")


def test_intro_and_notes_become_notes_header():
    xd = parse_ipuz(_ipuz(SOL, PUZ, {}, intro="Read <b>this</b>.", notes="Also."), "x.ipuz")
    assert xd.get_header("Notes") == "Read this. Also."


def test_byline_editor_split_when_no_editor_field():
    xd = parse_ipuz(_ipuz(SOL, PUZ, {}, author="Ann Author; edited by Ed Itor"), "x.ipuz")
    assert xd.get_header("Author") == "Ann Author"
    assert xd.get_header("Editor") == "Ed Itor"


def test_rebus_cells():
    sol = [["AB", "C"], ["D", "E"]]
    xd = parse_ipuz(_ipuz(sol, [[1, 2], [3, 0]], {}), "x.ipuz")
    assert xd.grid == ["1C", "DE"]
    assert xd.get_header("Rebus") == "1=AB"
    assert dict(((d, n), a) for d, n, a in xd.iteranswers())[("A", 1)] == "ABC"


def test_dict_solution_cells_and_lowercase():
    sol = [[{"value": "a"}, "b"], ["c", "d"]]
    xd = parse_ipuz(_ipuz(sol, [[1, 2], [3, 0]], {}), "x.ipuz")
    assert xd.grid == ["AB", "CD"]


def test_circles_become_lowercase_special():
    puz = [[{"cell": 1, "style": {"shapebg": "circle"}}, 2], [3, 0]]
    xd = parse_ipuz(_ipuz([["A", "B"], ["C", "D"]], puz, {}), "x.ipuz")
    assert xd.grid == ["aB", "CD"]
    assert xd.get_header("Special") == "circle"


def test_named_style_circle():
    puz = [[{"cell": 1, "style": "c"}, 2], [3, 0]]
    xd = parse_ipuz(_ipuz([["A", "B"], ["C", "D"]], puz, {}, styles={"c": {"shapebg": "circle"}}), "x.ipuz")
    assert xd.grid == ["aB", "CD"]


def test_omitted_cells_are_open_char():
    # a letter printed outside the grid, above column 0
    sol = [["H", None, None], ["E", "D", "#"]]
    puz = [["1", None, None], [1, 2, "#"]]
    xd = parse_ipuz(_ipuz(sol, puz, {}), "x.ipuz")
    assert xd.grid == ["H__", "ED#"]


def test_unfilled_cell_is_unknown():
    xd = parse_ipuz(_ipuz([["A", ":"], ["C", "D"]], [[1, 2], [3, 0]], {}), "x.ipuz")
    assert xd.grid == ["A.", "CD"]


def test_bars_recorded_and_warned():
    from xdfile import utils
    puz = [[1, {"cell": 2, "style": {"barred": "L"}}], [{"cell": 3, "style": {"barred": "T"}}, 0]]
    xd = parse_ipuz(_ipuz([["A", "B"], ["C", "D"]], puz, {}), "x.ipuz")
    assert xd.bars == {(0, 1): "L", (1, 0): "T"}
    assert any("barred grid" in s for s in utils.g_logs)


def test_clue_number_without_slot_raises_with_partial_xd():
    clues = {"Across": [[1, "ok"], [9, "nowhere"]], "Down": []}
    with pytest.raises(IncompletePuzzleParse) as ei:
        parse_ipuz(_ipuz(SOL, PUZ, clues), "x.ipuz")
    assert "A9" in str(ei.value)
    assert ei.value.xd.clues == [(("A", 1), "ok", "AB"), (("A", 9), "nowhere", "")]


def test_directional_clue_keys():
    clues = {"Across:Across": [[1, "a"]], "Down:Down": [[1, "d"]]}
    xd = parse_ipuz(_ipuz(SOL, PUZ, clues), "x.ipuz")
    assert [c[0] for c in xd.clues] == [("A", 1), ("D", 1)]


def test_not_a_crossword():
    with pytest.raises(PuzzleParseError):
        parse_ipuz(_ipuz(SOL, PUZ, {}, kind=["http://ipuz.org/sudoku#1"]), "x.ipuz")


def test_not_json():
    with pytest.raises(PuzzleParseError):
        parse_ipuz(b"<html>", "x.ipuz")
