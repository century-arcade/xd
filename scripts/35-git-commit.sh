#!/bin/sh

# unshelve into corpus directly

set -e
set -x

TODAY=`date +"%Y%m%d"`

git checkout crosswords
git checkout -b incoming_$TODAY
git add crosswords
git commit -m "incoming xd for $TODAY"
git push --set-upstream origin incoming_$TODAY


# submit pull request to gitlab (which is setup to add some people automatically on each PR)


