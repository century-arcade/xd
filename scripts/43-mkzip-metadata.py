#!/usr/bin/python3

# Usage: $0 -o xd-metadata.zip

# makes .zip of all metadata .tsv

from xdfile import metadatabase as metadb
from xdfile import utils


def main():
    args = utils.get_args()

    outf = utils.open_output()  # should be .zip

    outf.log = False
    outf.toplevel = 'xd'
    outf.write_file('README', open('doc/zip-README').read())
    outf.write_file('puzzles.tsv', open('pub/puzzles.tsv').read())
    outf.write_file('stats.tsv', open('pub/stats.tsv').read())
    outf.write_file('similar.tsv', open('gxd/similar.tsv').read())


if __name__ == "__main__":
    main()
