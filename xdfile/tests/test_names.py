from xdfile import names

HEAD = "\t".join(names.COLUMNS) + "\n"


def row(byline, person, kind="variant", status="confirmed", pub="", role="",
        start="", end=""):
    return "\t".join([byline, person, kind, status, pub, role, start, end,
                      "", "", ""]) + "\n"


def corpus(tmp_path, root_rows=(), shelf_rows=(), shelf="puzzmo"):
    """A corpus root (a .git dir marks it) with a shelf; returns the shelf."""
    (tmp_path / ".git").mkdir()
    d = tmp_path / shelf
    d.mkdir(parents=True)
    if root_rows is not None:
        (tmp_path / "names.tsv").write_text(HEAD + "".join(root_rows), encoding="utf-8")
    if shelf_rows is not None:
        (d / "names.tsv").write_text(HEAD + "".join(shelf_rows), encoding="utf-8")
    names._TABLES.clear()
    return d


def test_name_key_folds_case_accents_punctuation():
    assert names.name_key("Erik Agard") == names.name_key("erik  agard")
    assert names.name_key("Julie Bérubé") == "julie berube"
    assert names.name_key("William A. Lewis, Jr.") == names.name_key("William A Lewis Jr")
    assert names.name_key("./orta") == "orta"


def test_shelf_table_before_root(tmp_path):
    shelf = corpus(tmp_path, [row("Stanley", "Stanley Kubrick")],
                   [row("Stanley", "Stanley Newman")], shelf="newsday")
    assert names.resolve("stanley", shelf) == "Stanley Newman"
    assert names.resolve("Stanley", tmp_path) == "Stanley Kubrick"


def test_root_table_used_when_shelf_has_none(tmp_path):
    shelf = corpus(tmp_path, [row("B. E. Quigley", "Brendan Emmett Quigley")], None)
    assert names.resolve("B.E. Quigley", shelf) == "Brendan Emmett Quigley"


def test_both_tables_missing(tmp_path):
    shelf = corpus(tmp_path, None, None)
    assert names.load_names(shelf) == [{}, {}]
    assert names.resolve("brooke", shelf) is None


def test_nested_shelf_sees_every_table_up_to_root(tmp_path):
    shelf = corpus(tmp_path, [row("BEQ", "Brendan Emmett Quigley")],
                   [row("qv", "Quiara Vasquez")], shelf="indie/vasquez")
    year = shelf / "2024"
    year.mkdir()
    assert names.resolve("qv", year) == "Quiara Vasquez"
    assert names.resolve("BEQ", year) == "Brendan Emmett Quigley"
    assert len(names.table_paths(year)) == 4


def test_only_confirmed_rewrite_kinds(tmp_path):
    shelf = corpus(tmp_path, [], [
        row("brooke", "Brooke Husic"),
        row("Margaret Petherbridge", "Margaret Farrar", kind="former"),
        row("Shorts", "Will Shortz", kind="misspelling"),
        row("Anna Gram", "Someone", kind="pen"),
        row("Thomas Joseph", "Someone", kind="house"),
        row("maybe", "Someone", status="likely"),
    ])
    assert names.resolve("brooke", shelf) == "Brooke Husic"
    assert names.resolve("Margaret Petherbridge", shelf) == "Margaret Farrar"
    assert names.resolve("Shorts", shelf) == "Will Shortz"
    for kept in ("Anna Gram", "Thomas Joseph", "maybe", "nobody"):
        assert names.resolve(kept, shelf) is None


def test_scope_pub_role_dates(tmp_path):
    shelf = corpus(tmp_path, [], [
        row("alex", "Alex Briñas", pub="pzmo", start="2025-06-06", end="2025-06-06"),
        row("Ann", "Ann Hagerty", role="editor"),
        row("Lewis", "Joyce Nichols Lewis", pub="lat la", role="editor", start="2000", end="2000"),
    ])
    t = names.load_names(shelf)
    assert names.resolve("alex", t, "pzmo", "author", "2025-06-06") == "Alex Briñas"
    assert names.resolve("alex", t, "pzmo", "author", "2025-06-07") is None
    assert names.resolve("alex", t, "pzmomini", "author", "2025-06-06") is None
    assert names.resolve("alex", t, "pzmo", "author", None) is None
    assert names.resolve("Ann", t, "pzmo", "editor", "2024-01-01") == "Ann Hagerty"
    assert names.resolve("Ann", t, "pzmo", "author", "2024-01-01") is None
    assert names.resolve("Lewis", t, "la", "editor", "2000-07-04") == "Joyce Nichols Lewis"
    assert names.resolve("Lewis", t, "la", "editor", "2001-01-01") is None


def test_rows_that_disagree_resolve_nothing(tmp_path):
    shelf = corpus(tmp_path, [row("Jo", "Someone Else")],
                   [row("Jo", "Jo Brownbridge"), row("Jo", "Jo March")])
    assert names.resolve("Jo", shelf) is None


def test_normalize_keeps_joining(tmp_path):
    shelf = corpus(tmp_path, [], [row("brooke", "Brooke Husic"), row("./orta", "Orta Therox"),
                                  row("erik", "Erik Agard")])
    t = names.load_names(shelf)
    assert names.normalize("brooke and ./orta", t) == "Brooke Husic and Orta Therox"
    assert names.normalize("annierau, erik and bob weisz", t) == "annierau, Erik Agard and bob weisz"
    assert names.normalize("erik & brooke", t) == "Erik Agard & Brooke Husic"
    assert names.normalize("Rob Dubbin", t) == "Rob Dubbin"


def test_normalize_takes_a_whole_row_first(tmp_path):
    shelf = corpus(tmp_path, [row("Fran and Lou Sabin", "Frances Sabin and Louis Sabin"),
                              row("Lou", "Louis Sabin")], [])
    t = names.load_names(shelf)
    assert names.normalize("Fran and Lou Sabin", t) == "Frances Sabin and Louis Sabin"
