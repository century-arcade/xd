"""Tests for xdlint.py.

Layout:
    helpers          - rebus parsing, slot enumeration, answer validation
    parser           - section detection, auto-recovery, clue parsing edge cases
    rules            - one positive case for each rule, plus key negative cases
                       for rules whose semantics changed in the recent review
    fixers           - per-fixer behavior plus pipeline / idempotence
    cli              - argument-driven active-set construction and exit gating

Each test prefers building findings via run_checks() with an explicit
active-codes set, so unrelated rules don't pollute the assertion.
"""
import io
import sys
import textwrap
from contextlib import redirect_stdout, redirect_stderr

import pytest

import xdlint


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_slot_cache():
    """The module-level slot cache is keyed on id(ctx); ids may collide
    across tests, so wipe between tests."""
    xdlint._SLOT_CACHE.clear()
    yield
    xdlint._SLOT_CACHE.clear()


def make_ctx(text, filename="t.xd"):
    parsed = xdlint.parse(text)
    return xdlint.Ctx(filename=filename, text=text, parsed=parsed)


def run_rule(code, text, filename="t.xd"):
    """Run a single rule by code and return its findings."""
    ctx = make_ctx(text, filename)
    fn = next(f for (c, _s, _n, _e, f) in xdlint.RULES if c == code)
    return list(fn(ctx))


def codes_emitted(text, active=None, filename="t.xd"):
    ctx = make_ctx(text, filename)
    return [f.code for f in xdlint.run_checks(ctx, active)]


# A small valid puzzle used as a base for negative tests. Slots are
# A1=ABC, A3=FGH, D1=ADF, D2=CEH (3x3 with one block at (1,1)).
SIMPLE = textwrap.dedent("""\
    Title: T
    Author: A
    Date: 2024-01-01


    ABC
    D#E
    FGH


    A1. First ~ ABC
    A3. Second ~ FGH

    D1. Down one ~ ADF
    D2. Down two ~ CEH
""")


def test_simple_puzzle_is_clean():
    """SIMPLE is the negative-case baseline; if it ever stops being clean,
    every test in this file built on top of it is suspect."""
    findings = codes_emitted(SIMPLE, filename="src2024-01-01.xd")
    # XD107/XD108/XD106 etc. are warnings about missing/duplicate headers;
    # SIMPLE has Title/Author/Date so they shouldn't fire. XD202 is order;
    # the headers are in canonical order. No grid/clue issues either.
    assert findings == [], f"SIMPLE not clean: {findings}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestRebusParsing:
    def test_plain_value(self):
        r = xdlint.parse_rebus_value("ONE")
        assert r.across == ["ONE"]
        assert r.down == ["ONE"]
        assert not r.is_directional

    def test_directional(self):
        r = xdlint.parse_rebus_value("IE/EI")
        assert r.across == ["IE"]
        assert r.down == ["EI"]
        assert r.is_directional

    def test_schrodinger(self):
        r = xdlint.parse_rebus_value("A|B")
        assert r.across == ["A", "B"]
        assert r.down == ["A", "B"]
        assert not r.is_directional
        assert r.is_schrodinger(0)
        assert r.is_schrodinger(1)

    def test_directional_with_schrodinger_in_one_half(self):
        r = xdlint.parse_rebus_value("SE/S|E")
        assert r.across == ["SE"]
        assert r.down == ["S", "E"]
        assert r.is_directional

    def test_literal_slash_when_one_half_empty(self):
        # '/' with empty before is a literal '/' cell, not a directional split.
        r = xdlint.parse_rebus_value("/")
        assert r.across == ["/"]
        assert r.down == ["/"]

    def test_pipe_with_one_part_is_literal(self):
        # 'A|' has an empty part, so it's not a Schrödinger operator.
        r = xdlint.parse_rebus_value("A|")
        assert r.across == ["A|"]

    def test_parse_rebus_header(self):
        m = xdlint.parse_rebus_header("1=ONE 2=TWO 3=A/B")
        assert set(m) == {"1", "2", "3"}
        assert m["1"].across == ["ONE"]
        assert m["3"].across == ["A"]
        assert m["3"].down == ["B"]

    def test_parse_rebus_header_skips_garbage(self):
        # A multi-char key, a no-equals token, and an empty piece all skipped.
        m = xdlint.parse_rebus_header("1=ONE bare 22=BAD =EMPTY")
        assert set(m) == {"1"}


class TestEnumerateSlots:
    def test_simple_3x3(self):
        grid = [
            xdlint.GridRow(line=1, cells="ABC"),
            xdlint.GridRow(line=2, cells="D#E"),
            xdlint.GridRow(line=3, cells="FGH"),
        ]
        slots = xdlint.enumerate_slots(grid)
        positions = {(d, n): cells for (d, n, _r, _c, cells) in slots}
        assert (("A", 1) in positions and len(positions[("A", 1)]) == 3)
        assert (("D", 1) in positions and len(positions[("D", 1)]) == 3)
        assert (("D", 2) in positions and len(positions[("D", 2)]) == 3)
        assert (("A", 3) in positions and len(positions[("A", 3)]) == 3)

    def test_skips_length_one_slots(self):
        grid = [
            xdlint.GridRow(line=1, cells="A#B"),
            xdlint.GridRow(line=2, cells="###"),
            xdlint.GridRow(line=3, cells="C#D"),
        ]
        # No slot is longer than 1 cell; nothing should be emitted.
        assert xdlint.enumerate_slots(grid) == []

    def test_empty_grid(self):
        assert xdlint.enumerate_slots([]) == []


