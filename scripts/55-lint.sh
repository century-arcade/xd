#!/bin/sh
#
#   Checks .xd files for errors
#   Usage: $0 <DIR>
#

DIR=$1

echo "Check for xml entities in puzzles"
grep -ri '&[a-z]\+;' --exclude-dir .git $DIR

