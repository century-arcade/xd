"""tests for gxd source archives: the nightly downloader's MANIFEST.tsv / NOTES.md,
and 18-convert2xd.py reading them back into receipts.tsv"""

import hashlib
import importlib.util
import os
import subprocess
import sys
import zipfile

import puz
import pytest

from xdfile import utils
from xdfile.sourcearchive import (MANIFEST, MANIFEST_COLUMNS, NOTES, SourceArchiveWriter,
                                  is_archive_metadata, job_description, manifest_tsv,
                                  manifest_row, read_manifest)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(REPO, 'scripts')


@pytest.fixture(autouse=True)
def script_args(monkeypatch):
    # OutputZipFile consults the script's parsed args
    import types
    monkeypatch.setattr(utils, 'g_args', types.SimpleNamespace(debug=False))


def make_puz(title='Test'):
    p = puz.Puzzle()
    p.width = p.height = 3
    p.solution = 'CATARETEN'
    p.fill = '-' * 9
    p.title, p.author, p.copyright = title, 'Tester', '(c)'
    p.clues = ['Feline', 'Cat', 'Pay', 'Rodent', 'Speed', 'Number']
    return p.tobytes()


class FakeZip:
    def __init__(self):
        self.files = {}

    def write_file(self, fn, contents, timet=None):
        self.files[fn] = contents


def verify_archive(path, receipts_rows=()):
    """The checks gxd's scripts/make-source-archive.py --verify makes; returns a list of errors."""
    errors = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        lines = z.read(MANIFEST).decode('utf-8').splitlines()
        if lines[0].split('\t') != MANIFEST_COLUMNS:
            errors.append('bad header')
        listed = set()
        for line in lines[1:]:
            name, sha, size = line.split('\t')[:3]
            listed.add(name)
            data = z.read(name) if name in names else None
            if data is None or hashlib.sha256(data).hexdigest() != sha or len(data) != int(size):
                errors.append(name)
        errors += sorted(names - listed - {MANIFEST, NOTES})
    archive = os.path.basename(path)
    for r in receipts_rows:
        if r['InternalSource'] == archive and r['SourceFilename'] not in listed:
            errors.append('receipts cite %s' % r['SourceFilename'])
    return errors


# --- sourcearchive module ---

def test_manifest_tsv_columns_and_checksums():
    data = b'hello'
    tsv = manifest_tsv([manifest_row('a.puz', data, 'https://x/a.puz', '2026-10-14T12:00:00Z')])
    lines = tsv.splitlines()
    assert lines[0] == '\t'.join(MANIFEST_COLUMNS)
    assert lines[1].split('\t') == ['a.puz', hashlib.sha256(data).hexdigest(), '5',
                                    'https://x/a.puz', '2026-10-14T12:00:00Z']
    assert read_manifest(tsv)['a.puz']['source_url'] == 'https://x/a.puz'


def test_is_archive_metadata():
    for fn in ('MANIFEST.tsv', 'NOTES.md', '11-download-puzzles.log', 'sources.tsv',
               '20261014-www/NOTES.md', 'x.zip:NOTES.md'):
        assert is_archive_metadata(fn), fn
    for fn in ('wsj2026-10-14.puz', 'NOTES.md.puz', 'x.zip:up2026-10-14.puz'):
        assert not is_archive_metadata(fn), fn


def test_writer_manifest_lists_puzzles_and_log():
    z = FakeZip()
    arc = SourceArchiveWriter(z, '11-download-puzzles')
    arc.add_file('wsj2026-10-14.puz', b'WSJ', pubid='wsj', requested_date='2026-10-14',
                 source_url='https://herbach.dnsalias.com/wsj/wsj261014.puz')
    arc.add_file('up2026-10-14.puz', b'UP', pubid='up', requested_date='2026-10-14')
    arc.finish('the log\n', job='test job')

    assert set(z.files) == {'wsj2026-10-14.puz', 'up2026-10-14.puz', '11-download-puzzles.log', MANIFEST, NOTES}
    rows = read_manifest(z.files[MANIFEST])
    assert set(rows) == {'wsj2026-10-14.puz', 'up2026-10-14.puz', '11-download-puzzles.log'}
    for fn, row in rows.items():
        assert row['sha256'] == hashlib.sha256(z.files[fn]).hexdigest()
        assert row['bytes'] == str(len(z.files[fn]))
        assert row['fetched_at'].endswith('Z') and 'T' in row['fetched_at']
    assert rows['wsj2026-10-14.puz']['source_url'] == 'https://herbach.dnsalias.com/wsj/wsj261014.puz'
    assert rows['up2026-10-14.puz']['source_url'] == ''  # xword-dl
    assert rows['11-download-puzzles.log']['source_url'] == ''
    assert z.files['11-download-puzzles.log'] == b'the log\n'


