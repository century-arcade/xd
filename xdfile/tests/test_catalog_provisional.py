"""Unit tests for catalog.py provisional xdid helpers."""
from collections import namedtuple

from xdfile import catalog
from xdfile import metadatabase as metadb
from xdfile.xdfile import xdfile as XDFile


_FakeReceipt = namedtuple("_FakeReceipt", "CaptureTime ReceivedTime ExternalSource InternalSource SourceFilename xdid")


def _receipt(ExternalSource, SourceFilename, xdid, ReceivedTime="2016-08-21"):
    return _FakeReceipt(
        CaptureTime="", ReceivedTime=ReceivedTime,
        ExternalSource=ExternalSource, InternalSource="",
        SourceFilename=SourceFilename, xdid=xdid,
    )


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


def test_shelf_path_from_xdid_date_variant():
    # Trailing letter is a variant marker; shelves alongside the canonical date.
    assert catalog.shelf_path_from_xdid("fakepub2015-03-22a") == "fakepub/2015/fakepub2015-03-22a"
    assert catalog.shelf_path_from_xdid("fakepub2015-03-22z") == "fakepub/2015/fakepub2015-03-22z"


def test_shelf_path_from_xdid_number_variant():
    assert catalog.shelf_path_from_xdid("fakepub-481a") == "fakepub/fakepub-481a"


def test_shelf_path_from_xdid_unrecognized():
    # Not a recognizable xdid format
    assert catalog.shelf_path_from_xdid("not-an-xdid") is None
    assert catalog.shelf_path_from_xdid("unshelved-a3f9c2b1-foo") is None
    assert catalog.shelf_path_from_xdid("") is None
    # Two-letter variant suffix isn't allowed — only single letter.
    assert catalog.shelf_path_from_xdid("fakepub2015-03-22ab") is None


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


def _patch_receipts(monkeypatch, by_xdid=None, by_source=None):
    by_xdid = by_xdid or {}
    by_source = by_source or {}
    monkeypatch.setattr(metadb, "_receipts_by_xdid", lambda: by_xdid)
    monkeypatch.setattr(metadb, "check_already_received",
                        lambda extsrc, sf: by_source.get((extsrc, sf), []))


def test_latest_receipt_for_xdid_returns_max_received_time(monkeypatch):
    rows = [
        _receipt("bwh", "NYSun/late.puz",  "nys2007-03-27", ReceivedTime="2018-05-01"),
        _receipt("bwh", "NYSun/early.puz", "nys2007-03-27", ReceivedTime="2016-08-21"),
        _receipt("bwh", "NYSun/mid.puz",   "nys2007-03-27", ReceivedTime="2017-01-15"),
    ]
    _patch_receipts(monkeypatch, by_xdid={"nys2007-03-27": rows})
    result = metadb.latest_receipt_for_xdid("nys2007-03-27")
    assert result.SourceFilename == "NYSun/late.puz"


def test_latest_receipt_for_xdid_no_rows(monkeypatch):
    _patch_receipts(monkeypatch, by_xdid={})
    assert metadb.latest_receipt_for_xdid("nys2007-03-27") is None


def test_latest_receipt_after_displacement_picks_promoted_source(monkeypatch):
    # Replay state after a --conflict-mode=replace run: A's original 2016 claim
    # on the canonical xdid is overshadowed by B's 2026 promotion row. A's
    # demotion row maps A to the variant xdid, so it doesn't appear in the
    # canonical-xdid query at all.
    canonical = "nys2007-03-27"
    variant = "nys2007-03-27a"
    by_xdid = {
        canonical: [
            _receipt("bwh", "A.puz", canonical, ReceivedTime="2016-08-21"),
            _receipt("bwh", "B.puz", canonical, ReceivedTime="2026-05-06"),
        ],
        variant: [
            _receipt("bwh", "A.puz", variant, ReceivedTime="2026-05-06"),
        ],
    }
    _patch_receipts(monkeypatch, by_xdid=by_xdid)
    canonical_claimant = metadb.latest_receipt_for_xdid(canonical)
    variant_claimant = metadb.latest_receipt_for_xdid(variant)
    assert canonical_claimant.SourceFilename == "B.puz"
    assert variant_claimant.SourceFilename == "A.puz"


