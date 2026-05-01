"""decode() pipeline tests using synthetic mojibake strings drawn from
real corpus cases.

Each input is the literal Python string that puzpy would produce after
decoding a .puz file with the relevant byte sequence. We test decode()
directly rather than through a .puz round-trip because puzpy is
well-tested by its own maintainers; the interesting logic is what
decode() does with the resulting string. This also keeps the tests
runnable in CI without shipping copyrighted .puz binaries.

Each case's comment cites the corpus .xd file the bytes came from, so
future maintainers can cross-reference. See doc/character-encoding.md
for the full taxonomy of mojibake patterns these tests cover.
"""
from xdfile.puz2xd import decode


# Each case: (input_with_mojibake, expected_output, comment).
# Input is what puzpy returns after decoding ISO-8859-1 .puz bytes.
CASES = [
    # ---- U+008E Mac Roman override (cp1252 says 'Ž', corpus wants 'é') ----
    # gxd/bostonglobe/2015/bg2015-03-22.xd:109 — bg150322.puz
    ("Shortstop Jos\x8e", "Shortstop José"),
    # gxd/king/2008/pk2008-07-20.xd:124 — pk080720.puz
    ("G\x8erard Depardieu film", "Gérard Depardieu film"),
    # gxd/newsday/2005/nw2005-03-08.xd:69 — nw050308.puz
    ("Popular banquet entr\x8ee", "Popular banquet entrée"),

    # ---- cp1252 default for the šŠž block ----
    # gxd/wapost/2012/wap2012-03-04.xd:44 — pp120304.puz
    ("Ni\x9a natives", "Niš natives"),
    # gxd/indie/bequigley/beq-0424.xd:44 — Špilberk Castle (cp1252 Š is correct)
    ("\x8apilberk Castle", "Špilberk Castle"),
    # Serbian "Bože pravde" (national anthem)
    ("Bo\x9ee pravde", "Bože pravde"),

    # ---- UTF-8 smart-quote trailer reconstruction ----
    # gxd/philadelphia/2014/pi2014-01-12.xd — pi140112.puz
    # Original UTF-8 bytes \xe2\x80\x9c..\xe2\x80\x9d misread as latin-1
    # produces 'â' + U+0080 + U+009C/D. Reconstructed and then ASCII-flattened
    # to straight quotes by the typography pass.
    ("Trapped, with \xe2\x80\x9cup\xe2\x80\x9d", 'Trapped, with "up"'),
    # Variant: leading 'â' (\xe2 misread) was already collapsed upstream,
    # leaving just the C1 trailer pair.
    ("\x80\x9chello\x80\x9d", '"hello"'),
    # Right curly single quote (apostrophe)
    ("don\xe2\x80\x99t", "don't"),

    # ---- Em dash (cp1252 0x97) ----
    # gxd/avclub/2013/avc2013-07-03.xd:73
    ("Eja\x97wait", "Eja—wait"),

    # ---- Latin-1 misread of UTF-8 (XD009-class) ----
    # gxd/crossynergy/2015/cs2015-03-04.xd:73 — should be tête
    ("\"___ t\xc3\xaate\" lyric", "\"___ tête\" lyric"),
    # gxd/avclub/2016/avc2016-05-25.xd:71 — Ingénue
    ("Ing\xc3\xa9nue", "Ingénue"),
    # Multiple in one line
    ("M\xc3\xa1laga and Caf\xc3\xa9", "Málaga and Café"),
    # 'Ã´' (= ô) in Côte / Rhône
    ("C\xc3\xb4te d'Azur", "Côte d'Azur"),

    # ---- Triple-encoded mojibake collapses correctly ----
    # gxd/universal/2018/up2018-07-12.xd-style: 'â' (U+00E2) + C1 trailer
    # pair, where the leading 'â' is itself a UTF-8 round-trip artifact.
    ("Christian\xe2\x80\x99s book", "Christian's book"),

    # ---- Clean text passes through ----
    ("Normal clue text", "Normal clue text"),
    ("café", "café"),
    # Real French 'Â' / 'Ã' must NOT be touched by XD009-class fix.
    ("Âge moyen", "Âge moyen"),
    ("RÂLE", "RÂLE"),
    ("São Paulo", "São Paulo"),
]


def test_decode_pipeline():
    for input_text, expected in CASES:
        actual = decode(input_text)
        assert actual == expected, (
            f"decode({input_text!r}) = {actual!r}, expected {expected!r}"
        )


def test_decode_skips_ambiguous_u0080():
    # gxd/bostonglobe/2009/bg2009-06-07.xd:32 — the "90° on a compass" case.
    # cp1252 says U+0080 = '€' but corpus wants '°' (PDF Symbol artifact).
    # decode() must NOT auto-introduce '€'; the codepoint is left for the
    # XD010 lint rule to surface for manual review.
    out = decode("90\x80 on a compass")
    assert "90€" not in out
    assert "\x80" in out  # left intact


def test_decode_skips_ambiguous_u0098():
    # bg2010-03-28.xd:166 / bg2012-04-29.xd:138 — math contexts wanting '÷'.
    # Neither cp1252 ('˜') nor Mac Roman ('ò') is right; left for manual fix.
    out = decode("MDLX \x98 X")
    assert "˜" not in out
    assert "ò" not in out
    assert "\x98" in out


def test_decode_undefined_cp1252_passes_through():
    # cp1252 has 5 undefined slots: 0x81, 0x8D, 0x8F, 0x90, 0x9D. They're
    # left intact rather than guessed; XD010 lint surfaces them.
    for cp in (0x81, 0x8d, 0x8f, 0x90, 0x9d):
        s = "x" + chr(cp) + "y"
        out = decode(s)
        assert chr(cp) in out, f"U+{cp:04X} should pass through, got {out!r}"


def test_decode_strips_orphan_quote_trailer():
    # Specifically NOT something decode() handles directly — orphan U+009C
    # / U+009D after a straight " is XD010-fixer territory (the .xd-level
    # cleanup, not the puz-conversion pipeline). Document that here so a
    # future change doesn't accidentally start handling it in decode().
    out = decode('"Beyond the Sea"\x9d')
    assert "\x9d" in out  # decode passes it through; XD010 strips it later


def test_decode_no_orphan_a_circumflex_strip():
    # Legacy decode() blindly stripped 'Â' (U+00C2), corrupting real French.
    # The new pipeline only strips 'Â' when followed by a C1 control (a
    # UTF-8 mojibake signal).
    assert decode("Île-de-France") == "Île-de-France"
    assert decode("RÂLE") == "RÂLE"


def test_decode_collapses_nbsp():
    # \xc2\xa0 = UTF-8 NBSP read as latin-1; \xa0 = bare NBSP. Both -> space.
    assert decode("foo\xc2\xa0bar") == "foo bar"
    assert decode("foo\xa0bar") == "foo bar"
