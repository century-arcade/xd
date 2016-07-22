## How to process big puzzle archive (like bwh.zip)

rm -rf bwh-zips/ && mkdir bwh-zips
./scripts/90-split-archive.py -o bwh-zips/ --source bwh-2015.tgz bwh/
./scripts/18-convert2xd.py -o gxd/ bwh-zips/up.zip
