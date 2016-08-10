#!/bin/bash
#
#   Usage: $0 <table to export> <.tsv file as output>
#

DBFN='meta.db'
TABLE=$1
OUT=$2

ORDER=''
if [[ 'receipts' -eq "${TABLE}" ]]; then
    ORDER='ORDER BY ReceivedTime, xdid, CaptureTime'
fi
sqlite3 -header -separator $'\t' ${DBFN} "select * from ${TABLE} ${ORDER}" > ${OUT}
