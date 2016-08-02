#!/bin/bash

METADB='meta.db'

cd gxd/ && git checkout . && git clean -fd && cd ..
rm ${METADB} && ./scripts/05-sql-import-receipts.sh ${METADB}
