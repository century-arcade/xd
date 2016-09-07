#!/bin/sh
#
# Usage: $0 <source> <destination> <dir> 

SRC=$1
DST=$2
DIR=$3

shift
shift

## dryrun="true"
mv="mv"

echo "Rename to '${DST}' those which grids are different"

if [ -z "${dryrun}" ]; then
# Get those which have grid diff
for f in $(git diff -U0 -G# \
   --ignore-blank-lines  \
   --ignore-space-at-eol  \
   --ignore-space-change  \
   --ignore-all-space  \
   --diff-filter=M \
   --src-prefix=$SRC:  \
   --dst-prefix=$DST:  \
   $DIR | grep '^+++' | cut -d: -f2); do
    bn=$(basename $f .xd)
    dn=$(dirname $f)
    fnew=${dn}/${bn}${DST}.xd
    $mv $f $fnew
    git checkout $f
    git add $fnew
done

# Write diff file
fndiff=${DIR}/${SRC}-${DST}.diff
git diff -U0 -G~ \
   --ignore-blank-lines  \
   --ignore-space-at-eol  \
   --ignore-space-change  \
   --ignore-all-space  \
   --diff-filter=M \
   --src-prefix=$SRC:  \
   --dst-prefix=$DST:  \
   $DIR | grep '^[+\-]' > $fndiff

git add $fndiff
else
# Just print out git-diff for files except headers
git diff -U0 -G# \
   --ignore-blank-lines  \
   --ignore-space-at-eol  \
   --ignore-space-change  \
   --ignore-all-space  \
   --diff-filter=M \
   --src-prefix=$SRC:  \
   --dst-prefix=$DST:  \
   $DIR

fi