class TestAnswerValidation:
    def _validate(self, answer, slot_cells, grid_rows, rebus, direction_idx=0):
        grid = [xdlint.GridRow(line=i + 1, cells=row)
                for i, row in enumerate(grid_rows)]
        return xdlint._validate_answer_against_slot(
            answer, slot_cells, grid, rebus, direction_idx,
        )

    def test_plain_match(self):
        result = self._validate("ABC", [(0, 0), (0, 1), (0, 2)], ["ABC"], {})
        assert result is None

    def test_too_short(self):
        result = self._validate("AB", [(0, 0), (0, 1), (0, 2)], ["ABC"], {})
        assert result is not None and result[0] == "XD006"

    def test_too_long(self):
        result = self._validate("ABCD", [(0, 0), (0, 1), (0, 2)], ["ABC"], {})
        assert result is not None and result[0] == "XD006"

    def test_letter_mismatch(self):
        result = self._validate("AXC", [(0, 0), (0, 1), (0, 2)], ["ABC"], {})
        assert result is not None and result[0] == "XD007"

    def test_wildcard_accepts_anything(self):
        result = self._validate("AZC", [(0, 0), (0, 1), (0, 2)], ["A.C"], {})
        assert result is None

    def test_rebus_plain(self):
        rebus = {"1": xdlint.RebusExpansion(across=["ONE"], down=["ONE"])}
        result = self._validate("ONEB", [(0, 0), (0, 1)], ["1B"], rebus, 0)
        assert result is None

    def test_rebus_inline_directional_form(self):
        # 1=IE/EI; declared answer can embed both inline as "STOOLEI/IE"
        rebus = {"1": xdlint.RebusExpansion(across=["IE"], down=["EI"])}
        # Single-cell across slot with the declared answer using inline form.
        result = self._validate("IE/EI", [(0, 0)], ["1"], rebus, 0)
        assert result is None

    def test_rebus_variable_length_alts_match_longest_first(self):
        """Regression test for the alt-by-length sort fix.
        With alts ['A','AB'] for a Schrödinger cell, declared answer 'AB'
        must match the longer alt; greedy short-first would consume only
        'A' and then misalign the rest of the slot."""
        rebus = {"1": xdlint.RebusExpansion(across=["A", "AB"], down=["A", "AB"])}
        # Single-cell slot, declared "AB" must match the AB alt cleanly.
        result = self._validate("AB", [(0, 0)], ["1"], rebus, 0)
        assert result is None


