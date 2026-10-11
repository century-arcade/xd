"""Tests for xdlint's v4-draft support: format version detection (XD401-
XD403, --report-version, --only-version, --warn-v4/--warn-deprecated) and
the '## Design' section (parser, XD410-XD414).
"""
import io
import sys
import textwrap
from contextlib import redirect_stderr, redirect_stdout

import pytest

import xdlint


@pytest.fixture(autouse=True)
def _clear_slot_cache():
    xdlint._SLOT_CACHE.clear()
    yield
    xdlint._SLOT_CACHE.clear()


def make_ctx(text, filename="t.xd"):
    return xdlint.Ctx(filename=filename, text=text, parsed=xdlint.parse(text))


def findings(text, codes):
    ctx = make_ctx(text)
    return [f for f in xdlint.run_checks(ctx, set(codes))]


def codes(text, codes_):
    return [f.code for f in findings(text, codes_)]


def version(text):
    return xdlint.detect_version(xdlint.parse(text))


def run_main(args):
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


# 3x3, one block at the center. A1=ABC, A3=FGH, D1=ADF, D2=CEH.
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


def with_clue(body):
    return SIMPLE.replace("A1. First ~ ABC", f"A1. {body} ~ ABC")


def with_header(line):
    return SIMPLE.replace("Date: 2024-01-01", f"Date: 2024-01-01\n{line}")


HEADED = textwrap.dedent("""\
    ## Metadata

    Title: T
    Author: A
    Date: 2024-01-01

    ## Grid

    ABC
    D#E
    FGH

    ## Clues

    A1. First ~ ABC
    A3. Second ~ FGH

    D1. Down one ~ ADF
    D2. Down two ~ CEH

    ## Design

    {design}
""")


def headed(design):
    return HEADED.replace("{design}", textwrap.dedent(design).strip())


CLEAN_DESIGN = """\
    O { background: circle }
    S { background: shaded }

    O.S
    ...
    ..O
"""


# ---------------------------------------------------------------------------
# Version detection
# ---------------------------------------------------------------------------

class TestDetectVersion:
    def test_plain_file_is_common(self):
        info = version(SIMPLE)
        assert info.label == "common"
        assert info.v4 == {} and info.v3 == {}

    def test_v3_markup_alone_is_common(self):
        assert version(with_clue("{/Italic/} and {*bold*}")).label == "common"

    @pytest.mark.parametrize("body,feature", [
        ("H{~2~}O", "subscript"),
        ("E=mc{^2^}", "superscript"),
        ("{=Small caps=}", "small-caps"),
        ("See {@this | href: https://example.com@}", "link"),
        ("{!Whale | src: 'data:image/png;base64,AA=='!}", "image"),
        (r"What {\~\} means", "literal"),
        (r"Line one{\\}line two", "literal"),
        ("The {#red | x-color: #c00000#} planet", "color"),
    ])
    def test_v4_span_in_clue(self, body, feature):
        info = version(with_clue(body))
        assert info.label == "v4"
        assert feature in info.v4

    def test_unclosed_span_is_not_a_signal(self):
        assert version(with_clue("Open {^ brace")).label == "common"

    def test_markup_in_metadata_value(self):
        info = version(SIMPLE.replace("Title: T", "Title: {/Moby-Dick/}"))
        assert info.label == "v4"
        assert "metadata-markup" in info.v4

    def test_repeated_rebus_key(self):
        info = version(with_header("Rebus: 1=O 1=A"))
        assert "rebus-repeated-key" in info.v4

    def test_pipe_rebus_is_not_v4(self):
        assert version(with_header("Rebus: 1=O|A")).label == "common"

    def test_design_section(self):
        info = version(headed(CLEAN_DESIGN))
        assert info.label == "v4"
        assert "design-section" in info.v4

    def test_special_header_is_v3(self):
        info = version(with_header("Special: circle"))
        assert info.label == "v3"
        assert "special-header" in info.v3

    def test_cluegroup_is_v3(self):
        assert "cluegroup" in version(with_header("Cluegroup: X")).v3

    def test_dot_cell_is_v3(self):
        info = version(SIMPLE.replace("D#E", "D.E"))
        assert "dot-cell" in info.v3

    def test_both_is_mixed(self):
        text = with_header("Special: circle").replace(
            "A1. First ~ ABC", "A1. H{~2~}O ~ ABC")
        assert version(text).label == "mixed"

    def test_declared_v4_without_features(self):
        info = version(with_header("XdVersion: v4-exp"))
        assert info.label == "v4"
        assert info.declared == "v4-exp"

    def test_features_override_declared(self):
        text = with_header("XdVersion: v4-exp\nSpecial: circle")
        assert version(text).label == "v3"


