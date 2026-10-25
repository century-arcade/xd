"""gxd source archives: the MANIFEST.tsv and NOTES.md that travel with a .zip of originals.

gxd's CONTRIBUTING.md ("Source archives") asks that every archive backing
receipts.tsv rows hold the original files at their SourceFilename paths, a
MANIFEST.tsv (filename, sha256, bytes, source_url, fetched_at) and a NOTES.md.
gxd's scripts/make-source-archive.py --verify checks the result.
"""

import csv
import datetime
import hashlib
import os
import platform
import re
import subprocess
import time

MANIFEST = 'MANIFEST.tsv'
NOTES = 'NOTES.md'
MANIFEST_COLUMNS = ['filename', 'sha256', 'bytes', 'source_url', 'fetched_at']


def utc_iso8601(timet=None):
    if timet is None:
        timet = time.time()
    return datetime.datetime.fromtimestamp(int(timet), datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def manifest_row(filename, data, source_url='', fetched_at=''):
    return {
        'filename': filename,
        'sha256': hashlib.sha256(data).hexdigest(),
        'bytes': str(len(data)),
        'source_url': source_url or '',
        'fetched_at': fetched_at or '',
    }


def manifest_tsv(rows):
    lines = ['\t'.join(MANIFEST_COLUMNS)]
    for r in rows:
        lines.append('\t'.join(str(r.get(c, '')).replace('\t', ' ') for c in MANIFEST_COLUMNS))
    return '\n'.join(lines) + '\n'


def _basename(fn):
    # also splits find_files_with_time's "outer.zip:inner/path" names
    return re.split(r'[/\\:]', fn)[-1]


def is_manifest(fn):
    return _basename(fn) == MANIFEST


def is_archive_metadata(fn):
    """True for files in a source archive that aren't puzzle sources (manifest, notes, logs, tsvs)."""
    base = _basename(fn)
    return base in (MANIFEST, NOTES) or base.endswith('.tsv') or base.endswith('.log')


def read_manifest(contents):
    """Parse MANIFEST.tsv text into {filename: row dict}; values are left as strings."""
    if isinstance(contents, bytes):
        contents = contents.decode('utf-8')
    rows = {}
    for row in csv.DictReader(contents.splitlines(), delimiter='\t', quoting=csv.QUOTE_NONE):
        fn = (row.get('filename') or '').replace('\\', '/')
        if fn:
            rows[fn] = {k: (v or '') for k, v in row.items() if k}
    return rows


def git_commit(repodir):
    try:
        out = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repodir, capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return os.environ.get('GITHUB_SHA', '')


def package_version(name):
    """Installed version of a package, with the VCS commit when it was installed from git."""
    try:
        import importlib.metadata as md
        import json
        dist = md.distribution(name)
    except Exception:
        return 'not installed'
    ver = dist.version
    try:
        direct = json.loads(dist.read_text('direct_url.json') or '{}')
        vcs = direct.get('vcs_info', {})
        if vcs.get('commit_id'):
            ver += ' (%s@%s)' % (direct.get('url', ''), vcs['commit_id'])
    except Exception:
        pass
    return ver


def job_description(environ=None):
    """Which job made this archive: a GitHub Actions run (with its URL), or the droplet cron / a manual run."""
    env = os.environ if environ is None else environ
    if env.get('GITHUB_ACTIONS') == 'true' or env.get('GITHUB_RUN_ID'):
        url = ''
        if env.get('GITHUB_SERVER_URL') and env.get('GITHUB_REPOSITORY') and env.get('GITHUB_RUN_ID'):
            url = '%s/%s/actions/runs/%s' % (env['GITHUB_SERVER_URL'], env['GITHUB_REPOSITORY'], env['GITHUB_RUN_ID'])
        desc = 'GitHub Actions'
        if env.get('GITHUB_WORKFLOW'):
            desc += ' workflow "%s"' % env['GITHUB_WORKFLOW']
        return desc + (', run %s' % url if url else '')
    return 'host %s, not GitHub Actions (the droplet\'s nightly cron, or a manual run)' % platform.node()


class SourceArchiveWriter:
    """Wraps an OutputZipFile: records each saved puzzle and each attempt, and on finish()
    writes the log, MANIFEST.tsv and NOTES.md so the zip is a gxd source archive.

    Files go at the root of the zip, so their names in the archive are exactly the
    SourceFilename that 18-convert2xd.py records in receipts.tsv.
    """

    def __init__(self, outf, scriptname, logname=None):
        self.outf = outf
        self.scriptname = scriptname
        self.logname = logname or (scriptname + '.log')
        self.files = []     # manifest rows, plus 'requested_date' and 'pubid'
        self.attempts = []  # (pubid, requested_date, outcome, detail)
        self.started_at = utc_iso8601()

    def add_file(self, fn, content, pubid='', requested_date='', source_url='', fetched_at=None):
        timet = time.time()
        self.outf.write_file(fn, content, timet)
        row = manifest_row(fn, content, source_url, fetched_at or utc_iso8601(timet))
        row['pubid'] = pubid
        row['requested_date'] = str(requested_date or '')
        self.files.append(row)

    def attempt(self, pubid, requested_date, outcome, detail=''):
        self.attempts.append((pubid, str(requested_date), outcome, detail))

    def notes_md(self, command='', xd_commit='', xworddl_version='', job=''):
        lines = [
            '# Nightly puzzle download',
            '',
            'Puzzles fetched by xd\'s `scripts/%s.py`, the nightly downloader for gxd.' % self.scriptname,
            '',
            '- Made by: %s' % (job or job_description()),
            '- Started: %s' % self.started_at,
            '- Finished: %s' % utc_iso8601(),
            '- Command: `%s`' % command if command else '- Command: (unknown)',
            '- xd commit: %s' % (xd_commit or '(unknown)'),
            '- xword-dl version: %s' % (xworddl_version or '(unknown)'),
            '',
            '## Files',
            '',
            'Each puzzle is at the root of this zip, named `<pubid><YYYY-MM-DD>.<ext>`, which is',
            'also its `SourceFilename` in gxd\'s receipts.tsv.  The date in the name is the',
            'puzzle\'s date as reported by the source.  `MANIFEST.tsv` lists every file with',
            'its sha256, size, source URL and fetch time (UTC).',
            '',
            'Files saved via xword-dl (pubids with an `xword-dl_id` in gxd\'s sources.tsv) are',
            'xword-dl\'s .puz rendering of the publisher\'s data, not the bytes as served, so',
            'they have no `source_url`.  Files fetched directly from a `urlfmt` URL are the',
            'bytes as served from that URL.',
            '',
            '| file | pubid | requested date | source_url |',
            '|---|---|---|---|',
        ]
        for r in self.files:
            lines.append('| %s | %s | %s | %s |' % (r['filename'], r['pubid'], r['requested_date'],
                                                    r['source_url'] or '(xword-dl)'))
        if not self.files:
            lines.append('| (none) | | | |')
        lines += [
            '',
            'When the requested date differs from the date in the file name, xword-dl could',
            'not fetch the requested date and fell back to the latest available puzzle.',
            '',
            '## Attempts',
            '',
            '| pubid | requested date | outcome | detail |',
            '|---|---|---|---|',
        ]
        for pubid, date, outcome, detail in self.attempts:
            lines.append('| %s | %s | %s | %s |' % (pubid, date, outcome, detail.replace('|', '\\|').replace('\n', ' ')))
        if not self.attempts:
            lines.append('| (none) | | | |')
        lines += [
            '',
            '## Log',
            '',
            'The full run log is `%s` in this zip.' % self.logname,
            '',
        ]
        return '\n'.join(lines)

    def finish(self, log_text, **notes_kwargs):
        logdata = log_text.encode('utf-8') if isinstance(log_text, str) else log_text
        timet = time.time()
        self.outf.write_file(self.logname, logdata, timet)
        logrow = manifest_row(self.logname, logdata, '', utc_iso8601(timet))
        self.outf.write_file(NOTES, self.notes_md(**notes_kwargs).encode('utf-8'))
        self.outf.write_file(MANIFEST, manifest_tsv(self.files + [logrow]).encode('utf-8'))
