#!/usr/bin/env python3

# Usage: $0 -o gxd.sqlite gxd/

# outputs clues.tsv with all clues/answers by pubyear

from xdfile import utils
import xdfile


def main():
    args = utils.get_args('make gxd.sqlite')

    import sqlite3
    con = sqlite3.connect(args.output)
    cur = con.cursor()

    # puzzle metadata
    cur.execute('''CREATE TABLE puzzles (xdid TEXT, date TEXT, size TEXT, title TEXT, author TEXT, editor TEXT, copyright TEXT, grid TEXT)''')

    for xd in xdfile.corpus():
        cur.execute('INSERT INTO puzzles VALUES (?,?,?,?,?,?,?,?)',
                (
        xd.xdid(),
        xd.get_header("Date"),
        "%dx%d%s%s" % (xd.width(), xd.height(), xd.get_header("Rebus") and "R" or "", xd.get_header("Special") and "S" or ""),

        xd.get_header("Title"),
        xd.get_header("Author") or xd.get_header("Creator"),
        xd.get_header("Editor"),
        xd.get_header("Copyright"),
        '|'.join(xd.grid),
        ))

    con.commit()

    # clues
    cur.execute('''CREATE TABLE clues (xdid TEXT, position TEXT, answer TEXT, clue TEXT)''')

    for xd in xdfile.corpus():
        xdid = xd.xdid()
        for pos, clue, answer in xd.iterclues():
            if not pos: continue
            cur.execute('INSERT INTO clues VALUES (?, ?, ?, ?)', (xdid, pos, answer, clue))

    con.commit()

if __name__ == "__main__":
    main()
