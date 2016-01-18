#!/bin/bash

#exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

BUCKET=$1

REGION=us-west-2
S3CP="aws s3 cp --region $REGION"

### setup

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update && \
    sudo apt-get install --yes zip awscli python-lxml python-pip && \
    sudo pip install cssselect

wget https://github.com/century-arcade/xd/archive/master.zip

unzip master.zip
XD=xd-master

$S3CP s3://$BUCKET/src/LAST_FETCH LAST_FETCH
LAST_FETCH=`cat LAST_FETCH`
TODAY=`date +"%Y-%m-%d"`

### nyt

NYTRAW=nyt$TODAY-raw.zip
$XD/scrapers/dl-xwordinfo.com.py $LAST_FETCH $TODAY

zip $NYTRAW *.html && \
    $S3CP $NYTRAW s3://$BUCKET/src/xwordinfo.com-$TODAY.zip && \
    rm $NYTRAW

for i in *.html ; do
    NYTXD=${i%.html}.xd
    $XD/scrapers/xwi2xd.py $i $NYTXD && \
        $S3CP --acl public-read $NYTXD s3://$BUCKET/crosswords/nytimes/ && \
        rm $i $NYTXD
done

### lat

LATRAW=lat$TODAY-raw.zip

python $XD/main.py --download-raw --scraper latimes --outfile $LATRAW --from-date $LAST_FETCH --to-date $TODAY

python $XD/main.py --raw-to-xd --scraper latimes -i $LATRAW -o lat$TODAY.zip && \
    $S3CP $LATRAW s3://$BUCKET/crosswords/latimes/xdlat$TODAY.zip && \
    rm $LATRAW

### finish

echo $TODAY > LAST_FETCH
$S3CP LAST_FETCH s3://$BUCKET/src/LAST_FETCH

# sudo in production
poweroff

exit 0

