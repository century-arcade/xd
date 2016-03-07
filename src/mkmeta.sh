#!/bin/sh

pubid=$1
pubdir=crosswords/${pubid}
WWWOUT=www/xdiffs/${pubid}/
SRCDIR=`pwd`/src

mkdir -p ${WWWOUT}
ln -sf ${SRCDIR}/style.css ${WWWOUT}/

echo "num_xd: `find crosswords/${pubid} -name '*.xd' | wc -l`\nyears: `cd ${pubdir} ; echo [1-2]*`\n"> ${pubdir}/meta.txt