class TestGetHeaderAndGridGet:
    def test_get_header_case_insensitive(self):
        parsed = xdlint.parse("Title: T\nauthor: A\n\n\nAB\n\n\nA1. x ~ AB\n")
        assert xdlint.get_header(parsed, "title") == "T"
        assert xdlint.get_header(parsed, "AUTHOR") == "A"
        assert xdlint.get_header(parsed, "missing") is None

    def test_grid_get_out_of_bounds_is_block(self):
        grid = [xdlint.GridRow(line=1, cells="AB")]
        assert xdlint.grid_get(grid, -1, 0) == "#"
        assert xdlint.grid_get(grid, 1, 0) == "#"
        assert xdlint.grid_get(grid, 0, 5) == "#"
        assert xdlint.grid_get(grid, 0, 0) == "A"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class TestParser:
    def test_implicit_mode_basic(self):
        parsed = xdlint.parse(SIMPLE)
        assert parsed.section_mode == "implicit"
        assert {h.key for h in parsed.headers} == {"Title", "Author", "Date"}
        assert len(parsed.grid) == 3
        assert len(parsed.clues) == 4

    def test_explicit_mode_detected(self):
        text = (
            "## Metadata\n"
            "Title: T\n"
            "## Grid\n"
            "ABC\n"
            "## Clues\n"
            "A1. x ~ ABC\n"
        )
        parsed = xdlint.parse(text)
        assert parsed.section_mode == "explicit"
        assert len(parsed.grid) == 1
        assert len(parsed.clues) == 1

    def test_unspaced_tilde_in_answer_uses_spaced_separator(self):
        """Regression: when both ' ~ ' and a bare '~' appear, the spaced
        form should be the answer separator. Without the fix, rfind('~')
        would split inside the answer."""
        text = SIMPLE.replace(
            "A1. First ~ ABC",
            "A1. body ~ ANS~WER",
        )
        parsed = xdlint.parse(text)
        a1 = next(c for c in parsed.clues if c.pos == "A1")
        assert a1.body == "body"
        assert a1.answer == "ANS~WER"

    def test_bare_tilde_falls_back(self):
        text = SIMPLE.replace("A1. First ~ ABC", "A1. body~ABC")
        parsed = xdlint.parse(text)
        a1 = next(c for c in parsed.clues if c.pos == "A1")
        assert a1.body == "body"
        assert a1.answer == "ABC"

    def test_implicit_recovery_metadata_to_grid(self):
        """Missing 2-blank separator between metadata and grid: parser
        should auto-advance and emit XD019."""
        text = (
            "Title: T\n"
            "Date: 2024-01-01\n"
            "ABC\n"
            "D#E\n"
            "FGH\n"
            "\n"
            "\n"
            "A1. x ~ ABC\n"
            "A3. y ~ FGH\n"
            "D1. z ~ ADF\n"
            "D2. w ~ CEH\n"
        )
        parsed = xdlint.parse(text)
        assert any(f.code == "XD019" for f in parsed.parse_errors)
        assert len(parsed.grid) == 3

    def test_explicit_unknown_section_recorded_not_in_notes(self):
        """_unknown sections should populate ParsedXd.unknown_sections,
        not silently land in notes_text. (Regression for the original
        comment vs. behavior mismatch.)"""
        text = (
            "## Metadata\n"
            "Title: T\n"
            "## Foo\n"
            "this content should not become notes\n"
            "## Notes\n"
            "actual notes\n"
        )
        parsed = xdlint.parse(text)
        assert ("this content should not become notes"
                not in parsed.notes_text)
        assert "actual notes" in parsed.notes_text
        assert any(name == "Foo" for _, name in parsed.unknown_sections)

    def test_clue_metadata_anchored(self):
        text = SIMPLE.replace(
            "A1. First ~ ABC\n",
            "A1. First ~ ABC\nA1 ^Refs: D1\n",
        )
        parsed = xdlint.parse(text)
        a1 = next(c for c in parsed.clues if c.pos == "A1")
        assert a1.metadata.get("refs") == "D1"

    def test_clue_metadata_misplaced_emits_xd021(self):
        text = "## Clues\nA9 ^Refs: D1\n"  # no preceding clue
        parsed = xdlint.parse(text)
        assert any(f.code == "XD021" for f in parsed.parse_errors)

    def test_clue_with_no_dot_emits_xd012(self):
        text = (
            "## Metadata\nTitle: T\n## Grid\nAB\n## Clues\n"
            "this is not a clue line ~ ANSWER\n"
        )
        parsed = xdlint.parse(text)
        assert any(f.code == "XD012" for f in parsed.parse_errors)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class TestErrorRules:
    def test_xd001_non_rectangular(self):
        text = SIMPLE.replace("D#E", "D#")
        f = run_rule("XD001", text)
        assert any("row width" in finding.message for finding in f)

    def test_xd001_clean_grid_silent(self):
        assert run_rule("XD001", SIMPLE) == []

    def test_xd002_unrecognized_grid_char(self):
        text = SIMPLE.replace("D#E", "D@E")  # '@' not a known cell char
        f = run_rule("XD002", text)
        assert any("'@'" in x.message for x in f)

    def test_xd002_silent_on_declared_rebus(self):
        text = (
            "Title: T\nDate: 2024-01-01\nRebus: 1=ONE\n\n\n"
            "1B\n\n\n"
            "A1. x ~ ONEB\n"
        )
        # '1' is a declared rebus key; XD002 must not fire on it.
        f = run_rule("XD002", text)
        assert f == []

    def test_xd003_rebus_key_unused(self):
        text = (
            "Title: T\nDate: 2024-01-01\nRebus: 1=ONE 2=TWO\n\n\n"
            "1B\n\n\n"
            "A1. x ~ ONEB\n"
        )
        f = run_rule("XD003", text)
        assert any("'2'" in x.message for x in f)

    def test_xd004_clue_with_no_slot(self):
        text = SIMPLE + "A99. extra ~ XXX\n"
        f = run_rule("XD004", text)
        assert any("A99" in x.message for x in f)

    def test_xd005_count_match_clean(self):
        """SIMPLE has 4 slots and 4 distinct clue positions; no finding."""
        assert run_rule("XD005", SIMPLE) == []

    def test_xd005_does_not_bail_on_cluegroup_clue(self):
        """Regression: a single non-A/D clue used to skip XD005 entirely.
        Now XD005 should still compare A/D positions to slot count."""
        # Add an X1 cluegroup clue, then *also* drop a real D clue so the
        # count actually mismatches. Without the fix, the X1 clue would
        # silence the rule.
        text = SIMPLE.replace("D2. Down two ~ CEH\n", "")
        text += "X1. cluegroup ~ XXX\n"
        f = run_rule("XD005", text)
        assert len(f) == 1
        assert "3" in f[0].message and "4" in f[0].message  # 3 positions vs 4 slots

    def test_xd006_too_short_answer(self):
        text = SIMPLE.replace("A1. First ~ ABC", "A1. First ~ AB")
        f = run_rule("XD006", text)
        assert any("A1" in x.message for x in f)

    def test_xd007_letter_mismatch(self):
        text = SIMPLE.replace("A1. First ~ ABC", "A1. First ~ AXC")
        f = run_rule("XD007", text)
        assert any("A1" in x.message for x in f)

    def test_xd008_duplicate_clue_position(self):
        text = SIMPLE.replace(
            "A1. First ~ ABC",
            "A1. First ~ ABC\nA1. duplicate ~ ABC",
        )
        f = run_rule("XD008", text)
        assert any("A1" in x.message and "duplicat" in x.message for x in f)

    def test_xd008_allowed_for_schrodinger(self):
        """Two clues at the same position are legal when the slot has a
        Schrödinger cell in that direction."""
        text = (
            "Title: T\nDate: 2024-01-01\nRebus: 1=A|B\n\n\n"
            "1XY\n\n\n"
            "A1. reading one ~ AXY\n"
            "A1. reading two ~ BXY\n"
            "D1. d one ~ A\n"
        )
        # Note: D1 is length 1 so won't be a slot; pretend it's there for clue count
        # but XD008 itself shouldn't flag the A1 duplication.
        f = run_rule("XD008", text)
        assert f == []

    def test_xd701_filename_date_mismatch(self):
        f = run_rule("XD701", SIMPLE, filename="puz2018-01-01.xd")
        assert any("2018" in x.message and "2024" in x.message for x in f)

    def test_xd701_silent_when_dates_match(self):
        f = run_rule("XD701", SIMPLE, filename="puz2024-01-01.xd")
        assert f == []

    def test_xd010_c1_codepoint(self):
        text = SIMPLE.replace("Title: T", "Title: Tfoo")
        f = run_rule("XD010", text)
        assert any("U+0091" in x.message for x in f)

    def test_xd010_finding_lists_both_candidates(self):
        # Finding should show cp1252 and Mac Roman candidates so the
        # user can pick when --fix declines to auto-fix.
        text = SIMPLE.replace("Title: T", "Title: Tfoo")
        f = run_rule("XD010", text)
        assert any("cp1252:" in x.message and "Mac Roman:" in x.message
                   for x in f)

    def test_xd010_finding_undefined_cp1252(self):
        # U+009D is undefined in cp1252; finding should say so but
        # still show the Mac Roman candidate.
        text = SIMPLE.replace("Title: T", "Title: Tfoo")
        f = run_rule("XD010", text)
        assert any("cp1252: undefined" in x.message
                   and "Mac Roman:" in x.message for x in f)

    def test_xd011_html_entity(self):
        text = SIMPLE.replace("Title: T", "Title: T &amp; U")
        f = run_rule("XD011", text)
        assert any("&amp;" in x.message for x in f)

    def test_xd014_broken_ref(self):
        text = SIMPLE.replace(
            "A1. First ~ ABC\n",
            "A1. First ~ ABC\nA1 ^Refs: D99\n",
        )
        f = run_rule("XD014", text)
        assert any("D99" in x.message for x in f)

    def test_xd016_no_letters_in_grid(self):
        text = SIMPLE.replace("ABC\nD#E\nFGH", "###\n###\n###")
        f = run_rule("XD016", text)
        assert any("no answer cells" in x.message for x in f)

    def test_xd017_malformed_clue_position(self):
        text = SIMPLE.replace("A1. First ~ ABC", "A1x. First ~ ABC")
        f = run_rule("XD017", text)
        assert any("A1x" in x.message for x in f)

    def test_xd020_missing_required_section(self):
        text = "Title: T\nDate: 2024-01-01\n"  # no grid, no clues
        f = run_rule("XD020", text)
        msgs = " ".join(x.message for x in f)
        assert "no grid" in msgs and "no clues" in msgs


