#!/bin/bash

source scripts/helpers.sh

cp scripts/html/style.css $WWW/
cp scripts/html/*.html $WWW/

for page in about data ; do
    pagedir=$WWW/${page}
    markdown www/${page}.md > $pagedir.html
    scripts/44-mkwww-pages.py -o $WWW/ $pagedir.html
done

$aws s3 sync --region $REGION $WWW ${S3WWW}/ --acl public-read