class TestVersionRules:
    def test_xd401_info_per_feature(self):
        text = with_clue("H{~2~}O and E=mc{^2^}")
        fs = findings(text, {"XD401"})
        assert [f.severity for f in fs] == [xdlint.Severity.INFO] * 2
        assert "subscript" in fs[0].message and "superscript" in fs[1].message

    def test_xd402_info(self):
        fs = findings(with_header("Special: shaded"), {"XD402"})
        assert len(fs) == 1 and fs[0].severity == xdlint.Severity.INFO

    def test_xd403_bad_value(self):
        assert codes(with_header("XdVersion: four"), {"XD403"}) == ["XD403"]

    @pytest.mark.parametrize("value", ["4", "v4", "v4-exp", "4.0", "v4.0-draft"])
    def test_xd403_good_values(self, value):
        assert codes(with_header(f"XdVersion: {value}"), {"XD403"}) == []

    def test_xdversion_is_canonical_header(self):
        assert codes(with_header("XdVersion: v4"), {"XD111", "XD202"}) == []

    def test_promote(self):
        ctx = make_ctx(with_clue("H{~2~}O"))
        fs = list(xdlint.run_checks(ctx, {"XD401"},
                                    {"XD401": xdlint.Severity.WARNING}))
        assert [f.severity for f in fs] == [xdlint.Severity.WARNING]

    def test_repeated_rebus_key_validates_both_readings(self):
        text = textwrap.dedent("""\
            Title: T
            Author: A
            Date: 2024-01-01
            Rebus: 1=O 1=A


            C1NE
            ARES
            TEST


            A1. Sugar ___ ~ CONE
            A5. Gods of war ~ ARES
            A6. Exam ~ TEST

            D1. Feline ~ CAT
            D2. Mineral ~ ORE
            D3. Abbr. ~ NES
            D4. Dir. ~ EST
        """)
        assert codes(text, {"XD006", "XD007"}) == []
        assert xdlint.parse_rebus_header("1=O 1=A")["1"].across == ["O", "A"]


# ---------------------------------------------------------------------------
# Design section: parsing
# ---------------------------------------------------------------------------

