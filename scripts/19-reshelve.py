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

    receipts = metadb.xd_receipts_rows()
    rids = set()  # set of ReceiptId

    for r in receipts:
        oldpubid = ""
        oldpubid = utils.parse_pubid(r.xdid or '')

        newpubid = catalog.find_pubid("|".join((str(x) for x in r)))

        d = r._asdict()

        if int(r.ReceiptId) in rids:
            d["ReceiptId"] = max(rids) + 1

        try:
            rids.add(int(d["ReceiptId"]))
        except:
            # omit any lines without receiptId
            continue

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
