#!/bin/sh

# unshelve into corpus directly

set -e
set -x

git checkout crosswords
git checkout -b incoming_$TODAY
git commit -a -m "incoming for $TODAY"
git push

# submit pull request to gitlab (which is setup to add some people automatically on each PR)


