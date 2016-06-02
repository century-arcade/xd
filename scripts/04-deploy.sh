#!/bin/bash

# source scripts/config-vars.sh

scripts/95-mkwww-logs.py -o $WWW/$NOW/log.html $TMP

#aws s3 rm -recursive ${S3WWW}/pub

aws s3 sync $WWW ${S3WWW}/ --acl public-read

