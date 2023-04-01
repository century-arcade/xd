#!/usr/bin/env python3

'''
Usage: $0 <gxd.sqlite> <input_dir>

Create and populate <gxd.sqlite> database with metadata, grid, and clues.
'''

import os
import sys

import xdfile

def find_files(path, ext=''):
    for root, directories, files in os.walk(path):
        for fn in files:
            if fn.endswith(ext):
                yield os.path.join(root, fn)


def main(outdb, inputdir):
    import sqlite3
    con = sqlite3.connect(outdb)
    cur = con.cursor()

    # puzzle metadata
    cur.execute('DROP TABLE IF EXISTS puzzles')
    cur.execute('''CREATE TABLE puzzles (
        xdfn TEXT PRIMARY KEY,
        xdid TEXT,
        date TEXT,
        size TEXT,
        title TEXT,
        author TEXT,
        editor TEXT,
        copyright TEXT,
        grid TEXT)
    ''')

    cur.execute('DROP TABLE IF EXISTS clues')
    cur.execute('''CREATE TABLE IF NOT EXISTS clues (
        xdid TEXT,
        position TEXT,
        answer TEXT,
        clue TEXT)
    ''')

    for xdfn in find_files(inputdir, ext='.xd'):
        xd = xdfile.parse(xdfn)

        w = xd.width()
        h = xd.height()
        rebus = xd.get_header("Rebus") and "R" or ""
        special = xd.get_header("Special") and "S" or ""
        size = f'{w}x{h}{rebus}{special}'

        cur.execute('INSERT INTO puzzles VALUES (?,?,?,?,?,?,?,?,?)', (
            xdfn,
            xd.xdid(),
            xd.get_header("Date"),
            size,
            xd.get_header("Title"),
            xd.get_header("Author") or xd.get_header("Creator"),
            xd.get_header("Editor"),
            xd.get_header("Copyright"),
            '|'.join(xd.grid),
        ))

        for pos, clue, answer in xd.iterclues():
            if pos:
                cur.execute('INSERT INTO clues VALUES (?, ?, ?, ?)', (xd.xdid(), pos, answer, clue))

    con.commit()


if __name__ == "__main__":
    main(*sys.argv[1:])
