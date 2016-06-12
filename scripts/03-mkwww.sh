#!/bin/sh

# Run without parameters, from the xd directory.
#
#   Creates .html for the public website in $WWW (usually wwwroot)

#source scripts/config-vars.sh

CORPUS="-c $GXD"

mkdir -p $WWW/pub/gxd

# 
cp $GXD/*.tsv $WWW/pub/gxd/

# 6x: mkwww

scripts/60-mkwww-diffs.py $CORPUS -o $WWW

# prerequisite: 41-pubyears (in 02-analyze)

scripts/65-mkwww-publishers.py $CORPUS -o $WWW

scripts/67-mkwww-clues.py $CORPUS -o $WWW
scripts/68-mkwww-words.py $CORPUS -o $WWW

scripts/71-mkwww-redirects.py -o $WWW $GXD/redirects.tsv

