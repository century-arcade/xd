#!/bin/bash
#
#

LOGS_INDEX='index.html'

HTML_HEAD="<!DOCTYPE html><html><body>"
HTML_END="</body></html>"

echo $HTML_HEAD > ${LOGS_INDEX}

for l in $(aws s3 ls --region ${REGION} s3://${BUCKET}/logs/ | grep '.log' | sort -r | awk '{print $4}'); do
    echo "<div><a href='http://${BUCKET}/logs/${l}'>$l</a></div>" >> ${LOGS_INDEX}
done

echo $HTML_END >> ${LOGS_INDEX}

aws s3 cp --region ${REGION} ${LOGS_INDEX} s3://${BUCKET}/logs/ --acl public-read
