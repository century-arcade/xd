#!/bin/bash
# Run without parameters, from the xd directory.
#
#   Creates .html for the public website in $WWW (usually wwwroot)
#source scripts/config-vars.sh

source scripts/colorsh.sh

CORPUS="-c $GXD"
mkdir -p $WWW/pub/gxd
# 
cp $GXD/*.tsv $WWW/pub/gxd/
cp $PUB/*.tsv $WWW/pub/

echo -en "${GREEN}Generate /pub/[<pub>][<year>]${NORMAL}\n"
scripts/31-mkwww-publishers.py $CORPUS -o $WWW

echo -en "${GREEN}Generate /pub/word/<ANSWER>${NORMAL}\n"
scripts/33-mkwww-words.py $CORPUS -o $WWW

echo -en "${GREEN}Generate /pub/clue/<boiledclue>${NORMAL}\n"
scripts/34-mkwww-clues.py $CORPUS -o $WWW

echo -en "${GREEN}Generate /pub/<xdid>${NORMAL}\n"
scripts/35-mkwww-diffs.py $CORPUS -o $WWW

echo -en "${GREEN}Generate /pub/clue/<xdid>${NORMAL}\n"
scripts/36-mkwww-deepclues.py $CORPUS -o $WWW

echo -en "${GREEN}From gxd/redirects.tsv${NORMAL}\n"
scripts/38-mkwww-redirects.py -o $WWW $GXD/redirects.tsv

# Reset color
tput sgr0
