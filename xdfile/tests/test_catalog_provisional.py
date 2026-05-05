"""Unit tests for catalog.py provisional xdid helpers."""
from xdfile import catalog
from xdfile.xdfile import xdfile as XDFile


_MINIMAL_XD = "Title: t\n\n\nA\n\n\nA1. c ~ A\n"


def test_is_provisional_real_xdids_negative():
    assert not catalog.is_provisional("nyt2015-03-22")
    assert not catalog.is_provisional("up-481")
    assert not catalog.is_provisional("")
    assert not catalog.is_provisional(None)


def test_is_provisional_no_pubid_form():
    assert catalog.is_provisional("unshelved-a3f9c2b1-foo")


def test_is_provisional_with_pubid_form():
    assert catalog.is_provisional("nyt-unshelved-a3f9c2b1-foo")


def test_provisional_xdid_no_pubid():
    xdid = catalog._provisional_xdid("bwh|bwh-2015.tgz|other_sources/foo.puz")
    assert xdid.startswith("unshelved-")
    parts = xdid.split("-")
    assert len(parts[1]) == 8  # hash
    assert all(c in "0123456789abcdef" for c in parts[1])
    assert parts[2] == "foo"  # slug


def test_provisional_xdid_with_pubid():
    xdid = catalog._provisional_xdid("bwh|bwh-2015.tgz|other_sources/bridge.puz", pubid="nyt")
    assert xdid.startswith("nyt-unshelved-")
    assert xdid.endswith("-bridge")


def test_provisional_xdid_deterministic():
    a = catalog._provisional_xdid("bwh|x.tgz|y.puz")
    b = catalog._provisional_xdid("bwh|x.tgz|y.puz")
    assert a == b


def test_provisional_xdid_distinct_for_distinct_inputs():
    a = catalog._provisional_xdid("bwh|x.tgz|foo.puz")
    b = catalog._provisional_xdid("bwh|x.tgz|bar.puz")
    c = catalog._provisional_xdid("nyt|x.tgz|foo.puz")
    assert a != b  # different filename
    assert a != c  # different ExternalSource
    assert b != c


def test_provisional_slug_strips_specials():
    assert catalog._provisional_slug("Odd File (v2).puz") == "oddfilev2"
    assert catalog._provisional_slug("with spaces.puz") == "withspaces"
    assert catalog._provisional_slug("UPPER123.puz") == "upper123"


def test_provisional_slug_dashes_kept():
    assert catalog._provisional_slug("foo-bar-baz.puz") == "foo-bar-baz"


def test_provisional_slug_length_cap():
    out = catalog._provisional_slug("a" * 100 + ".puz", max_len=10)
    assert len(out) == 10


def test_provisional_slug_empty_fallback():
    # All-special input strips to nothing -> 'x' fallback
    assert catalog._provisional_slug("(((.puz") == "x"


def test_parse_mdtext_three_parts():
    assert catalog._parse_mdtext("a|b|c/d") == ("a", "b", "c/d")


def test_parse_mdtext_short():
    assert catalog._parse_mdtext("a|b") == ("a", "b", "")
    assert catalog._parse_mdtext("") == ("", "", "")


def test_provisional_path_no_pubid():
    xdid = "unshelved-a3f9c2b1-foo"
    assert catalog.provisional_path(xdid, "bwh") == "unshelved/bwh/" + xdid


def test_provisional_path_no_pubid_no_extsrc():
    xdid = "unshelved-a3f9c2b1-foo"
    assert catalog.provisional_path(xdid, "") == "unshelved/unknown/" + xdid


def test_provisional_path_with_unknown_pubid():
    # Pubid not in publications.tsv -> publisher falls back to pubid itself.
    xdid = "fakepub-unshelved-a3f9c2b1-foo"
    p = catalog.provisional_path(xdid, "bwh")
    assert p == "fakepub/unshelved/" + xdid


def test_shelf_path_from_xdid_date_format():
    # Pubid not in publications.tsv -> publisher falls back to pubid itself.
    assert catalog.shelf_path_from_xdid("fakepub2015-03-22") == "fakepub/2015/fakepub2015-03-22"


def test_shelf_path_from_xdid_number_format():
    assert catalog.shelf_path_from_xdid("fakepub-481") == "fakepub/fakepub-481"


def test_shelf_path_from_xdid_unrecognized():
    # Not a recognizable xdid format
    assert catalog.shelf_path_from_xdid("not-an-xdid") is None
    assert catalog.shelf_path_from_xdid("unshelved-a3f9c2b1-foo") is None
    assert catalog.shelf_path_from_xdid("") is None


def _make_xd(filename):
    xd = XDFile(_MINIMAL_XD, filename=filename)
    return xd


def test_deduce_set_seqnum_skips_embedded_digits():
    # Embedded digits (year fragment, dir index) shouldn't become Number.
    xd = _make_xd("WAPost/wp92bms.xd")
    catalog.deduce_set_seqnum(xd)
    assert not xd.get_header("Number"), "wp92bms (year fragment) should not produce Number"
    assert not xd.get_header("Date")


def test_deduce_set_seqnum_trailing_digits_become_number():
    xd = _make_xd("foo/up-1234.xd")
    catalog.deduce_set_seqnum(xd)
    assert xd.get_header("Number") == "1234"


def test_deduce_set_seqnum_trailing_digits_no_separator():
    xd = _make_xd("other_sources/UP0481.xd")
    catalog.deduce_set_seqnum(xd)
    assert xd.get_header("Number") == "481"


def test_deduce_set_seqnum_single_digit_number():
    # Real corpus has small-number puzzles (e.g. bg-1, bg-2); regex must catch.
    xd = _make_xd("bg-2.xd")
    catalog.deduce_set_seqnum(xd)
    assert xd.get_header("Number") == "2"


def test_deduce_set_seqnum_trailing_letter_variant():
    # Optional single-letter variant suffix (e.g. "bg-002a") still extracts Number.
    xd = _make_xd("bg-002a.xd")
    catalog.deduce_set_seqnum(xd)
    assert xd.get_header("Number") == "2"


def test_deduce_set_seqnum_date_wins_over_number():
    # Date heuristic runs first; even if digits are present, Date should be set.
    xd = _make_xd("nytimes/2015/nyt2015-03-22.xd")
    catalog.deduce_set_seqnum(xd)
    assert xd.get_header("Date")
    assert not xd.get_header("Number")
