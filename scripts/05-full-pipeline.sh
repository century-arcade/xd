#!/bin/sh
#
#

source scripts/helpers.sh

echo '10-import'
scripts/10-import.sh

# Define QUICKRUN to skip time consuming actions
if [ ! -n "$QUICKRUN" ]; then
    echo '20-analyze'
    scripts/20-analyze.sh
    echo '30-mkwww'
    scripts/30-mkwww.sh
fi

# commit new puzzles and saved analysis results
scripts/41-git-commit.sh

echo '40-deploy'
scripts/40-deploy.sh
