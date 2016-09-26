#!/bin/bash
#
#

source scripts/helpers.sh

$aws s3 rm --recursive ${S3WWW}/

# Define QUICKRUN to skip time consuming actions
if [ ! -n "$QUICKRUN" ]; then
    echo '20-analyze beta'
    scripts/20-analyze.sh
    echo '30-mkwww beta'
    scripts/30-mkwww.sh
fi

echo '40-deploy'
scripts/40-deploy.sh
