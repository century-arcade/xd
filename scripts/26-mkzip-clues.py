#!/usr/bin/env python3

# Usage: $0 -o xd-clues.zip gxd/

# outputs clues.tsv with all clues/answers by pubyear

from xdfile import utils
import xdfile


def main():
    utils.get_args('make clues.tsv files')
    outf = utils.open_output()  # should be .zip

    outf.log = False
    outf.toplevel = 'xd'
    outf.write_file('README', open('doc/zip-README').read())

    # skip clues from redacted contest puzzles (whole puzzle is all X's)
    redacted = {xd.xdid() for xd in xdfile.corpus() if xd.is_redacted()}
    all_clues = [(ca.pubid, str(xdfile.year_from_date(ca.date)), ca.answer, ca.clue)
                 for ca in xdfile.clues()
                 if ca.xdid() not in redacted]

    utils.info("sorting and formatting %d clues..." % len(all_clues))
    clues_tsv = ''
    clues_tsv += '\t'.join("pubid year answer clue".split()) + '\n'
    clues_tsv += '\n'.join('\t'.join(cluerow) for cluerow in sorted(all_clues))
    utils.info("sorting and formatting clues, done")

    utils.info("writing clues.tsv to %s..." % outf.filename)
    outf.write_file('clues.tsv', clues_tsv)
    utils.info("writing clues.tsv, done")

if __name__ == "__main__":
    main()
