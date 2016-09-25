#!/usr/bin/env python3

# Usage: $0 -o xd-clues.zip gxd/

# outputs clues.tsv with all clues/answers by pubyear

from xdfile import metadatabase as metadb
from xdfile import utils
import xdfile


def main():
    args = utils.get_args('make clues.tsv files')
    outf = utils.open_output()  # should be .zip

    outf.log = False
    outf.toplevel = 'xd'
    outf.write_file('README', open('doc/zip-README').read())

    all_clues = [(ca.pubid, str(xdfile.year_from_date(ca.date)), ca.answer, ca.clue) for ca in xdfile.clues()]

    clues_tsv = ''

    clues_tsv += '\t'.join("pubid year answer clue".split()) + '\n'
    clues_tsv += '\n'.join('\t'.join(cluerow) for cluerow in sorted(all_clues))
    outf.write_file('clues.tsv', clues_tsv)

if __name__ == "__main__":
    main()
