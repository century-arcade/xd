#!/bin/bash

# .xd scraping tool
# run this script 
# requires REGION, BRANCH, and BUCKET

S3CP="aws s3 cp --region ${REGION}"

#### download/unzip xd sources

wget https://github.com/century-arcade/xd/archive/${BRANCH}.zip

unzip ${BRANCH}.zip
XD=xd-${BRANCH}

#### get LAST_FETCH date (or use TODAY)

${S3CP} s3://${BUCKET}/src/LAST_FETCH LAST_FETCH
LAST_FETCH=`cat LAST_FETCH`
TODAY=`date +"%Y-%m-%d"`

if [ -z "${LAST_FETCH}" ]; then
    LAST_FETCH=${TODAY}
fi

### download/parse/upload nyt

NYTRAW=nyt${TODAY}-raw.zip
${XD}/scrapers/dl-xwordinfo.com.py ${LAST_FETCH} ${TODAY}

zip ${NYTRAW} *.html && \
    ${S3CP} ${NYTRAW} s3://${BUCKET}/src/xwordinfo.com-${TODAY}.zip && \
    rm ${NYTRAW}

for i in *.html ; do
    NYTXD=${i%.html}.xd
    ${XD}/utils/xwi2xd.py $i ${NYTXD} && \
        ${S3CP} --acl public-read ${NYTXD} s3://${BUCKET}/crosswords/nytimes/ && \
        rm $i ${NYTXD}
done

### download/parse/upload lat

LATRAW=lat${TODAY}-raw.zip
LATXD=lat${TODAY}.zip

python ${XD}/main.py --download-raw --scraper latimes --outfile ${LATRAW} --from-date ${LAST_FETCH} --to-date ${TODAY} && \
    ${S3CP} ${LATRAW} s3://${BUCKET}/src/

python ${XD}/main.py --raw-to-xd --scraper latimes -i ${LATRAW} -o lat${TODAY}.zip && \
    ${S3CP} ${LATXD} s3://${BUCKET}/crosswords/latimes/xdlat${TODAY}.zip && \
    rm ${LATRAW}

### update LAST_FETCH date

echo ${TODAY} > LAST_FETCH
${S3CP} LAST_FETCH s3://${BUCKET}/src/LAST_FETCH

### send email

#aws ses send-email --destination ${EMAIL} --message "Your logs are attached." --subject "${TODAY} logs" --to ${EMAIL}

### and done

exit 0

