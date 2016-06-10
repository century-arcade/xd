#!/usr/bin/env python3

# Usage: $0 [-c <corpus>] <regex> <pubid>
#
#   rewrites receipts.tsv and fills in any blanks based on regex
#
#   git mv all .xd with pubid of <src> to have a pubid of <dest> (simple file rename)
# 
#

import re

from xdfile import utils, metadatabase as metadb, catalog


def main():
    args = utils.get_args()

    all_receipts = metadb.xd_receipts_header

    for r in sorted(metadb.xd_receipts().values(), key=lambda x: int(x.ReceiptId)):
        oldpubid = ""
        if r.xdid:
            oldpubid = utils.parse_pubid(r.xdid)

        newpubid = catalog.find_pubid("|".join(r))

        d = r._asdict()

        if newpubid and newpubid != oldpubid:
            seqnum = utils.parse_seqnum(r.xdid or r.SourceFilename)
            if seqnum:
                newxdid = newpubid + seqnum
                utils.log("changing xdid from '%s' to '%s'" % (r.xdid, newxdid))
                d["xdid"] = newxdid
            else:
                utils.log("no date or number in xdid, not reshelving")

        all_receipts += metadb.xd_receipts_row(**d)

    open(metadb.RECEIPTS_TSV, 'w').write(all_receipts)


main()
