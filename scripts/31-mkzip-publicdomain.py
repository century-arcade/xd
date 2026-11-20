#!/usr/bin/env python3

# Usage: $0 -c gxd -o xd-puzzles-publicdomain.zip [paths...]
#
# Zips the full .xd of every puzzle in the corpus that is in the US public
# domain by date: published before 1 January of (this year - 95), so before
# 1931 in 2026, 1932 in 2027. This is tier (a) of docs/DATASETS.md.
#
# Date is the only rule. A later puzzle is left out even if it is believed
# to be public domain for another reason (e.g. no renewal, as found for Judge
# 1931-1939 in docs/assessments/copyright-renewal-2026.md); add it here only
# once the maintainers have decided to publish it. Puzzles with no year are
# left out.
#
# With paths, only those .xd files are read instead of the whole corpus.

import datetime
import os
import subprocess

from xdfile import utils
from xdfile import ids
import xdfile


PD_TERM = 95  # years of US copyright for works published 1927-1977


def gxd_commit(corpusdir):
    try:
        return subprocess.run(['git', '-C', corpusdir, 'rev-parse', '--short', 'HEAD'],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def main():
    p = utils.args_parser('zip the public-domain puzzles in the corpus')
    p.add_argument('--before', type=int, default=datetime.date.today().year - PD_TERM,
                   help='include puzzles published before this year (default: this year - %d)' % PD_TERM)
    args = utils.get_args(parser=p)

    outf = utils.open_output()
    assert isinstance(outf, utils.OutputZipFile), '-o must name a .zip'
    outf.log = False
    outf.toplevel = ''

    corpusroot = os.path.dirname(os.path.abspath(args.corpusdir))
    commit = gxd_commit(args.corpusdir)

    puzzles = []
    nlater = nnoyear = nredacted = 0
    for xd in xdfile.iter_corpus():
        year = xdfile.year_from_date(ids.date(xd) or '')
        if not year:
            nnoyear += 1
            continue
        if year >= args.before:
            nlater += 1
            continue
        if xd.is_redacted():
            nredacted += 1
            continue
        puzzles.append(xd)

    puzzles.sort(key=lambda xd: (ids.date(xd), ids.xdid(xd)))
    manifest = ['xdid\tDate\tpath']
    for xd in puzzles:
        path = os.path.relpath(os.path.abspath(xd.filename), corpusroot).replace(os.sep, '/')
        with open(xd.filename, 'rb') as fp:  # the file as it is in gxd, byte for byte
            outf.write_file(path, fp.read())
        manifest.append('\t'.join([ids.xdid(xd), ids.date(xd), path]))

    source = 'gxd %s' % commit if commit else 'gxd'
    readme = f"""\
xd crossword puzzles in the public domain

{len(puzzles)} puzzles from the xd Crossword Corpus published before {args.before},
in .xd format, built from {source} on {datetime.date.today().isoformat()}.

US copyright in a work published before {args.before} has expired, so these
puzzles are in the public domain in the United States. Laws elsewhere differ.
MANIFEST.tsv lists each puzzle with its date and path.

The .xd format: https://github.com/century-arcade/xd
About the corpus and its public data: https://centuryarcade.org/xd/datasets/
"""
    outf.write_file('README', readme.encode('utf-8'))
    outf.write_file('MANIFEST.tsv', ('\n'.join(manifest) + '\n').encode('utf-8'))
    outf.comment = ('xd puzzles published before %d, from %s' % (args.before, source)).encode('utf-8')

    utils.info('wrote %d puzzles to %s (left out: %d from %d or later, %d with no year, %d redacted)'
               % (len(puzzles), outf.filename, nlater, args.before, nnoyear, nredacted))


if __name__ == '__main__':
    main()
