#!/usr/bin/env python3

# Usage: $0 -c gxd -o xd-sample.zip --seed S [options]
#        $0 --dry-run --puzzles-tsv pub/puzzles.tsv --similar-tsv gxd/similar.tsv [options]
#
# Draws a reproducible stratified sample of full puzzles (see xdfile/sample.py
# for the selection rule) and writes a .zip of the original .xd files plus
# MANIFEST.tsv and README. Same seed + same gxd commit + same options => same
# sample. --dry-run prints the per-publication/decade allocation without
# writing anything, and can run from the public xd-metadata.zip tables
# (puzzles.tsv, similar.tsv) without a gxd checkout; it does not know which
# puzzles are redacted, so exact picks can differ slightly from a real run.

import os
import subprocess
import sys

from xdfile import utils, sample
import xdfile


def gxd_commit(corpusdir):
    try:
        return subprocess.check_output(['git', '-C', corpusdir, 'rev-parse', 'HEAD'],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return 'unknown'


def load_similar(path, max_similar):
    if not path or not os.path.exists(path):
        utils.warn('no similarity table at %s; near-duplicate grids will not be filtered' % path)
        return {}
    rows = []
    with open(path, encoding='utf-8') as fp:
        header = fp.readline().rstrip('\n').split('\t')
        cols = [header.index(c) for c in ('xdid1', 'xdid2', 'matchpct')] if 'xdid1' in header else [0, 1, 2]
        for line in fp:
            f = line.rstrip('\n').split('\t')
            if len(f) > max(cols):
                rows.append(tuple(f[i] for i in cols))
    return sample.similarity_graph(rows, max_similar)


def load_excludes(paths):
    ret = set()
    for p in paths or []:
        with open(p, encoding='utf-8') as fp:
            for line in fp:
                x = line.split('\t', 1)[0].strip()
                if x and x != 'xdid' and not x.startswith('#'):
                    ret.add(x)
    return ret


def candidates_from_corpus(args):
    corpus = {}
    nredacted = nwindow = 0
    for xd in xdfile.corpus():
        if xd.is_redacted():
            nredacted += 1
            continue
        if not sample.in_window(xd.date(), args.since, args.before):
            nwindow += 1
            continue
        corpus[xd.xdid()] = xd
    utils.info('excluded %d redacted, %d outside date window' % (nredacted, nwindow))
    cands = [sample.Candidate(x, xd.publication_id(), xd.date()) for x, xd in corpus.items()]
    return cands, corpus


def candidates_from_tsv(args):
    cands = []
    for r in utils.parse_tsv_rows(args.puzzles_tsv, 'Puzzle'):
        parts = utils.split_xdid(r.xdid)
        if not parts:
            continue  # undated/numbered xdids have no date to window on
        date = str(r.Date or '-'.join(parts[1:]))
        if sample.in_window(date, args.since, args.before):
            cands.append(sample.Candidate(r.xdid, parts[0], date))
    return cands


def main():
    p = utils.args_parser('draw a reproducible stratified sample of full puzzles')
    p.add_argument('--seed', required=True, help='RNG seed; record it, it defines the sample')
    p.add_argument('--rate', type=float, default=1000, help='one puzzle per RATE puzzles per publication (default 1000)')
    p.add_argument('--min-per-pub', type=int, default=1, help='floor per publication (default 1)')
    p.add_argument('--since', default='1965-01-01', help='earliest date, inclusive (default 1965-01-01)')
    p.add_argument('--before', default='2020-01-01', help='latest date, exclusive (default 2020-01-01)')
    p.add_argument('--max-similar', type=int, default=50, help='block grids >= this %% similar to a chosen one (default 50)')
    p.add_argument('--similar-tsv', default='gxd/similar.tsv')
    p.add_argument('--exclude', action='append', help='file of xdids (first column) to exclude, e.g. an earlier MANIFEST.tsv; repeatable')
    p.add_argument('--puzzles-tsv', help='with --dry-run: plan from this puzzles.tsv instead of the corpus')
    p.add_argument('--dry-run', action='store_true', help='print allocation only')
    args = utils.get_args(parser=p)

    if args.puzzles_tsv:
        if not args.dry_run:
            sys.exit('--puzzles-tsv is for planning only; use with --dry-run')
        cands, corpus = candidates_from_tsv(args), {}
    else:
        cands, corpus = candidates_from_corpus(args)

    similar = load_similar(args.similar_tsv, args.max_similar)
    excluded = load_excludes(args.exclude)
    selected, report = sample.draw(cands, args.seed, args.rate, args.min_per_pub, similar, excluded)

    lines = ['pubid\tdecade\tavailable\twanted\tchosen']
    lines += ['%s\t%s\t%d\t%d\t%d' % r for r in report]
    short = [r for r in report if r[4] < r[3]]
    table = '\n'.join(lines)
    print(table)
    print('# %d puzzles from %d publications (%d candidates)' %
          (len(selected), len({r[0] for r in report}), len(cands)))
    if short:
        print('# %d strata came up short after near-duplicate filtering' % len(short))

    if args.dry_run:
        return

    outf = utils.open_output()
    assert isinstance(outf, utils.OutputZipFile), '-o must name a .zip'
    outf.log = False
    outf.toplevel = 'xd-sample'

    manifest = ['xdid\tpubid\tdate\tsize\trebus']
    for xdid in selected:
        xd = corpus[xdid]
        try:
            contents = open(xd.filename, 'rb').read()
        except OSError:
            contents = xd.to_unicode().encode('utf-8')
        pubid = xd.publication_id()
        outf.write_file('%s/%s.xd' % (pubid, xdid), contents)
        manifest.append('%s\t%s\t%s\t%s\t%s' % (xdid, pubid, xd.date(), xd.sizestr(), 'R' if xd.rebus() else ''))

    readme = '\n'.join([
        'xd sample: %d puzzles' % len(selected),
        '',
        'NOT FOR REDISTRIBUTION. These puzzles are copyrighted by their constructors',
        'and publishers and are provided only under the terms you agreed to.',
        '',
        'Reproduce with:',
        '  gxd commit:  %s' % gxd_commit(args.corpusdir),
        '  command:     %s' % ' '.join(sys.argv),
        '',
        'Allocation:',
        table,
        '',
    ])
    outf.write_file('MANIFEST.tsv', ('\n'.join(manifest) + '\n').encode('utf-8'))
    outf.write_file('README', readme.encode('utf-8'))
    utils.info('wrote %d puzzles to %s' % (len(selected), outf.filename))


if __name__ == '__main__':
    main()
