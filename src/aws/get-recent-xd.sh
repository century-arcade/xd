#!/bin/bash -x

# .xd scraping tool

# requires REGION, BRANCH, and BUCKET to be set

S3CP="aws s3 cp --region ${REGION:-us-west-2}"
YEAR=`date +"%Y"`

### download/unzip xd sources

wget https://github.com/century-arcade/xd/archive/${BRANCH}.zip
unzip ${BRANCH}.zip
XD=xd-${BRANCH}

### s3get previous archive, download new dates, convert everything, s3put both raw archive and cooked archive

aws s3 sync --region ${REGION:-us-west-2} --exclude '*' --include "*-${YEAR}-raw.zip" s3://${BUCKET}/src/ .

for SRCZIP in *-raw.zip ; do
    XDZIP=${SRCZIP%-raw.zip}.zip
    ${XD}/src/downloadraw ${SRCZIP} && \
        ${S3CP} ${SRCZIP} s3://${BUCKET}/src/ && \
        ${XD}/src/convert2xd ${SRCZIP} ${XDZIP} && \
        ${S3CP} --acl public-read ${XDZIP} s3://${BUCKET}/
done

exit 0