class TestWarningRules:
    def test_xd015_answer_word_in_clue(self):
        """Only fires when answer has explicit '|' word splits."""
        text = SIMPLE.replace(
            "A1. First ~ ABC",
            "A1. The first abc letter ~ A|BC",
        )
        # Need a real word match: replace ABC slot with something that
        # has a real word.
        text = (
            "Title: T\nDate: 2024-01-01\n\n\n"
            "ABCDE\n\n\n"
            "A1. The cat sat ~ THE|CAT|SAT\n"
            "D1. _ ~ A\n"
            "D2. _ ~ B\n"
            "D3. _ ~ C\n"
            "D4. _ ~ D\n"
            "D5. _ ~ E\n"
        )
        f = run_rule("XD015", text)
        assert any("'cat'" in x.message or "'the'" in x.message
                   or "'sat'" in x.message for x in f)

    def test_xd018_multiple_tilde(self):
        text = SIMPLE.replace("A1. First ~ ABC", "A1. body ~ extra ~ ABC")
        f = run_rule("XD018", text)
        assert len(f) == 1

    def test_xd101_backslash_in_clue(self):
        text = SIMPLE.replace("A1. First ~ ABC", "A1. has\\bs ~ ABC")
        f = run_rule("XD101", text)
        assert len(f) == 1
        assert "col" in f[0].message

    def test_xd101_column_uses_original_line_offset(self):
        """Regression: col was previously reported relative to the stripped
        clue, so leading whitespace shifted the value. Now it uses the
        original line."""
        # Spec doesn't allow leading whitespace on clue lines, but the
        # parser handles it; the rule's col should still be correct.
        text = SIMPLE.replace(
            "A1. First ~ ABC",
            "    A1. has\\bs ~ ABC",
        )
        f = run_rule("XD101", text)
        assert len(f) == 1
        # 'col' should account for the 4 leading spaces. The '\' is at
        # index 11 in the original line ("    A1. has\bs..."), so col=12.
        assert "col 12" in f[0].message

    def test_xd102_extra_blank_lines(self):
        # Implicit mode auto-advances past 2 blanks in clues, so this rule
        # only meaningfully fires under explicit '## Clues' markers.
        text = (
            "## Metadata\nTitle: T\n"
            "## Grid\nABC\n"
            "## Clues\n"
            "A1. one ~ ABC\n"
            "\n\n\n"
            "A3. two ~ ABC\n"
        )
        f = run_rule("XD102", text)
        assert len(f) >= 1

    def test_xd103_editor_folded_into_author(self):
        text = SIMPLE.replace("Author: A", "Author: A / Ed. B")
        f = run_rule("XD103", text)
        assert len(f) == 1

    def test_xd104_non_standard_special(self):
        text = SIMPLE.replace("Author: A", "Author: A\nSpecial: weird")
        f = run_rule("XD104", text)
        assert any("'weird'" in x.message for x in f)

    def test_xd105_non_iso_date(self):
        text = SIMPLE.replace("Date: 2024-01-01", "Date: 1/1/2024")
        f = run_rule("XD105", text)
        assert len(f) == 1

    def test_xd106_missing_date(self):
        text = SIMPLE.replace("Date: 2024-01-01\n", "")
        f = run_rule("XD106", text)
        assert len(f) == 1

    def test_xd107_duplicate_header(self):
        text = SIMPLE.replace("Author: A", "Author: A\nAuthor: B")
        f = run_rule("XD107", text)
        assert any("Author" in x.message for x in f)

    def test_xd108_missing_title(self):
        text = SIMPLE.replace("Title: T\n", "")
        f = run_rule("XD108", text)
        assert len(f) == 1

    def test_xd110_indented_section_header(self):
        text = "  ## Metadata\nTitle: T\n## Grid\nAB\n## Clues\nA1. x ~ AB\n"
        f = run_rule("XD110", text)
        assert len(f) == 1

    def test_xd111_non_canonical_header(self):
        text = SIMPLE.replace("Author: A", "Author: A\nFoo: bar")
        f = run_rule("XD111", text)
        assert any("'Foo'" in x.message for x in f)


