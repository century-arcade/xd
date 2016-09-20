#!/bin/bash

# Run without parameters from the xd directory.
# 

source scripts/helpers.sh

export TMP=`mktemp -d`

RECENTS=$GXD/recent-downloads.tsv
EMAILZIP=$TMP/$NOW-email.zip
WWWZIP=$TMP/$NOW-www.zip

set -e

# 1x: download more recent puzzles

# check for email and parse out attachments
mkdir -p $TMP/incoming
$aws s3 sync --region $REGION ${S3PRIV}/incoming $TMP/incoming/
if find $TMP/incoming -mindepth 1 -print -quit | grep -q .; then
    $python scripts/12-parse-email.py -o $EMAILZIP $TMP/incoming
    $aws s3 cp $EMAILZIP ${S3PRIV}/sources/
    $aws s3 rm --recursive ${S3PRIV}/incoming
fi

# download from www
$python scripts/11-download-puzzles.py -o $WWWZIP --recents $RECENTS
$aws s3 cp --region $REGION $WWWZIP ${S3PRIV}/sources/

# convert everything to .xd, shelve in the proper location, and commit
$python scripts/18-convert2xd.py -o $GXD/ $EMAILZIP $WWWZIP

# updates receipts.tsv with xdid according to current rules
# $python scripts/19-reshelve.py

