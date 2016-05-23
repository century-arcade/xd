#!/bin/bash

aws="echo aws"

XDWWW=xd.saul.pw
XDPRIV=xd-private

$aws s3api create-bucket --bucket $XDWWW
$aws s3api create-bucket --bucket $XDPRIV

# enable static website hosting
# set xd.workmuch.com DNS to S3 endpoint
# upload /error.html (public-read)
# upload /index.html (public-read)
# set mime-type for .xd