class TestInfoRules:
    def test_xd013_missing_refs_metadata(self):
        text = SIMPLE.replace(
            "A1. First ~ ABC",
            "A1. See 3-Across ~ ABC",
        )
        f = run_rule("XD013", text)
        assert len(f) == 1

    def test_xd013_silent_with_refs(self):
        text = SIMPLE.replace(
            "A1. First ~ ABC",
            "A1. See 3-Across ~ ABC\nA1 ^Refs: A3",
        )
        f = run_rule("XD013", text)
        assert f == []

    def test_xd201_trailing_whitespace(self):
        text = SIMPLE.replace("Title: T\n", "Title: T   \n")
        f = run_rule("XD201", text)
        assert len(f) == 1

    def test_xd202_headers_out_of_order(self):
        text = (
            "Date: 2024-01-01\n"
            "Title: T\n"
            "\n\n"
            "AB\n"
            "\n\n"
            "A1. x ~ AB\n"
        )
        f = run_rule("XD202", text)
        assert any("Title" in x.message for x in f)

    def test_xd203_leading_whitespace_grid(self):
        text = SIMPLE.replace("ABC\nD#E\nFGH", "  ABC\n  D#E\n  FGH")
        f = run_rule("XD203", text)
        assert len(f) == 3

    def test_xd204_tab_character(self):
        text = SIMPLE.replace("Title: T", "Title:\tT")
        f = run_rule("XD204", text)
        assert len(f) == 1

    def test_xd205_limited_charset(self):
        text = (
            "Title: T\nDate: 2024-01-01\n\n\n"
            "AAA\nA#A\nAAA\n\n\n"
            "A1. x ~ AAA\n"
            "A3. y ~ AAA\n"
            "D1. z ~ AAA\n"
            "D2. w ~ AAA\n"
        )
        f = run_rule("XD205", text)
        assert any("1 distinct" in x.message for x in f)

    def test_xd206_unrecognized_clue_meta_key(self):
        text = SIMPLE.replace(
            "A1. First ~ ABC\n",
            "A1. First ~ ABC\nA1 ^Hint: a hint\n",
        )
        f = run_rule("XD206", text)
        assert any("'hint'" in x.message for x in f)

    def test_xd207_unknown_section(self):
        text = (
            "## Metadata\nTitle: T\n"
            "## Mystery\ncontent\n"
            "## Grid\nAB\n"
            "## Clues\nA1. x ~ AB\n"
        )
        f = run_rule("XD207", text)
        assert any("Mystery" in x.message for x in f)


class TestFeatureDetectionRules:
    """XD3xx rules: announce feature usage so the corpus can be searched.
    Each rule fires once per file when the feature is present, never on
    SIMPLE (which uses no special features)."""

    def test_simple_emits_no_feature_findings(self):
        for code in ("XD301", "XD302", "XD303", "XD304", "XD305",
                     "XD306", "XD307"):
            assert run_rule(code, SIMPLE) == [], f"{code} fired on SIMPLE"

    def test_xd301_uses_rebus(self):
        text = (
            "Title: T\nDate: 2024-01-01\nRebus: 1=ONE\n\n\n"
            "1B\n\n\n"
            "A1. x ~ ONEB\n"
        )
        f = run_rule("XD301", text)
        assert len(f) == 1 and "Rebus" in f[0].message

    def test_xd302_uses_special(self):
        text = SIMPLE.replace("Author: A\n", "Author: A\nSpecial: shaded\n")
        f = run_rule("XD302", text)
        assert len(f) == 1 and "Special" in f[0].message

    def test_xd303_uses_clue_metadata(self):
        text = SIMPLE.replace(
            "A1. First ~ ABC\n",
            "A1. First ~ ABC\nA1 ^Refs: A3\n",
        )
        f = run_rule("XD303", text)
        assert len(f) == 1 and "clue-metadata" in f[0].message

    def test_xd304_uses_clue_markup(self):
        text = SIMPLE.replace(
            "A1. First ~ ABC",
            "A1. {/italic/} clue ~ ABC",
        )
        f = run_rule("XD304", text)
        assert len(f) == 1 and "{/italic/}" in f[0].message

    def test_xd305_uses_cluegroup_via_header(self):
        text = SIMPLE.replace(
            "Author: A\n",
            "Author: A\nCluegroup: X=Theme\n",
        )
        f = run_rule("XD305", text)
        assert len(f) == 1 and "Cluegroup" in f[0].message

    def test_xd306_uses_quantum_rebus_directional(self):
        text = (
            "Title: T\nDate: 2024-01-01\nRebus: 1=IE/EI\n\n\n"
            "1B\n\n\n"
            "A1. x ~ IEB\n"
        )
        f = run_rule("XD306", text)
        assert len(f) == 1 and "directional" in f[0].message

    def test_xd306_uses_quantum_rebus_schrodinger(self):
        text = (
            "Title: T\nDate: 2024-01-01\nRebus: 1=A|B\n\n\n"
            "1XY\n\n\n"
            "A1. r1 ~ AXY\n"
        )
        f = run_rule("XD306", text)
        assert len(f) == 1 and "Schr" in f[0].message

    def test_xd307_uses_notes(self):
        text = (
            "## Metadata\nTitle: T\n## Grid\nAB\n## Clues\nA1. x ~ AB\n"
            "## Notes\nsome notes content\n"
        )
        f = run_rule("XD307", text)
        assert len(f) == 1


class TestSeverityChanges:
    """Lock in the severity changes from this round so they can't drift."""

    def test_xd101_is_debug(self):
        sev = next(s for (c, s, _, _, _) in xdlint.RULES if c == "XD101")
        assert sev == xdlint.Severity.DEBUG

    def test_xd018_is_debug(self):
        sev = next(s for (c, s, _, _, _) in xdlint.RULES if c == "XD018")
        assert sev == xdlint.Severity.DEBUG

    def test_xd103_is_info(self):
        sev = next(s for (c, s, _, _, _) in xdlint.RULES if c == "XD103")
        assert sev == xdlint.Severity.INFO

    def test_xd111_is_info(self):
        sev = next(s for (c, s, _, _, _) in xdlint.RULES if c == "XD111")
        assert sev == xdlint.Severity.INFO

    def test_xd204_is_warning(self):
        sev = next(s for (c, s, _, _, _) in xdlint.RULES if c == "XD204")
        assert sev == xdlint.Severity.WARNING

    def test_xd205_is_warning(self):
        sev = next(s for (c, s, _, _, _) in xdlint.RULES if c == "XD205")
        assert sev == xdlint.Severity.WARNING

    def test_debug_rank_below_info(self):
        assert (xdlint.Severity.DEBUG.rank
                < xdlint.Severity.INFO.rank
                < xdlint.Severity.WARNING.rank
                < xdlint.Severity.ERROR.rank)


# ---------------------------------------------------------------------------
# Fixers
# ---------------------------------------------------------------------------

