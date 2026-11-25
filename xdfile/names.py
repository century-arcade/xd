"""People's names: the names tables, and what they say a printed name is.

gxd's EDITORIAL.md, "People's names": `Author:` and `Editor:` name people,
`Byline:` keeps the author credit as printed. Who is the same person is
decided in the names tables, `names.tsv` files at two levels: a shelf's table
(`<shelf>/names.tsv`, how that publication credits people) and the corpus's
table (`names.tsv` at the root, facts about a person wherever printed). A name
is looked up in its shelf's table first, then the corpus's.

Columns: byline, person, kind, status, pub, role, start, end, qid, source,
note. Only `confirmed` rows of kind `variant` or `misspelling` rewrite a
name; `former`, `pen` and `house` names are kept as printed (the row links
them to the person), and a `likely` row never rewrites. The optional scope
narrows a row: `pub` (space-separated pubids), `role` (author or editor),
`start` and `end` (dates, inclusive; a year or year-month covers all of it).

Fetching and converting never resolve names; normalizing is an import step
between converting and committing (xdlint XD812 --fix, --profile gxd).
xdlint.py carries a copy of this logic, since it stays standalone;
tests/test_xdlint.py checks that the two agree.

    from xdfile import names
    tables = names.load_names("gxd/puzzmo")
    names.resolve("brooke", tables, pub="pzmo", role="author", date="2023-10-16")
    # 'Brooke Husic'
"""

import csv
import os
import re
import unicodedata

COLUMNS = ["byline", "person", "kind", "status", "pub", "role", "start", "end",
           "qid", "source", "note"]

# Kinds that rewrite a name to the person's own spelling of it. Former, pen and
# house names are different names, the credit someone chose, and stay as
# printed; their rows only say who it is.
REWRITE_KINDS = {"variant", "misspelling"}

# How Author: and Editor: join names; kept as they are when names change.
JOIN_RE = re.compile(r"(, | and | & )")


def name_key(name):
    """What two spellings of one name share: case, accents and punctuation
    aside ("Erik Agard" = "erik agard", "William A. Lewis, Jr." = "William A.
    Lewis Jr."). From crossref's crossref/names.py."""
    s = "".join(c for c in unicodedata.normalize("NFKD", name)
                if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s.lower())).strip()


def read_table(path):
    """One names.tsv -> {name_key(byline): [row, ...]}; {} if there is none.
    Rows keep every column, as stripped strings ('' when empty)."""
    out = {}
    try:
        f = open(path, encoding="utf-8", newline="")
    except FileNotFoundError:
        return out
    with f:
        for row in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            row = {k: (row.get(k) or "").strip() for k in COLUMNS}
            if row["byline"] and row["person"]:
                out.setdefault(name_key(row["byline"]), []).append(row)
    return out


def _corpus_root(start):
    """The nearest directory at or above `start` holding .git (a clone or a
    worktree); None if there is none."""
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def table_paths(shelf, root=None):
    """The names.tsv paths that apply to a directory, nearest first: the
    shelf's own, any above it (a shelf inside another, indie/vasquez), and
    the corpus root's last. `root` defaults to the enclosing git checkout;
    without one, only the shelf's own table."""
    shelf = os.path.abspath(shelf)
    root = os.path.abspath(root) if root else _corpus_root(shelf)
    paths = []
    if root is None or not (shelf + os.sep).startswith(root.rstrip(os.sep) + os.sep):
        return [os.path.join(shelf, "names.tsv")]
    d = shelf
    while True:
        paths.append(os.path.join(d, "names.tsv"))
        if d == root:
            return paths
        d = os.path.dirname(d)


_TABLES = {}


def load_names(shelf, root=None):
    """The names tables for a shelf directory, nearest first (see
    table_paths); a missing file is an empty table. Cached per path."""
    tables = []
    for p in table_paths(shelf, root):
        if p not in _TABLES:
            _TABLES[p] = read_table(p)
        tables.append(_TABLES[p])
    return tables


def _date_in(date, start, end):
    """Is `date` (YYYY-MM-DD) within [start, end]? Either bound may be
    missing, or partial (a year, a year-month), covering all of it."""
    if not (start or end):
        return True
    if not date:
        return False
    if start and date[:len(start)] < start:
        return False
    if end and date[:len(end)] > end:
        return False
    return True


def row_applies(row, pub=None, role=None, date=None):
    """Does this row rewrite a name printed in this pub, role and date?"""
    if row["status"] != "confirmed" or row["kind"] not in REWRITE_KINDS:
        return False
    if row["pub"] and (pub or "").lower() not in row["pub"].lower().split():
        return False
    if row["role"] and (role or "").lower() != row["role"].lower():
        return False
    return _date_in(date or "", row["start"], row["end"])


def resolve(name, tables, pub=None, role=None, date=None):
    """The person a printed name is, by the first table that has a row for
    it that applies; None if no table says, or the table's rows that apply
    disagree. `tables` is what load_names() returns, or a shelf directory."""
    if isinstance(tables, (str, os.PathLike)):
        tables = load_names(tables)
    key = name_key(name)
    if not key:
        return None
    for table in tables:
        people = {r["person"] for r in table.get(key, ())
                  if row_applies(r, pub, role, date)}
        if len(people) == 1:
            return people.pop()
        if people:
            return None
    return None


def normalize(value, tables, pub=None, role=None, date=None):
    """An Author: or Editor: value with each name a table resolves written
    as the person, the joining (", ", " and ", " & ") kept. A value a table
    resolves whole ("Fran and Lou Sabin" as one row) is taken whole."""
    whole = resolve(value, tables, pub, role, date)
    if whole is not None:
        return whole
    parts = JOIN_RE.split(value)
    for i in range(0, len(parts), 2):
        person = resolve(parts[i], tables, pub, role, date)
        if person is not None:
            parts[i] = person
    return "".join(parts)