def test_variants_of_xdid_matches_letter_suffix(monkeypatch):
    by_xdid = {
        "nys2007-03-27":  [_receipt("bwh", "f.puz", "nys2007-03-27")],
        "nys2007-03-27a": [_receipt("bwh", "g.puz", "nys2007-03-27a")],
        "nys2007-03-27c": [_receipt("bwh", "h.puz", "nys2007-03-27c")],
        "nys2007-03-28":  [_receipt("bwh", "i.puz", "nys2007-03-28")],
        # Not a variant of nys2007-03-27 — different base date.
        "nys2007-03-28a": [_receipt("bwh", "j.puz", "nys2007-03-28a")],
    }
    _patch_receipts(monkeypatch, by_xdid=by_xdid)
    variants = metadb.variants_of_xdid("nys2007-03-27")
    xdids = sorted(r.xdid for r in variants)
    assert xdids == ["nys2007-03-27a", "nys2007-03-27c"]


def test_mint_variant_xdid_first_letter(monkeypatch):
    # No prior receipts for this base -> lowest letter is 'a'.
    _patch_receipts(monkeypatch, by_xdid={}, by_source={})
    assert catalog.mint_variant_xdid("nys2007-03-27", "bwh", "x.puz") == "nys2007-03-27a"


def test_mint_variant_xdid_skips_claimed_letters(monkeypatch):
    by_xdid = {
        "nys2007-03-27a": [_receipt("bwh", "g.puz", "nys2007-03-27a")],
        "nys2007-03-27b": [_receipt("bwh", "h.puz", "nys2007-03-27b")],
    }
    _patch_receipts(monkeypatch, by_xdid=by_xdid)
    assert catalog.mint_variant_xdid("nys2007-03-27", "bwh", "new.puz") == "nys2007-03-27c"


def test_mint_variant_xdid_stability_reuses_prior_assignment(monkeypatch):
    # SourceFilename already has a receipt for variant 'b' -> reuse it,
    # even though 'a' is currently free.
    by_xdid = {
        "nys2007-03-27b": [_receipt("bwh", "g.puz", "nys2007-03-27b")],
    }
    by_source = {
        ("bwh", "g.puz"): [_receipt("bwh", "g.puz", "nys2007-03-27b")],
    }
    _patch_receipts(monkeypatch, by_xdid=by_xdid, by_source=by_source)
    assert catalog.mint_variant_xdid("nys2007-03-27", "bwh", "g.puz") == "nys2007-03-27b"


def test_mint_variant_xdid_in_run_claimed(monkeypatch):
    # 'a' was minted earlier in this same run (not yet in receipts.tsv).
    _patch_receipts(monkeypatch, by_xdid={}, by_source={})
    assert catalog.mint_variant_xdid(
        "nys2007-03-27", "bwh", "new.puz",
        in_run_claimed={"nys2007-03-27a"},
    ) == "nys2007-03-27b"


def test_mint_variant_xdid_exhausted(monkeypatch):
    by_xdid = {"nys2007-03-27" + ch: [_receipt("bwh", ch + ".puz", "nys2007-03-27" + ch)]
               for ch in "abcdefghijklmnopqrstuvwxyz"}
    _patch_receipts(monkeypatch, by_xdid=by_xdid)
    assert catalog.mint_variant_xdid("nys2007-03-27", "bwh", "new.puz") is None


def test_mint_variant_xdid_unrecognized_base(monkeypatch):
    # Base xdid with no shelf format -> nothing to mint.
    _patch_receipts(monkeypatch)
    assert catalog.mint_variant_xdid("not-an-xdid", "bwh", "x.puz") is None


def test_mint_variant_xdid_number_format(monkeypatch):
    _patch_receipts(monkeypatch, by_xdid={})
    assert catalog.mint_variant_xdid("up-481", "bwh", "x.puz") == "up-481a"
