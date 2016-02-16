#!/bin/bash -x

# .xd scraping tool

# requires REGION, BRANCH, and BUCKET

S3CP="aws s3 cp --region ${REGION}"
YEAR=`date +"%Y"`

CROSSWORDS="nytimes latimes chronicle theglobeandmail_canadian theglobeandmail_universal wapost wsj newsday"

### download/unzip xd sources

wget https://github.com/century-arcade/xd/archive/${BRANCH}.zip

unzip ${BRANCH}.zip
XD=xd-${BRANCH}

### s3get previous archive, download new dates, convert everything, s3put both raw archive and cooked archive

for cw in ${CROSSWORDS} ; do
    SRCZIP=${cw}-${YEAR}-raw.zip
    XDZIP=${cw}-${YEAR}.zip
    ${S3CP} s3://${BUCKET}/src/${SRCZIP} . && \
        ${XD}/scrape-xd.py ${cw} && \
        ${S3CP} ${SRCZIP} s3://${BUCKET}/src/ && \
        ${S3CP} --acl public-read ${XDZIP} s3://${BUCKET}/
done

exit 0

