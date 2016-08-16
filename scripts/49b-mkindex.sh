#!/bin/bash
#
#

LOGS_INDEX='index.html'

HTML_HEAD="<!DOCTYPE html><html><head><meta http-equiv='content-type' content='text/html; charset=UTF-8'></head><body>"
HTML_END="</body></html>"

echo $HTML_HEAD > ${LOGS_INDEX}

for l in $(aws s3 ls --region ${REGION} s3://${BUCKET}/logs/ | egrep '\.log$' | sort -r | awk '{print $4}'); do
    echo "<div><a href='http://${BUCKET}/logs/${l}' type='text/html'>$l</a></div>" >> ${LOGS_INDEX}
done

echo $HTML_END >> ${LOGS_INDEX}

aws s3 cp --region ${REGION} ${LOGS_INDEX} s3://${BUCKET}/logs/ --acl public-read
