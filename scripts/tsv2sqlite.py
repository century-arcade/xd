#!/usr/bin/env python3

# Usage: $0 [-o <sqlitedb>] <input>
#
#   Converts file in <input.tsv> to sqlite database
#

import sqlite3

import xdfile.utils
from xdfile.utils import args_parser, get_args
from xdfile import metadatabase as metadb


def main():
    p = args_parser('convert .tsv to sqlite')
    args = get_args(parser=p)

    sqlconn = sqlite3.connect(args.output)
    cur = sqlconn.cursor()

    rows = [list(r) for r in xdfile.utils.parse_tsv(args.inputs[0], "Receipt").values()]
    cur.executemany('INSERT INTO receipts VALUES (?,?,?,?,?,?)', rows)
    sqlconn.commit()

if __name__ == "__main__":
    main()
