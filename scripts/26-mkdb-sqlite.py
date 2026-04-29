#!/usr/bin/env python3

'''
Usage: $0 -o <gxd.sqlite> -c <corpus>

Create and populate <gxd.sqlite> database with metadata, grid, and clues.
'''

import sqlite3
import sys

from xdfile import iter_corpus
from xdfile.utils import get_args, info


def main():
    args = get_args(desc='create sqlite db with metadata, grid, and clues')
    if not args.output:
        sys.exit("usage: %s -o <gxd.sqlite> -c <corpus>" % sys.argv[0])

    # Incremental: previously-imported puzzles are skipped. To force a full
    # rebuild (e.g. after a parser change), delete the sqlite file first.
    con = sqlite3.connect(args.output)
    cur = con.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS puzzles (
        xdfn TEXT PRIMARY KEY,
        xdid TEXT,
        date TEXT,
        size TEXT,
        title TEXT,
        author TEXT,
        editor TEXT,
        copyright TEXT,
        A1_D1 TEXT,
        grid TEXT)
    ''')

    cur.execute('''CREATE TABLE IF NOT EXISTS clues (
        xdid TEXT,
        position TEXT,
        answer TEXT,
        clue TEXT)
    ''')

    existing = set(row[0] for row in cur.execute('SELECT xdfn FROM puzzles'))

    for xd in iter_corpus():
        if xd.filename in existing:
            continue

        w = xd.width()
        h = xd.height()
        rebus = xd.get_header("Rebus") and "R" or ""
        special = xd.get_header("Special") and "S" or ""
        size = f'{w}x{h}{rebus}{special}'

        cur.execute('INSERT INTO puzzles VALUES (?,?,?,?,?,?,?,?,?,?)', (
            xd.filename,
            xd.xdid(),
            xd.get_header("Date"),
            size,
            xd.get_header("Title"),
            xd.get_header("Author") or xd.get_header("Creator"),
            xd.get_header("Editor"),
            xd.get_header("Copyright"),
            "%s_%s" % (xd.get_answer("A1"), xd.get_answer("D1")),
            '|'.join(xd.grid),
        ))

        for pos, clue, answer in xd.iterclues():
            if pos:
                cur.execute('INSERT INTO clues VALUES (?, ?, ?, ?)', (xd.xdid(), pos, answer, clue))

    info("creating index...")
    cur.execute('CREATE INDEX IF NOT EXISTS puzzles_size_date ON puzzles(size, date)')

    info("committing...")
    con.commit()


if __name__ == "__main__":
    main()
