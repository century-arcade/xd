#!/bin/bash
#
#   Usage: $0 <table to export> <.tsv file as output>
#

DBFN='meta.db'
TABLE=$1
OUT=$2

sqlite3 -header -separator $'\t' ${DBFN} "select * from ${TABLE}" > ${OUT}
