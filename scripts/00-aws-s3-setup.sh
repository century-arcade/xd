#!/bin/sh

source scripts/helpers.sh

$aws s3api create-bucket --bucket $DOMAIN
$aws s3api create-bucket --bucket $XDPRIV

# enable static website hosting
$aws s3 website $S3WWW --index-document index.html --error-document error.html

# clean old bucket
$aws s3 rm --recursive $S3WWW

# also done every update
WWWFILES=scripts/html/error.html scripts/html/style.css
$aws s3 cp $WWWFILES $S3WWW/

# external: set $DOMAIN DNS to S3 endpoint