class TestFixers:
    def test_xd010_mojibake(self):
        # U+0091 (cp1252 left single quote U+2018) — the canonical mojibake.
        text = "Title: T\n"
        new, n = xdlint.FIXERS["XD010"][1](text)
        assert n == 1
        assert "‘" in new
        assert "" not in new

    def test_xd010_fix_macroman_e_acute(self):
        # U+008E is Mac Roman é, not cp1252 Ž. Override produces é.
        text = "Czanne\n"
        new, n = xdlint.FIXERS["XD010"][1](text)
        assert n == 1
        assert new == "Cézanne\n"

    def test_xd010_fix_utf8_trailer_smart_quote(self):
        # U+0080 followed by another C1 control = trailing bytes of
        # \xe2\x80\xXX. Reconstruct the original UTF-8 character.
        text = "say hi\n"
        new, n = xdlint.FIXERS["XD010"][1](text)
        assert n == 2
        assert new == "say “hi”\n"

    def test_xd010_fix_skips_ambiguous_single(self):
        # U+0080 alone: cp1252 says € but corpus shows °/$/÷ too.
        # Leave for manual fix; finding still surfaces.
        text = "90 on a compass\n"
        new, n = xdlint.FIXERS["XD010"][1](text)
        assert n == 0
        assert text == new

    def test_xd010_fix_orphan_smart_quote_trailer(self):
        # U+009C/U+009D after a straight " is a stray UTF-8 trailer
        # byte from a smart quote whose lead bytes were already turned
        # into the straight ". Strip the trailer.
        text = '"Beyond the Sea" singer\n'
        new, n = xdlint.FIXERS["XD010"][1](text)
        assert n == 1
        assert new == '"Beyond the Sea" singer\n'

    def test_xd010_fix_orphan_open_quote_trailer(self):
        # U+009C is the trailer for left curly quote; same pattern.
        text = '"hello"\n'
        new, n = xdlint.FIXERS["XD010"][1](text)
        assert n == 2
        assert new == '"hello"\n'

    def test_xd010_fix_does_not_strip_lone_u009d(self):
        # U+009D NOT preceded by a straight " is unusual; leave it alone
        # so the finding stays visible for manual review.
        text = 'foobar\n'
        new, n = xdlint.FIXERS["XD010"][1](text)
        assert n == 0
        assert new == text

    def test_xd011_html_entity_unescape(self):
        text = "Title: A &amp; B\n"
        new, n = xdlint.FIXERS["XD011"][1](text)
        assert n == 1
        assert "&" in new and "&amp;" not in new

    def test_xd110_dedent_section_header(self):
        text = "  ## Metadata\nTitle: T\n"
        new, n = xdlint.FIXERS["XD110"][1](text)
        assert n == 1
        assert new.startswith("## Metadata")

    def test_xd203_dedent_grid_row(self):
        text = SIMPLE.replace("ABC\nD#E\nFGH", "  ABC\n  D#E\n  FGH")
        new, n = xdlint.FIXERS["XD203"][1](text)
        assert n == 3
        assert "  ABC" not in new

    def test_xd204_tabs_to_spaces(self):
        text = "Title:\tT\n"
        new, n = xdlint.FIXERS["XD204"][1](text)
        assert n == 1
        assert "\t" not in new

    def test_xd201_trim_trailing_whitespace(self):
        text = "Title: T   \n"
        new, n = xdlint.FIXERS["XD201"][1](text)
        assert n == 1
        assert new == "Title: T\n"

    def test_xd201_preserves_crlf(self):
        text = "Title: T   \r\n"
        new, _ = xdlint.FIXERS["XD201"][1](text)
        assert new == "Title: T\r\n"

    def test_xd107_drop_duplicate_keeps_first(self):
        text = "Title: First\nTitle: Second\n\n\nAB\n\n\nA1. x ~ AB\n"
        new, n = xdlint.FIXERS["XD107"][1](text)
        assert n == 1
        assert "First" in new and "Second" not in new

    def test_xd102_collapse_blank_runs_in_clues(self):
        # Explicit mode so the parser preserves the run inside clues.
        text = (
            "## Metadata\nTitle: T\n"
            "## Grid\nABC\n"
            "## Clues\n"
            "A1. one ~ ABC\n"
            "\n\n\n"
            "A3. two ~ ABC\n"
        )
        new, n = xdlint.FIXERS["XD102"][1](text)
        assert n == 1
        assert "\n\n\n" not in new
        assert "A1. one ~ ABC\n\nA3. two" in new

    def test_xd013_synthesize_refs(self):
        text = SIMPLE.replace(
            "A1. First ~ ABC",
            "A1. See 3-Across ~ ABC",
        )
        new, n = xdlint.FIXERS["XD013"][1](text)
        assert n == 1
        assert "A1 ^Refs: A3" in new

    def test_xd202_reorder_headers(self):
        text = (
            "Date: 2024-01-01\n"
            "Title: T\n"
            "\n\nAB\n\n\nA1. x ~ AB\n"
        )
        new, _ = xdlint.FIXERS["XD202"][1](text)
        # Title should now come before Date.
        title_pos = new.index("Title:")
        date_pos = new.index("Date:")
        assert title_pos < date_pos


