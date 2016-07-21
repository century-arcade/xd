#!/bin/sh

echo "rm -rf bwh_zips/ && mkdir bwh_zips"
echo ./scripts/90-split-archive.py -o bwh_zips/ --source bwh-2015.tgz bwh/
echo ./scripts/18-convert2xd.py -o gxd/ bwh_zips/up.zip 
