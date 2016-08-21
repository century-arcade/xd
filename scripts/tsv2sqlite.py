#!/usr/bin/env python3

# Usage: $0 [-o <sqlitedb>] <input>
#
#   Converts file in <input.tsv> to sqlite database
#

import sqlite3
import xdfile.utils
from xdfile.utils import args_parser, get_args, info
from xdfile import metadatabase as metadb


# Map tsvtype and sql table
sqlmap = {
    'Receipt' : 'receipts',
    'Publication' : 'publications',
}


def main():
    p = args_parser('convert .tsv to sqlite')
    p.add_argument('--tsvtype', default=None, help='Tsv file type to import')
    args = get_args(parser=p)

    if args.tsvtype is not None:
    # Process only if tsvtype supplied
        sqlconn = sqlite3.connect(args.output)
        cur = sqlconn.cursor()
        rows = [list(r) for r in xdfile.utils.parse_tsv_rows(args.inputs[0], args.tsvtype)]

        if args.tsvtype == 'Similar':
            # Fill up similar clues first
            sclues = [[x[0], x[2], x[3], x[4]] for x in rows]
            INS_TMPL = ",".join('?' * len(sclues[0]))
            cur.executemany('INSERT INTO %s VALUES (%s)' % ('similar_clues', INS_TMPL), sclues)
            # Fill up similar grids
            sgrids = []
            for r in rows:
                if '=' in r[5]:
                    for pos in r[5].split(' '):
                        (xdidm, pctm) = pos.split('=')
                        sgrids.append([r[0], xdidm, int(pctm)])

            INS_TMPL = ",".join('?' * len(sgrids[0]))
            cur.executemany('INSERT INTO %s VALUES (%s)' % ('similar_grids', INS_TMPL), sgrids)
        else:
            rows = [list(r) for r in xdfile.utils.parse_tsv_rows(args.inputs[0], args.tsvtype)]

            info("Rows to be inserted to sql table [ %s ]: %s" % (sqlmap[args.tsvtype], len(rows)))
            INS_TMPL = ",".join('?' * len(rows[0]))
            cur.executemany('INSERT OR IGNORE INTO %s VALUES (%s)' % (sqlmap[args.tsvtype], INS_TMPL), rows)
        sqlconn.commit()

if __name__ == "__main__":
    main()