class TestXD103Fixer:
    """The XD103 fixer is the trickiest one: it splits 'Author: X / Ed. Y'
    and also has to delete sibling Author lines itself (the previously
    buggy XD107 interaction)."""

    def test_simple_split(self):
        text = SIMPLE.replace("Author: A", "Author: Smith / Ed. Jones")
        new, _ = xdlint.FIXERS["XD103"][1](text)
        assert "Author: Smith" in new
        assert "Editor: Jones" in new

    def test_dirty_author_first_with_plain_sibling(self):
        text = SIMPLE.replace(
            "Author: A",
            "Author: Smith / Ed. Jones\nAuthor: Plain Other",
        )
        new, _ = xdlint.FIXERS["XD103"][1](text)
        assert "Author: Smith" in new
        assert "Editor: Jones" in new
        # The plain sibling Author should be deleted by the fixer itself.
        assert "Author: Plain Other" not in new

    def test_dirty_author_not_first_keeps_cleaned_one(self):
        """The headline regression: if XD107 ran after XD103 and the dirty
        Author wasn't the first one, XD107 would keep the wrong line."""
        text = SIMPLE.replace(
            "Author: A",
            "Author: Plain First\nAuthor: Smith / Ed. Jones",
        )
        new, _ = xdlint.FIXERS["XD103"][1](text)
        assert "Author: Smith" in new
        assert "Editor: Jones" in new
        # The plain first Author must be removed; the cleaned one must
        # survive.
        assert "Author: Plain First" not in new

    def test_existing_editor_with_different_value_skipped(self):
        text = SIMPLE.replace(
            "Author: A",
            "Author: Smith / Ed. Jones\nEditor: Existing",
        )
        new, n = xdlint.FIXERS["XD103"][1](text)
        # Conservative: don't clobber a non-matching existing Editor.
        assert n == 0
        assert new == text

    def test_existing_editor_matching_value_still_runs(self):
        text = SIMPLE.replace(
            "Author: A",
            "Author: Smith / Ed. Jones\nEditor: Jones",
        )
        new, n = xdlint.FIXERS["XD103"][1](text)
        # Author gets cleaned; Editor stays.
        assert n >= 1
        assert "Author: Smith" in new
        assert "Editor: Jones" in new


class TestApplyFixesPipeline:
    def test_idempotent_on_clean_file(self):
        new, counts = xdlint.apply_fixes(SIMPLE, None, unsafe_ok=False)
        assert new == SIMPLE
        assert counts == {}

    def test_idempotence_after_fix(self):
        text = SIMPLE.replace("Title: T", "  ## Metadata\nTitle: T   ")
        # First pass should fix; second pass should be a no-op.
        once, _ = xdlint.apply_fixes(text, None, unsafe_ok=False)
        twice, counts = xdlint.apply_fixes(once, None, unsafe_ok=False)
        assert once == twice
        assert counts == {}

    def test_xd103_then_xd107_pipeline(self):
        """End-to-end: dirty Author not first, with both fixers running.
        After the pipeline we want one Author (the cleaned one), one Editor,
        no duplicates."""
        text = SIMPLE.replace(
            "Author: A",
            "Author: Plain First\nAuthor: Smith / Ed. Jones",
        )
        new, _ = xdlint.apply_fixes(text, None, unsafe_ok=False)
        # Exactly one Author: line; it should be the cleaned one.
        author_lines = [ln for ln in new.splitlines() if ln.startswith("Author:")]
        assert author_lines == ["Author: Smith"]
        assert any(ln.startswith("Editor: Jones") for ln in new.splitlines())

    def test_pipeline_respects_active_codes(self):
        text = "Title: T   \n\n\nAB\n\n\nA1. x ~ AB\n"
        # Restrict to XD201 only.
        new, counts = xdlint.apply_fixes(text, {"XD201"}, unsafe_ok=False)
        assert "XD201" in counts
        assert "Title: T\n" in new


# ---------------------------------------------------------------------------
# CLI / driver
# ---------------------------------------------------------------------------

