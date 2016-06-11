#!/bin/bash

aws="echo aws"

$aws s3api create-bucket --bucket $DOMAIN
$aws s3api create-bucket --bucket $XDPRIV

# enable static website hosting
$aws s3 website $S3WWW --index-document index.html --error-document error.html

WWWFILES=www/error.html www/style.css
$aws s3 cp $WWWFILES $S3WWW/

# set $DOMAIN DNS to S3 endpoint