def test_notes_md_contents():
    z = FakeZip()
    arc = SourceArchiveWriter(z, '11-download-puzzles')
    arc.add_file('up2026-10-13.puz', b'UP', pubid='up', requested_date='2026-10-14')
    arc.attempt('up', '2026-10-14', 'saved', 'up2026-10-13.puz (latest issue, not the requested date)')
    arc.attempt('lat', '2026-10-14', 'failed', 'xword-dl: 404 | gone')
    env = {'GITHUB_ACTIONS': 'true', 'GITHUB_SERVER_URL': 'https://github.com',
           'GITHUB_REPOSITORY': 'century-arcade/xd', 'GITHUB_RUN_ID': '12345',
           'GITHUB_WORKFLOW': 'Nightly download'}
    arc.finish('log', command='11-download-puzzles.py -o x.zip', xd_commit='abc123',
               xworddl_version='2026.1', job=job_description(env))
    notes = z.files[NOTES].decode('utf-8')

    assert 'https://github.com/century-arcade/xd/actions/runs/12345' in notes
    assert 'xd commit: abc123' in notes
    assert 'xword-dl version: 2026.1' in notes
    assert '`11-download-puzzles.py -o x.zip`' in notes
    assert "not the bytes as served" in notes and 'no `source_url`' in notes
    assert '| up2026-10-13.puz | up | 2026-10-14 | (xword-dl) |' in notes
    assert '| up | 2026-10-14 | saved | up2026-10-13.puz (latest issue, not the requested date) |' in notes
    assert '| lat | 2026-10-14 | failed | xword-dl: 404 \\| gone |' in notes
    assert '`11-download-puzzles.log`' in notes


def test_job_description_outside_actions():
    desc = job_description({})
    assert 'not GitHub Actions' in desc and 'droplet' in desc


# --- 11-download-puzzles.py ---

