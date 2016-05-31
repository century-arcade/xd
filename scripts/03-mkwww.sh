#!/bin/sh

# Run without parameters, from the xd directory.
#
#   produces a similarity check for a bunch of raw crosswords, creating several artifacts along the way

#source scripts/config-vars.sh

CORPUS="-c $GXD"

mkdir -p wwwroot/pub/gxd

## produce an analysis for each puzzle in odd.tsv
#scripts/60-mkwww-odd.py ${CORPUS} -o wwwroot/ $GXD/odd.tsv

# 
cp $GXD/*.tsv wwwroot/pub/gxd/

#scripts/60-mkwww-pub-index.py ${CORPUS} -o wwwroot/pub/

# 6x: mkwww

#scripts/60-mkwww-diffs.py -o www/${BASE} pub/similar.tsv

#scripts/65-mkwww-publishers -o www/
#scripts/65-mkwww-index.py -o www/${BASE} ${BASE}-similar.tsv
#scripts/67-mkwww-clues.py -o wwwroot/
#scripts/68-mkwww-words.py -o wwwroot/

scripts/71-mkwww-redirects.py -o wwwroot/ $GXD/redirects.tsv

