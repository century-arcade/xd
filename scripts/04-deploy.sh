#!/bin/bash

# source scripts/config-vars.sh

scripts/95-mkwww-logs.py -o ${OUTWWWDIR}/${NOW}/log.html ${OUTBASEDIR}

aws s3 sync ${OUTWWWDIR} ${S3WWW}/ --acl public-read

