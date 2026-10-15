"""receipts.jsonl transition: metadatabase reads receipts.jsonl (falling back
to receipts.tsv) and appends to both; validate-receipts.py reads either."""
import importlib.util
import json
import os
import subprocess

import pytest

from xdfile import metadatabase as metadb

HEADER = "CaptureTime\tReceivedTime\tExternalSource\tInternalSource\tSourceFilename\txdid\n"
ROWS = [
    ["2016-05-27", "2016-05-27", '"Saul Pwanson" <saul＠saul.pw>', "e.zip", "nyw1913-12-21.xd", "nyw1913-12-21"],
    ["2015-01-19", "2016-05-29", "x", "eltana.zip", "unfinished grids/é.puz", ""],
]
NEW = ["2026-10-15", "2026-10-15", "https://example.com/", "20261015-www.zip", "abc261014.puz", "abc2026-10-14"]


def tsv(rows):
    return HEADER + "".join("\t".join(r) + "\n" for r in rows)


def jsonl(rows, **extra):
    return "".join(json.dumps({**dict(zip(metadb.RECEIPT_COLUMNS, r)), **extra},
                              ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows)


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _reset():
    for fn in (metadb.receipts_rows, metadb.xd_receipts_rows, metadb._receipts_by_source, metadb._receipts_by_xdid):
        fn.cache.clear()
    for fp in metadb._open_tables.values():
        fp.close()
    metadb._open_tables.clear()


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.mkdir("gxd")
    _reset()
    yield tmp_path
    _reset()


# --- reader ---

def test_reads_tsv_when_no_jsonl(corpus):
    write(metadb.RECEIPTS_TSV, tsv(ROWS))
    rows = metadb.receipts_rows()
    assert [r.SourceFilename for r in rows] == [r[4] for r in ROWS]
    assert metadb.check_already_received("x", ROWS[1][4])[0].xdid == ""


def test_prefers_jsonl_and_keeps_optional_fields(corpus):
    write(metadb.RECEIPTS_TSV, tsv(ROWS))
    write(metadb.RECEIPTS_JSONL, jsonl(ROWS, method="download"))
    rows = metadb.receipts_rows()
    assert [r.method for r in rows] == ["download", "download"]
    assert [[r[k] for k in metadb.RECEIPT_COLUMNS] for r in rows] == ROWS
    assert metadb.latest_receipt_for_xdid("nyw1913-12-21").ExternalSource == ROWS[0][2]


def test_jsonl_only(corpus):
    write(metadb.RECEIPTS_JSONL, jsonl(ROWS))
    assert len(metadb.receipts_rows()) == 2


def test_falls_back_to_tsv_when_jsonl_is_behind(corpus):
    """A branch appended to receipts.tsv alone: don't lose those rows."""
    write(metadb.RECEIPTS_TSV, tsv(ROWS + [NEW]))
    write(metadb.RECEIPTS_JSONL, jsonl(ROWS))
    rows = metadb.receipts_rows()
    assert len(rows) == 3
    assert metadb.check_already_received(NEW[2], NEW[4])


def test_tsv_and_jsonl_readers_agree(corpus):
    write(metadb.RECEIPTS_TSV, tsv(ROWS))
    from_tsv = [dict(r) for r in metadb.receipts_rows()]
    _reset()
    write(metadb.RECEIPTS_JSONL, jsonl(ROWS))
    assert [dict(r) for r in metadb.receipts_rows()] == from_tsv


# --- writer ---

def test_append_receipt_writes_both(corpus):
    write(metadb.RECEIPTS_TSV, tsv(ROWS))
    write(metadb.RECEIPTS_JSONL, jsonl(ROWS))
    metadb.append_receipt(NEW)
    metadb.append_receipt(ROWS[1][:5] + [None], disposition="unfinished")
    _reset()
    assert read(metadb.RECEIPTS_TSV) == tsv(ROWS + [NEW, ROWS[1]])
    assert read(metadb.RECEIPTS_JSONL) == jsonl(ROWS + [NEW]) + jsonl([ROWS[1]], disposition="unfinished")


def test_append_receipt_jsonl_line_is_canonical():
    line = metadb.receipt_jsonl_line(NEW, xd_sha256="0" * 64, method="download", color="blue", source_id="")
    assert line == ('{"CaptureTime":"2026-10-15","ReceivedTime":"2026-10-15",'
                    '"ExternalSource":"https://example.com/","InternalSource":"20261015-www.zip",'
                    '"SourceFilename":"abc261014.puz","xdid":"abc2026-10-14",'
                    '"method":"download","xd_sha256":"' + "0" * 64 + '"}\n')


def test_append_receipt_does_not_start_a_partial_jsonl(corpus):
    """A gxd checkout from before receipts.jsonl: write the TSV only, so the
    sync script can later build receipts.jsonl from the whole TSV."""
    write(metadb.RECEIPTS_TSV, tsv(ROWS))
    metadb.append_receipt(NEW)
    _reset()
    assert read(metadb.RECEIPTS_TSV) == tsv(ROWS + [NEW])
    assert not os.path.exists(metadb.RECEIPTS_JSONL)


def test_append_receipt_after_tsv_is_retired(corpus):
    write(metadb.RECEIPTS_JSONL, jsonl(ROWS))
    metadb.append_receipt(NEW)
    _reset()
    assert read(metadb.RECEIPTS_JSONL) == jsonl(ROWS + [NEW])
    assert not os.path.exists(metadb.RECEIPTS_TSV)


def test_append_receipt_new_corpus_gets_both(corpus):
    metadb.append_receipt(NEW)
    metadb.append_receipt(ROWS[0])
    _reset()
    assert read(metadb.RECEIPTS_TSV) == tsv([NEW, ROWS[0]])
    assert read(metadb.RECEIPTS_JSONL) == jsonl([NEW, ROWS[0]])


def test_append_receipt_repairs_missing_final_newline(corpus):
    write(metadb.RECEIPTS_TSV, tsv(ROWS))
    write(metadb.RECEIPTS_JSONL, jsonl(ROWS)[:-1])
    metadb.append_receipt(NEW)
    _reset()
    assert read(metadb.RECEIPTS_JSONL) == jsonl(ROWS + [NEW])


# --- validate-receipts.py ---

def _load_validate():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "validate-receipts.py")
    spec = importlib.util.spec_from_file_location("validate_receipts", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(*args):
    subprocess.run(["git", *args], check=True, capture_output=True)


def _commit(files, msg):
    for path, text in files.items():
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        write(path, text)
    _git("add", "-A")
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", msg)


@pytest.mark.parametrize("with_tsv", [True, False])
def test_validate_receipts_reads_jsonl(tmp_path, monkeypatch, capsys, with_tsv):
    vr = _load_validate()
    monkeypatch.chdir(tmp_path)
    _git("init", "-q")
    base_files = {"receipts.jsonl": jsonl(ROWS[:1]), "nyworld/nyw1913-12-21.xd": "x"}
    if with_tsv:
        base_files["receipts.tsv"] = tsv(ROWS[:1])
    _commit(base_files, "base")
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()

    # a new puzzle whose receipt is in receipts.jsonl: passes
    files = {"receipts.jsonl": jsonl(ROWS[:1] + [NEW]), "abc/abc2026-10-14.xd": "x"}
    if with_tsv:
        files["receipts.tsv"] = tsv(ROWS[:1] + [NEW])
    _commit(files, "good")
    monkeypatch.setattr("sys.argv", ["v", "--base", base])
    vr.main()
    assert "1 new receipts row(s), 1 new .xd file(s)" in capsys.readouterr().out

    # a new puzzle with a receipt in receipts.tsv only: fails on receipts.jsonl
    if with_tsv:
        files = {"receipts.tsv": tsv(ROWS[:1] + [NEW, ROWS[1][:5] + ["zzz2026-01-01"]]),
                 "zzz/zzz2026-01-01.xd": "x"}
        _commit(files, "tsv only")
        with pytest.raises(SystemExit):
            vr.main()
        assert "no receipts.jsonl row has xdid 'zzz2026-01-01'" in capsys.readouterr().err

    # a malformed jsonl line
    _commit({"receipts.jsonl": read("receipts.jsonl") + "not json\n"}, "bad")
    with pytest.raises(SystemExit):
        vr.main()
    assert "not a JSON object" in capsys.readouterr().err