class TestDesignParsing:
    def test_headed_design_is_its_own_section(self):
        p = xdlint.parse(headed(CLEAN_DESIGN))
        assert p.section_mode == "explicit"
        assert p.design_line > 0
        assert [raw for _ln, raw in p.design][0] == "O { background: circle }"
        assert len(p.clues) == 4 and len(p.grid) == 3
        assert p.notes_text == ""
        assert p.unknown_sections == []

    def test_headed_design_no_xd207(self):
        assert codes(headed(CLEAN_DESIGN), {"XD207"}) == []

    def test_trailing_design_in_headingless_file(self):
        text = SIMPLE + "\n\nA note.\n\n## Design\n\n" + textwrap.dedent(CLEAN_DESIGN)
        p = xdlint.parse(text)
        assert p.section_mode == "implicit"
        assert len(p.grid) == 3 and len(p.clues) == 4
        assert p.notes_text == "A note."
        assert len(p.design) == 5
        assert codes(text, {"XD410"}) == ["XD410"]
        assert codes(text, {"XD411", "XD412", "XD413", "XD414", "XD019",
                            "XD020"}) == []

    def test_headed_file_no_xd410(self):
        assert codes(headed(CLEAN_DESIGN), {"XD410"}) == []

    def test_text_before_first_heading_read_headingless(self):
        text = SIMPLE + "\n\n## Notes\n\nA note.\n"
        p = xdlint.parse(text)
        assert p.section_mode == "explicit"
        assert [h.key for h in p.headers] == ["Title", "Author", "Date"]
        assert len(p.grid) == 3 and len(p.clues) == 4
        assert p.notes_text == "A note."
        assert codes(text, {"XD019", "XD020"}) == []

    def test_metadata_before_grid_heading(self):
        text = "Title: T\nAuthor: A\n\n## Grid" + HEADED.split("## Grid", 1)[1]
        p = xdlint.parse(text)
        assert [h.key for h in p.headers] == ["Title", "Author"]
        assert len(p.grid) == 3 and len(p.clues) == 4

    def test_design_heading_case_insensitive(self):
        p = xdlint.parse(headed(CLEAN_DESIGN).replace("## Design", "## DESIGN"))
        assert p.design_line > 0

    def test_parse_design_styles_and_grid(self):
        d = xdlint.parse_design([(10, "A, B { background: circle; bar-top: true; }"),
                                 (11, "A { bar-left: true }"),
                                 (12, "AB."),
                                 (13, "...")])
        assert d.errors == []
        assert d.styles["A"] == {"background": (10, "circle"),
                                 "bar-top": (10, "true"),
                                 "bar-left": (11, "true")}
        assert set(d.styles["B"]) == {"background", "bar-top"}
        assert [r.cells for r in d.grid] == ["AB.", "..."]

    def test_parse_design_multiline_rule(self):
        d = xdlint.parse_design([(1, "A {"), (2, "  background: circle;"),
                                 (3, "  bar-top: true;"), (4, "}"), (5, "A")])
        assert d.errors == []
        assert d.styles["A"]["bar-top"] == (1, "true")
        assert [r.line for r in d.grid] == [5]

    def test_parse_design_quoted_value_keeps_delimiters(self):
        url = "url('data:image/png;base64,iVBORw0KGgo=')"
        d = xdlint.parse_design([(1, f"I {{ background-image: {url}; background-size: 2 2 }}"),
                                 (2, "I.")])
        assert d.errors == []
        assert d.styles["I"]["background-image"] == (1, url)
        assert d.styles["I"]["background-size"] == (1, "2 2")


# ---------------------------------------------------------------------------
# Design section: rules
# ---------------------------------------------------------------------------

DESIGN_RULES = {"XD410", "XD411", "XD412", "XD413", "XD414"}


class TestDesignRules:
    def test_clean_design(self):
        assert codes(headed(CLEAN_DESIGN), DESIGN_RULES) == []

    def test_spec_example_properties(self):
        design = """\
            A { background: circle; bar-top: true }
            B { background-image: url('https://example.com/p.png'); background-size: 2 2 }
            C { bar-left: true; x-background-color: #c0392b }

            AB.
            ...
            C..
        """
        assert codes(headed(design), DESIGN_RULES) == []

    def test_wrong_row_count(self):
        design = "O { background: circle }\n\nO..\n..."
        assert codes(headed(design), {"XD412"}) == ["XD412"]

    def test_wrong_row_width(self):
        design = "O { background: circle }\n\nO..\n....\n..."
        fs = findings(headed(design), {"XD412"})
        assert len(fs) == 1 and "width 4" in fs[0].message

    def test_styles_without_grid(self):
        assert codes(headed("O { background: circle }"), {"XD412"}) == ["XD412"]

    def test_undefined_style(self):
        design = "O { background: circle }\n\nO.Q\n...\n..Q"
        fs = findings(headed(design), {"XD413"})
        assert len(fs) == 1 and "'Q'" in fs[0].message

    def test_unknown_property(self):
        design = "O { colour: red }\n\nO..\n...\n..."
        fs = findings(headed(design), {"XD414"})
        assert len(fs) == 1 and "colour" in fs[0].message

    def test_x_property_accepted(self):
        design = "O { x-anything: whatever }\n\nO..\n...\n..."
        assert codes(headed(design), {"XD414"}) == []

    @pytest.mark.parametrize("decl", [
        "background: square",
        "bar-top: yes",
        "background-size: 0 2",
        "background-image: url(https://example.com/unquoted.png)",
    ])
    def test_bad_values(self, decl):
        design = f"O {{ {decl} }}\n\nO..\n...\n..."
        assert codes(headed(design), {"XD414"}) == ["XD414"]

    def test_comma_in_value(self):
        design = "O { background-size: 2, 2 }\n\nO..\n...\n..."
        fs = findings(headed(design), {"XD411"})
        assert len(fs) == 1 and "comma" in fs[0].message

    def test_unclosed_rule(self):
        design = "O { background: circle\n\nO..\n...\n..."
        fs = findings(headed(design), {"XD411"})
        assert len(fs) == 1 and "closing" in fs[0].message

    def test_missing_colon(self):
        design = "O { background circle }\n\nO..\n...\n..."
        assert codes(headed(design), {"XD411"}) == ["XD411"]

    def test_empty_design(self):
        text = HEADED.replace("{design}", "")
        assert codes(text, {"XD411"}) == ["XD411"]


