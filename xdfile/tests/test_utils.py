"""unit tests for utils.py"""
import os

from xdfile import utils

TEST_DIRECTORY = os.path.abspath(os.path.dirname(__file__))


def test_find_files():
    mygen = utils.find_files(TEST_DIRECTORY)
    for fullfn, contents in mygen:
        # It should throw out anything starting with '.'
        assert not fullfn.startswith('.')

def test_clean_c1_controls_cp1252_default():
    # U+0097 -> em dash, U+0091 -> left smart quote, U+009A -> š
    assert utils.clean_c1_controls("emdash") == "em—dash"
    assert utils.clean_c1_controls("hi") == "‘hi’"
    assert utils.clean_c1_controls("Ni") == "Niš"

def test_clean_c1_controls_macroman_e_acute_override():
    # U+008E is Mac Roman é in our corpus, not cp1252's Ž.
    assert utils.clean_c1_controls("Czanne") == "Cézanne"
    assert utils.clean_c1_controls("Jos") == "José"

def test_clean_c1_controls_skips_ambiguous_single():
    # U+0080 and U+0098 are too ambiguous (° vs €, ÷ vs ˜).
    # Caller must resolve manually; clean_c1_controls leaves them alone.
    assert utils.clean_c1_controls("90 compass") == "90 compass"
    assert utils.clean_c1_controls("3  cosine") == "3  cosine"

def test_clean_c1_controls_utf8_trailer_lead_dropped():
    # \u0080 + C1 = trailing bytes of \xe2\x80\xXX with lead byte lost.
    assert utils.clean_c1_controls("hi") == "“hi”"
    assert utils.clean_c1_controls("dont") == "don’t"

def test_clean_c1_controls_utf8_trailer_lead_as_a_circumflex():
    # When \xe2 survived as latin-1 'â', strip and reconstruct the
    # original UTF-8 character.
    assert utils.clean_c1_controls("âhiâ") == "“hi”"
    assert utils.clean_c1_controls("donât") == "don’t"

def test_clean_c1_controls_undefined_cp1252_passes_through():
    # 5 codepoints are undefined in cp1252; they're left alone for
    # manual resolution (XD010 finding still flags them).
    for cp in (0x81, 0x8d, 0x8f, 0x90, 0x9d):
        s = "x" + chr(cp) + "y"
        assert utils.clean_c1_controls(s) == s, f"U+{cp:04X} should pass through"

def test_clean_c1_controls_no_changes_for_clean_text():
    assert utils.clean_c1_controls("normal clue text") == "normal clue text"
    assert utils.clean_c1_controls("Café") == "Café"

def test_clean_latin1_utf8_mojibake_lowercase_e_circumflex():
    # 'Ãª' = bytes \xc3\xaa (UTF-8 for 'ê') misread as latin-1.
    assert utils.clean_latin1_utf8_mojibake("tÃªte") == "tête"


def test_clean_latin1_utf8_mojibake_lowercase_e_acute():
    assert utils.clean_latin1_utf8_mojibake("IngÃ©nue") == "Ingénue"


def test_clean_latin1_utf8_mojibake_a_circumflex_only_flagged_with_cont_byte():
    # Real 'Â' followed by ASCII ('Âge') must NOT be touched. The latin-1
    # encoding of 'Âg' is \xc2\x67 which fails UTF-8 decode anyway, but
    # the regex should not even match because 0x67 is outside U+0080-U+00BF.
    assert utils.clean_latin1_utf8_mojibake("Âge") == "Âge"
    assert utils.clean_latin1_utf8_mojibake("RÂLE") == "RÂLE"


def test_clean_latin1_utf8_mojibake_no_change_for_clean_text():
    assert utils.clean_latin1_utf8_mojibake("café") == "café"
    assert utils.clean_latin1_utf8_mojibake("plain ascii") == "plain ascii"

def test_clean_c1_controls_strips_orphan_quote_trailer():
    # U+009C/D after a straight " is the surviving trailer byte of
    # a UTF-8 smart quote whose lead bytes were turned into the
    # straight " upstream. Strip it.
    assert utils.clean_c1_controls('"Big Brother"') == '"Big Brother"'
    assert utils.clean_c1_controls('"open"') == '"open"'
    # Lone U+009D not preceded by " is left intact for manual review.
    assert utils.clean_c1_controls("foobar") == "foobar"



# Bylines as the nightly feeds deliver them -> (Author, Editor).
BYLINES = [
    ("by Byron Walden, edited by Ben Tausig", ("Byron Walden", "Ben Tausig")),
    ("Amanda Rafkin; edited by Kelsey Dixon", ("Amanda Rafkin", "Kelsey Dixon")),
    ("By Mike Shenk/Edited by Mike Shenk", ("Mike Shenk", "Mike Shenk")),
    ("Kyle Dolan / Ed. Patti Varol", ("Kyle Dolan", "Patti Varol")),
    ("By Adrian Johnson and Alexandra Doumani / Ed. David Steinberg",
     ("Adrian Johnson and Alexandra Doumani", "David Steinberg")),
    ("Zachary Edward-Brown & Shannon Rapp / Ed. Patti Varol",
     ("Zachary Edward-Brown & Shannon Rapp", "Patti Varol")),
    ("S.N., edited by Stanley Newman", ("S.N.", "Stanley Newman")),
    ("Fred Piscop, edited by Stanley Newman", ("Fred Piscop", "Stanley Newman")),
    ("By Alfio Micci; Ed. By Charles Preston", ("Alfio Micci", "Charles Preston")),
    ("By CJ Tan", ("CJ Tan", "")),
    ("by Matt Gaffney", ("Matt Gaffney", "")),
    ("Matt Gaffney", ("Matt Gaffney", "")),
    ("Ed Sessa", ("Ed Sessa", "")),
    ("Ed Pegg Jr.", ("Ed Pegg Jr.", "")),
    ("Byron Walden", ("Byron Walden", "")),
    # Only an editor named: left for a person to sort out.
    ("Edited by Will Shortz", ("Edited by Will Shortz", "")),
    ("", ("", "")),
]


def test_clean_author_header():
    for byline, want in BYLINES:
        assert utils.clean_author_header(byline) == want, byline


def test_split_author_editor_keeps_existing_editor():
    assert utils.split_author_editor("Smith", "Jones") == ("Smith", "Jones")
    assert utils.split_author_editor("", "Jones") == ("", "Jones")


def test_strip_by_prefix():
    assert utils.strip_by_prefix("By Mike Shenk") == "Mike Shenk"
    assert utils.strip_by_prefix("by by Mike Shenk") == "Mike Shenk"
    assert utils.strip_by_prefix("Byron Walden") == "Byron Walden"
    assert utils.strip_by_prefix("By") == "By"
