#!/bin/sh

source scripts/helpers.sh

# $aws s3 rm -recursive ${S3WWW}/pub

cp scripts/html/style.css $WWW/
cp scripts/html/*.html $WWW/

for page in about data ; do 
    pagedir=$WWW/${page}
    markdown www/${page}.md > $pagedir.html
    scripts/44-mkwww-pages.py -o $WWW/ $pagedir.html
done


$aws s3 sync --region $REGION $WWW ${S3WWW}/ --acl public-read

# concatenate all logfiles from working dirs and copy to cloud
ALLLOGS=$WWW/log/$TODAY-logs.txt
$python scripts/49-cat-logs.py -o $ALLLOGS $PUB $TMP
$aws s3 cp --region $REGION $ALLLOGS ${S3WWW}/logs/ --acl public-read
