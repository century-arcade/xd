#!/bin/bash
# source scripts/config-vars.sh

# aws s3 rm -recursive ${S3WWW}/pub

cp scripts/html/style.css $WWW/pub/
cp scripts/html/*.html $WWW/

aws s3 sync --region $REGION $WWW ${S3WWW}/ --acl public-read

# PLEASE CHECK HOW TO RUN
# scripts/49-cat-logs.py
