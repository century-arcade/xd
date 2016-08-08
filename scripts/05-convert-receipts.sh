#!/bin/bash
#
# Usage: $0 <receipts.tsv>
# Remove Receipts ID from file

FILE=$1

if [[ -n $(cat $FILE | head | grep ReceiptId) ]]; then
    cp $FILE ${FILE}.orig
    cat ${FILE}.orig | cut -f 2- > $FILE
fi

