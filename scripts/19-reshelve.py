#!/usr/bin/env python3
# Usage: $0 [-c <corpus>] <regex> <pubid>
#
#   rewrites receipts.jsonl and receipts.tsv (whichever exist) and fills in any blanks based on regex
#
#   git mv all .xd with pubid of <src> to have a pubid of <dest> (simple file rename)
#
#
import os

from xdfile import utils, metadatabase as metadb, catalog


def main():
    utils.get_args()

    all_receipts = metadb.xd_receipts_header
    all_jsonl = ""

    receipts = metadb.xd_receipts_rows()

    for r in receipts:
        oldpubid = ""
        oldpubid = utils.parse_pubid(r.xdid or '')

        d = dict(r)
        core = [d.get(k) or "" for k in metadb.RECEIPT_COLUMNS]

        newpubid = catalog.find_pubid("|".join(core))

        if newpubid and newpubid != oldpubid:
            seqnum = utils.parse_seqnum(r.xdid or r.SourceFilename)
            if seqnum:
                newxdid = newpubid + seqnum
                utils.info("changing xdid from '%s' to '%s'" % (r.xdid, newxdid))
                core[-1] = newxdid
            else:
                utils.info("no date or number in xdid, not reshelving")

        all_receipts += metadb.xd_receipts_row(*core)
        all_jsonl += metadb.receipt_jsonl_line(core, **d)

    if os.path.exists(metadb.RECEIPTS_TSV) or not os.path.exists(metadb.RECEIPTS_JSONL):
        open(metadb.RECEIPTS_TSV, 'w', encoding='utf-8', newline='').write(all_receipts)
    if os.path.exists(metadb.RECEIPTS_JSONL):
        open(metadb.RECEIPTS_JSONL, 'w', encoding='utf-8', newline='').write(all_jsonl)


main()
