#!/bin/bash
#
# Run without parameters, from the xd directory.
#
#   Creates .html for the public website in $WWW (usually wwwroot)

source scripts/helpers.sh
source scripts/colorsh.sh

CORPUS="-c $GXD"
mkdir -p $WWW/pub/gxd

#cp $GXD/*.tsv $WWW/pub/gxd/
#cp $PUB/*.tsv $WWW/pub/

echo -en "${GREEN}Generate /pub/ index${NORMAL}\n"
$python scripts/37-pubyear-svg.py -o $WWW/
$aws s3 mv --recursive --region $REGION $WWW ${S3WWW}/ --acl public-read

echo -en "${GREEN}Generate /pub/word/<ANSWER>${NORMAL}\n"
$python scripts/33-mkwww-words.py $CORPUS -o $WWW/
$aws s3 mv --recursive --region $REGION $WWW ${S3WWW}/ --acl public-read

echo -en "${GREEN}Generate /pub/clue/<boiledclue>${NORMAL}\n"
$python scripts/34-mkwww-clues.py $CORPUS -o $WWW/
$aws s3 mv --recursive --region $REGION $WWW ${S3WWW}/ --acl public-read

echo -en "${GREEN}Generate /pub/<xdid>${NORMAL}\n"
$python scripts/35-mkwww-diffs.py $CORPUS -o $WWW/
$aws s3 mv --recursive --region $REGION $WWW ${S3WWW}/ --acl public-read

echo -en "${GREEN}Generate /pub/clue/<xdid>${NORMAL}\n"
$python scripts/36-mkwww-deepclues.py $CORPUS -o $WWW/
$aws s3 mv --recursive --region $REGION $WWW ${S3WWW}/ --acl public-read

echo -en "${GREEN}From gxd/redirects.tsv${NORMAL}\n"
$python scripts/38-mkwww-redirects.py -o $WWW/ $GXD/redirects.tsv
$aws s3 mv --recursive --region $REGION $WWW ${S3WWW}/ --acl public-read

# Reset color
tput sgr0

