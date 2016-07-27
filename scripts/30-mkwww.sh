#!/bin/sh
# Run without parameters, from the xd directory.
#
#   Creates .html for the public website in $WWW (usually wwwroot)
#source scripts/config-vars.sh

CORPUS="-c $GXD"
mkdir -p $WWW/pub/gxd
#
cp $GXD/*.tsv $WWW/pub/gxd/
cp $PUB/*.tsv $WWW/pub/

# generate /pub/[<pub>][<year>]
scripts/31-mkwww-publishers.py $CORPUS -o $WWW/

# generate /pub/word/<ANSWER>
scripts/33-mkwww-words.py $CORPUS -o $WWW/

# generate /pub/clue/<boiledclue>
scripts/34-mkwww-clues.py $CORPUS -o $WWW/

# generate /pub/<xdid>
scripts/35-mkwww-diffs.py $CORPUS -o $WWW/

# generate /pub/clue/<xdid>
scripts/36-mkwww-deepclues.py $CORPUS -o $WWW/

# from gxd/redirects.tsv
scripts/38-mkwww-redirects.py -o $WWW/ $GXD/redirects.tsv
