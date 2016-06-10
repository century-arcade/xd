#!/usr/bin/env python3
#
# Usage: $0 [-c <corpus>]
#
#   reports receipts.xdid that are not in the corpus

import os.path

from xdfile import metadatabase as metadb, catalog, utils
import xdfile

def main():
    all_xd = set(xd.xdid() for xd in xdfile.corpus())
    receipt_xd = set(r.xdid for r in metadb.xd_receipts().values())

    unr = sorted(all_xd - receipt_xd)
    uns = sorted(receipt_xd - all_xd)
    utils.log('unreceived (%s): %s' % (len(unr), ' '.join(unr)))
    utils.log('unshelved (%s): %s' % (len(uns), ' '.join(uns)))


main()