class TestFixersLeaveDesignAlone:
    def test_xd209_skips_design(self):
        design = "O {  background: circle }\n\nO..\n...\n..."
        text = headed(design)
        assert codes(text, {"XD209"}) == []
        new, _counts = xdlint.apply_fixes(text, {"XD209"}, False)
        assert new == text

    def test_xd011_skips_design(self):
        design = "B { background-image: url('https://x.test/a?b=1&amp;c=2') }\n\nB..\n...\n..."
        text = headed(design)
        assert codes(text, {"XD011"}) == []
        new, _counts = xdlint.apply_fixes(text, {"XD011"}, False)
        assert new == text

    def test_xd011_still_fixes_clues_in_headed_file(self):
        text = headed(CLEAN_DESIGN).replace("A1. First", "A1. Fish &amp; chips")
        new, counts = xdlint.apply_fixes(text, {"XD011"}, False)
        assert "Fish & chips" in new and counts.get("XD011") == 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@pytest.fixture
def corpus(tmp_path):
    files = {
        "common.xd": SIMPLE,
        "v4.xd": with_clue("H{~2~}O"),
        "v3.xd": with_header("Special: circle"),
        "mixed.xd": with_header("Special: circle").replace(
            "A1. First ~ ABC", "A1. H{~2~}O ~ ABC"),
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


class TestVersionCLI:
    def test_report_version(self, corpus):
        code, out, err = run_main(["--report-version", str(corpus)])
        assert code == 0
        rows = {line.split("\t")[0].rsplit("/", 1)[-1]: line.split("\t")[1:]
                for line in out.splitlines()}
        assert rows["common.xd"] == ["common", "v4=-", "v3=-"]
        assert rows["v4.xd"] == ["v4", "v4=subscript", "v3=-"]
        assert rows["v3.xd"] == ["v3", "v4=-", "v3=special-header"]
        assert rows["mixed.xd"][0] == "mixed"
        assert "4 file(s): v3 1, v4 1, mixed 1, common 1" in err

    def test_report_version_shows_declared(self, tmp_path):
        p = tmp_path / "d.xd"
        p.write_text(with_header("XdVersion: v4-exp"), encoding="utf-8")
        _code, out, _err = run_main(["--report-version", str(p)])
        assert out.rstrip().endswith("\tXdVersion=v4-exp")

    def test_only_version_filters(self, corpus):
        _code, out, _err = run_main(["--report-version", "--only-version",
                                     "v4,mixed", str(corpus)])
        names = sorted(line.split("\t")[0].rsplit("/", 1)[-1]
                       for line in out.splitlines())
        assert names == ["mixed.xd", "v4.xd"]

    def test_only_version_bad_label(self, corpus):
        code, _out, err = run_main(["--only-version", "v5", str(corpus)])
        assert code == 2 and "v5" in err

    def test_v4_passes_by_default(self, corpus):
        code, out, _err = run_main([str(corpus / "v4.xd")])
        assert code == 0 and "XD401" not in out

    def test_warn_v4(self, corpus):
        code, out, _err = run_main(["--warn-v4", str(corpus / "v4.xd")])
        assert code == 1
        assert "\twarning\tXD401\t" in out

    def test_warn_deprecated(self, corpus):
        code, out, _err = run_main(["--warn-deprecated", str(corpus / "v3.xd")])
        assert code == 1
        assert "\twarning\tXD402\t" in out

    def test_only_version_with_lint(self, corpus):
        code, out, _err = run_main(["--warn-v4", "--only-version", "common",
                                    str(corpus)])
        assert code == 0 and out == ""
