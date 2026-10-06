#!/usr/bin/env python3

# Usage: $0 -o xd-clues.zip gxd/

# outputs clues.tsv with all clues/answers by pubyear

from xdfile import utils
import xdfile


HEADER = '\t'.join("pubid year answer clue".split())


def main():
    utils.get_args('make clues.tsv files')
    outf = utils.open_output()
    assert isinstance(outf, utils.OutputZipFile), '-o must name a .zip'

    outf.log = False
    outf.toplevel = 'xd'
    outf.write_file('README', open('doc/zip-README').read())

    # skip clues from redacted contest puzzles (whole puzzle is all X's)
    puzzles = {}
    for xd in xdfile.corpus():
        if xd.is_redacted():
            continue
        pubid = xd.publication_id()
        pubyear = (pubid, str(xdfile.year_from_date(xd.date() or "")))
        puzzles.setdefault(pubyear, []).append(xd)

    # one pubyear at a time: all 8.9M clue rows at once costs several GB, which
    # overruns a hosted build container. (pubid, year) leads the sort key, so
    # emitting sorted pubyears of sorted rows is the same order as sorting all.
    utils.info("writing clues.tsv for %d pubyears..." % len(puzzles))
    nclues = 0
    with outf.open_file('clues.tsv') as fp:
        fp.write(HEADER.encode('utf-8'))
        for pubyear in sorted(puzzles):
            pubid, year = pubyear
            rows = sorted((pubid, year, answer, clue)
                          for xd in puzzles[pubyear]
                          for pos, clue, answer in xd.iterclues())
            fp.write(''.join('\n' + '\t'.join(row) for row in rows).encode('utf-8'))
            nclues += len(rows)
            utils.progress('%s%s' % pubyear, every=50)
    utils.progress()
    utils.info("wrote %d clues to %s, done" % (nclues, outf.filename))


if __name__ == "__main__":
    main()
