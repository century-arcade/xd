#!/bin/bash

# source scripts/config-vars.sh

# aws s3 rm -recursive ${S3WWW}/pub

cp scripts/style.css $WWW/pub/
cp scripts/*.html $WWW/

aws s3 sync --region $REGION $WWW ${S3WWW}/ --acl public-read