@pytest.fixture
def downloader():
    spec = importlib.util.spec_from_file_location('download_puzzles_script',
                                                  os.path.join(SCRIPTS, '11-download-puzzles.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Src(utils.AttrDict):
    pass


def test_download_writes_source_archive(downloader, monkeypatch, tmp_path):
    import datetime
    wsj_bytes = make_puz('WSJ')
    up_puz = puz.load(make_puz('UP'))

    class Resp:
        def read(self):
            return wsj_bytes
    urls = []
    monkeypatch.setattr(downloader.urllib.request, 'urlopen', lambda url, timeout: urls.append(url) or Resp())

    def by_keyword(xwordid, date=None, filename=None):
        if date:
            raise ValueError('no puzzle for %s' % date)
        return up_puz, 'up2026-10-13.puz'  # falls back to the latest issue
    monkeypatch.setattr(downloader, 'by_keyword', by_keyword)

    sources = {
        'wsj': Src(pubid='wsj', ext='puz', freq='1', urlfmt='https://herbach.dnsalias.com/wsj/wsj%y%m%d.puz', **{'xword-dl_id': ''}),
        'up': Src(pubid='up', ext='puz', freq='1', urlfmt='', **{'xword-dl_id': 'uni'}),
        'lat': Src(pubid='lat', ext='puz', freq='1', urlfmt='', **{'xword-dl_id': 'lat'}),
    }

    zpath = str(tmp_path / '20261015-120000-www.zip')
    outf = utils.OutputZipFile(zpath, toplevel='', log=False)
    arc = SourceArchiveWriter(outf, '11-download-puzzles')
    date = datetime.date(2026, 10, 14)
    assert downloader.download_puzzles(arc, sources['wsj'], 'wsj', date, '', fallback_latest=False)
    assert downloader.download_puzzles(arc, sources['up'], 'up', date, 'uni', fallback_latest=True)
    assert not downloader.download_puzzles(arc, sources['lat'], 'lat', date, 'lat', fallback_latest=False)
    arc.finish('log\n', job='test')
    outf.close()

    assert urls == ['https://herbach.dnsalias.com/wsj/wsj261014.puz']
    with zipfile.ZipFile(zpath) as z:
        names = set(z.namelist())
        rows = read_manifest(z.read(MANIFEST))
        notes = z.read(NOTES).decode('utf-8')
        assert z.read('wsj2026-10-14.puz') == wsj_bytes
    # no top-level folder: archive paths are the receipts' SourceFilenames
    assert names == {'wsj2026-10-14.puz', 'up2026-10-13.puz', '11-download-puzzles.log', MANIFEST, NOTES}
    assert rows['wsj2026-10-14.puz']['source_url'] == 'https://herbach.dnsalias.com/wsj/wsj261014.puz'
    assert rows['up2026-10-13.puz']['source_url'] == ''
    assert '| up2026-10-13.puz | up | 2026-10-14 | (xword-dl) |' in notes
    assert '| lat | 2026-10-14 | failed | xword-dl: no puzzle for 2026-10-14 |' in notes
    assert verify_archive(zpath) == []


# --- 18-convert2xd.py ---

def run_convert2xd(workdir, zpath):
    gxd = workdir / 'gxd'
    gxd.mkdir(exist_ok=True)
    (gxd / 'pubregex.tsv').write_text('regex\tpubid\nwsj\twsj\nup\tup\n')
    env = dict(os.environ, PYTHONPATH=REPO)
    subprocess.run([sys.executable, os.path.join(SCRIPTS, '18-convert2xd.py'), '-o', 'gxd/', str(zpath)],
                   cwd=workdir, env=env, check=True, capture_output=True)
    return {r['SourceFilename']: r for r in utils.parse_tsv_data((gxd / 'receipts.tsv').read_text())}


def test_convert2xd_reads_manifest(tmp_path):
    zpath = tmp_path / '20261015-120000-www.zip'
    z = utils.OutputZipFile(str(zpath), toplevel='', log=False)
    arc = SourceArchiveWriter(z, '11-download-puzzles')
    arc.add_file('wsj2026-10-14.puz', make_puz('WSJ'), pubid='wsj', requested_date='2026-10-14',
                 source_url='https://herbach.dnsalias.com/wsj/wsj261014.puz', fetched_at='2026-10-15T12:00:01Z')
    arc.add_file('up2026-10-14.puz', make_puz('UP'), pubid='up', requested_date='2026-10-14',
                 fetched_at='2026-10-15T12:00:03Z')
    arc.finish('log\n', job='test')
    z.close()

    receipts = run_convert2xd(tmp_path, zpath)
    assert set(receipts) == {'wsj2026-10-14.puz', 'up2026-10-14.puz'}  # not NOTES.md, MANIFEST.tsv, .log
    wsj, up = receipts['wsj2026-10-14.puz'], receipts['up2026-10-14.puz']
    assert wsj['ExternalSource'] == 'https://herbach.dnsalias.com/wsj/wsj261014.puz'
    assert wsj['CaptureTime'] == '2026-10-15T12:00:01Z'
    assert up['ExternalSource'] == '20261015-120000-www.zip'  # blank source_url falls back to the zip
    assert up['CaptureTime'] == '2026-10-15T12:00:03Z'
    for r in receipts.values():
        assert r['InternalSource'] == '20261015-120000-www.zip'
    assert verify_archive(str(zpath), receipts.values()) == []


def test_convert2xd_old_zip_without_manifest_unchanged(tmp_path):
    # the pre-manifest nightly layout: everything under <timestamp>-www/, plus a .log
    zpath = tmp_path / '20261015-000311-www.zip'
    with zipfile.ZipFile(zpath, 'w') as z:
        z.writestr(zipfile.ZipInfo('20261015-000311-www/wsj2026-10-14.puz', (2026, 10, 15, 0, 3, 12)), make_puz())
        z.writestr(zipfile.ZipInfo('20261015-000311-www/11-download-puzzles.log', (2026, 10, 15, 0, 5, 0)), b'log')

    receipts = run_convert2xd(tmp_path, zpath)
    assert list(receipts) == ['wsj2026-10-14.puz']
    r = receipts['wsj2026-10-14.puz']
    assert r['ExternalSource'] == '20261015-000311-www.zip'
    assert r['InternalSource'] == '20261015-000311-www.zip'
    assert r['CaptureTime'] == '2026-10-15'
    assert r['xdid'] == 'wsj2026-10-14'
