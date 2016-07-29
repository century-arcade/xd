#!/bin/sh

SRC=$1
DST=$2

shift
shift

mv="mv"

echo "Rename to 'b' those which grids are different"
# Get those which have grid diff
for f in $(git diff -U0 -G# \
   --ignore-blank-lines  \
   --ignore-space-at-eol  \
   --ignore-space-change  \
   --ignore-all-space  \
   --diff-filter=M \
   --src-prefix=$SRC:  \
   --dst-prefix=$DST:  \
   $* | grep '^+++' | cut -d: -f2); do
    bn=$(basename $f .xd)
    dn=$(dirname $f)
    $mv $f ${dn}/${bn}b.xd
done

git diff -U0 -G~ \
   --ignore-blank-lines  \
   --ignore-space-at-eol  \
   --ignore-space-change  \
   --ignore-all-space  \
   --diff-filter=M \
   --src-prefix=$SRC:  \
   --dst-prefix=$DST:  \
   $* | grep '^[+\-]' > ${SRC}-${DST}.diff
