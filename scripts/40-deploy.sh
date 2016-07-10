#!/bin/bash
# source scripts/config-vars.sh

mkdir -p $WWW/tech

markdown www/index.md > $WWW/index.html
markdown www/tech.md > $WWW/tech/index.html

# aws s3 rm -recursive ${S3WWW}/pub

cp scripts/html/style.css $WWW/pub/
cp scripts/html/*.html $WWW/

aws s3 sync --region $REGION $WWW ${S3WWW}/ --acl public-read

# concatenate all logfiles from working dirs and copy to cloud
ALLLOGS=$WWW/log/$TODAY-logs.txt
scripts/49-cat-logs.py -o $ALLLOGS $PUB $TMP
aws s3 cp --region $REGION $ALLLOGS ${S3WWW}/log/ --acl public-read

