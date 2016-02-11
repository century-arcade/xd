#!/bin/bash

# .xd scraping tool
# run this script 
# requires REGION, BRANCH, and BUCKET

S3CP="aws s3 cp --region ${REGION}"

#### download/unzip xd sources

wget https://github.com/century-arcade/xd/archive/${BRANCH}.zip

unzip ${BRANCH}.zip
XD=xd-${BRANCH}

TODAY=`date +"%Y-%m-%d"`
YEAR=`date +"%Y"`

for cw in nytimes latimes ; do
    SRCZIP=${cw}-${YEAR}-raw.zip
    XDZIP=${cw}-${YEAR}.zip
    ${S3CP} s3://${BUCKET}/src/${SRCZIP} .
    ${XD}/scrape-xd.py ${cw}
    ${S3CP} ${SRCZIP} s3://${BUCKET}/src/
    ${S3CP} --acl public-read ${XDZIP} s3://${BUCKET}/
done

### send email

#aws ses send-email --destination ${EMAIL} --message "Your logs are attached." --subject "${TODAY} logs" --to ${EMAIL}

### and done

exit 0