def run_main(args):
    """Invoke xdlint.main() with custom argv. Returns (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    saved_argv = sys.argv
    sys.argv = ["xdlint"] + list(args)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = xdlint.main()
            except SystemExit as e:
                code = e.code or 0
    finally:
        sys.argv = saved_argv
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def tmp_xd_file(tmp_path):
    """Write SIMPLE to a tmp .xd file and return its path."""
    p = tmp_path / "src2024-01-01.xd"
    p.write_text(SIMPLE, encoding="utf-8")
    return str(p)


class TestCLI:
    def test_clean_file_exits_zero(self, tmp_xd_file):
        code, _out, _err = run_main([tmp_xd_file])
        assert code == 0

    def test_error_in_file_exits_one(self, tmp_path):
        # Non-rectangular grid => XD001 (error) => exit 1 at default gate.
        bad = SIMPLE.replace("D#E", "D#")
        p = tmp_path / "src2024-01-01.xd"
        p.write_text(bad, encoding="utf-8")
        code, out, _err = run_main([str(p)])
        assert code == 1
        assert "XD001" in out

    def test_max_severity_warning_gates_warnings(self, tmp_path):
        text = SIMPLE.replace("Date: 2024-01-01", "Date: 1/1/2024")
        p = tmp_path / "src2024-01-01.xd"
        p.write_text(text, encoding="utf-8")
        # Default gate (warning): a warning trips it.
        code, _, _ = run_main([str(p)])
        assert code == 1
        # Loosened to error gate: warnings stop tripping it.
        code, _, _ = run_main([str(p), "--max-severity", "error"])
        assert code == 0

    def test_disable_preserves_parser_findings(self, tmp_path):
        """Regression: --disable used to silence parser-level findings
        because they aren't in RULES. The fix unions PARSER_LEVEL_FINDINGS
        codes back into the active set."""
        # Missing 2-blank separator triggers XD019 from the parser.
        text = (
            "Title: T\nDate: 2024-01-01\n"
            "ABC\nD#E\nFGH\n"
            "\n\n"
            "A1. x ~ ABC\nA3. y ~ FGH\n"
            "D1. z ~ ADF\nD2. w ~ CEH\n"
        )
        p = tmp_path / "src2024-01-01.xd"
        p.write_text(text, encoding="utf-8")
        # Disable an unrelated rule; XD019 should still appear.
        code, out, _ = run_main([str(p), "--disable", "XD201"])
        assert "XD019" in out

    def test_no_experimental_preserves_parser_findings(self, tmp_path):
        """Regression: --no-experimental had the same silencing bug as
        --disable. Fixed in the same way."""
        text = (
            "Title: T\nDate: 2024-01-01\n"
            "ABC\nD#E\nFGH\n"
            "\n\n"
            "A1. x ~ ABC\nA3. y ~ FGH\n"
            "D1. z ~ ADF\nD2. w ~ CEH\n"
        )
        p = tmp_path / "src2024-01-01.xd"
        p.write_text(text, encoding="utf-8")
        code, out, _ = run_main([str(p), "--no-experimental"])
        assert "XD019" in out

    def test_enable_only_restricts(self, tmp_path):
        text = SIMPLE.replace("Title: T\n", "Title: T   \n")
        p = tmp_path / "src2024-01-01.xd"
        p.write_text(text, encoding="utf-8")
        # --enable-only XD201: only trailing whitespace should fire.
        # XD201 is INFO so we also need to lower the gate from the
        # default (warning) to surface it in output.
        # (Other rules might want to fire but should be filtered.)
        code, out, _ = run_main([str(p), "--enable-only", "XD201",
                                 "--max-severity", "info"])
        assert "XD201" in out
        # Pick a rule that *would* fire if active (XD202 would fire only
        # if headers were out of order; it shouldn't matter here either way).
        # Use XD110 as a sentinel: not present in this file, so absent
        # regardless. Better: verify only XD201 codes appear.
        emitted = set()
        for line in out.splitlines():
            for tok in line.split("\t"):
                if tok.startswith("XD"):
                    emitted.add(tok)
        assert emitted <= {"XD201"}

    def test_list_rules_mentions_parser_level(self, capsys):
        code, out, _ = run_main(["--list-rules"])
        assert code == 0
        assert "XD019" in out  # parser-level
        assert "XD001" in out  # rule-level

    def test_default_gate_suppresses_info_in_output(self, tmp_path):
        """With the default --max-severity=warning, INFO-level findings
        should be filtered from stdout (in addition to not tripping the
        exit gate)."""
        text = SIMPLE.replace("Author: A\n", "Author: A\nSpecial: shaded\n")
        p = tmp_path / "src2024-01-01.xd"
        p.write_text(text, encoding="utf-8")
        code, out, _ = run_main([str(p)])
        # XD302 (uses-special) is INFO; should not print at default gate.
        assert "XD302" not in out
        # ...but should appear at info gate.
        code, out, _ = run_main([str(p), "--max-severity", "info"])
        assert "XD302" in out

    def test_debug_gate_surfaces_debug_findings(self, tmp_path):
        text = SIMPLE.replace("A1. First ~ ABC", "A1. body ~ extra ~ ABC")
        p = tmp_path / "src2024-01-01.xd"
        p.write_text(text, encoding="utf-8")
        # XD018 is DEBUG; not visible at default warning gate.
        code, out, _ = run_main([str(p)])
        assert "XD018" not in out
        # Surfaces at debug gate.
        code, out, _ = run_main([str(p), "--max-severity", "debug"])
        assert "XD018" in out

    def test_decode_findings_for_non_utf8(self, tmp_path):
        p = tmp_path / "src2024-01-01.xd"
        # Write raw bytes that include an invalid UTF-8 byte.
        p.write_bytes(b"Title: T\xff\n\n\nAB\n\n\nA1. x ~ AB\n")
        code, out, _ = run_main([str(p)])
        assert "XD022" in out


class TestFixCLI:
    """End-to-end coverage for the --fix runner: writes to disk, --diff,
    --show-fixes, and the XD022-decode-skip safety check."""

    def test_fix_writes_to_disk(self, tmp_path):
        text = SIMPLE.replace("Title: T\n", "Title: T   \n")
        p = tmp_path / "src2024-01-01.xd"
        p.write_text(text, encoding="utf-8")
        code, _, err = run_main([str(p), "--fix"])
        assert "Title: T   " not in p.read_text(encoding="utf-8")
        assert "Title: T" in p.read_text(encoding="utf-8")
        assert "fixed" in err

    def test_fix_diff_mode_does_not_write(self, tmp_path):
        text = SIMPLE.replace("Title: T\n", "Title: T   \n")
        p = tmp_path / "src2024-01-01.xd"
        original_bytes = text.encode("utf-8")
        p.write_bytes(original_bytes)
        code, out, _err = run_main([str(p), "--diff"])
        # File on disk unchanged.
        assert p.read_bytes() == original_bytes
        # Diff printed to stdout.
        assert "---" in out and "+++" in out
        # Diff mode exits 1 when there are changes.
        assert code == 1

    def test_fix_diff_clean_file_exits_zero(self, tmp_xd_file):
        code, out, _ = run_main([tmp_xd_file, "--diff"])
        assert code == 0
        assert out == ""

    def test_fix_show_fixes_lists_codes(self, tmp_path):
        text = SIMPLE.replace("Title: T\n", "Title: T   \n")
        p = tmp_path / "src2024-01-01.xd"
        p.write_text(text, encoding="utf-8")
        code, _out, err = run_main([str(p), "--fix", "--show-fixes"])
        assert "XD201" in err

    def test_fix_skips_files_with_xd022(self, tmp_path):
        p = tmp_path / "src2024-01-01.xd"
        p.write_bytes(b"Title: T\xff\n\n\nAB\n\n\nA1. x ~ AB\n")
        code, _out, err = run_main([str(p), "--fix"])
        # File on disk should still contain the bad byte.
        assert b"\xff" in p.read_bytes()
        assert "skip" in err

    def test_fix_incompatible_with_base(self, tmp_xd_file):
        code, _out, err = run_main([tmp_xd_file, "--fix", "--base", "HEAD"])
        # argparse.error exits with status 2 and prints to stderr.
        assert code != 0
        assert "incompatible" in err


class TestNonUtf8Decode:
    """The _decode_with_findings helper round-trips into ParsedXd's
    parse_errors so the rest of the linter can keep running."""

    def test_pure_utf8_no_findings(self):
        text, findings = xdlint._decode_with_findings(b"Title: T\n")
        assert findings == []
        assert text == "Title: T\n"

    def test_invalid_byte_emits_xd022(self):
        text, findings = xdlint._decode_with_findings(b"Title: T\xff\n")
        assert len(findings) == 1
        assert findings[0].code == "XD022"
        assert "�" in text  # replacement char
