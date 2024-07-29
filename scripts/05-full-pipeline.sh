#!/bin/bash
#
#

source scripts/helpers.sh

echo '10-import'
scripts/10-import.sh

# commit new puzzles and saved analysis results
scripts/41-git-commit.sh

echo '40-deploy'
scripts/40-deploy.sh

# concatenate all logfiles from working dirs and copy to cloud
ALLLOGS=$WWW/log/$TODAY-logs.txt
$python scripts/49-cat-logs.py -o $ALLLOGS $PUB $TMP
$aws s3 cp --region $REGION $ALLLOGS ${S3WWW}/logs/ --acl public-read
