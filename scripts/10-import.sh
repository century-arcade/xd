#!/bin/bash

# Run without parameters from the xd directory.
# 

source scripts/helpers.sh

export TMP=`mktemp -d`

RECENTS=$GXD/recent-downloads.tsv
WWWZIP=$TMP/$NOW-www.zip

set -e

# 1x: download more recent puzzles

# download from www
$python scripts/11-download-puzzles.py -o $WWWZIP
$aws s3 cp --region $REGION $WWWZIP ${S3PRIV}/sources/

# record the zip in gxd's source-archives.tsv (committed with the receipts by
# 41-git-commit.sh); skipped for gxd checkouts that predate the register
if [ -f $GXD/scripts/source_archives.py ]; then
    $python $GXD/scripts/make-source-archive.py $WWWZIP --register --producer "xd nightly downloader"
fi

# convert everything to .xd, shelve in the proper location, and commit
$python scripts/18-convert2xd.py -o $GXD/ $WWWZIP

# updates receipts.tsv with xdid according to current rules
# $python scripts/19-reshelve.py

