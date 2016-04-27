
CORPUS=gxd

S3CFG= -c src/aws/s3cfg.century-arcade 
BUCKET= xd.saul.pw
WWWDIR= www/xdiffs

SCRIPTDIR=$(shell pwd)/scripts
QUERYDIR=$(shell pwd)/queries

COLLECTION=bwh-2015

all:

extract:
	mkdir -p bwh
	tar -C bwh/ -zxf ${COLLECTION}.tgz

catalog: ${COLLECTION}-source.zip

convert: ${COLLECTION}-converted.zip

headers-clean: ${COLLECTION}-cleaned.zip

shelve: ${COLLECTION}-shelved.zip

collection-clean:
	rm -f ${COLLECTION}-shelved.zip
	rm -f ${COLLECTION}-cleaned.zip
	rm -f ${COLLECTION}-source.zip
	rm -f ${COLLECTION}-converted.zip

${COLLECTION}-source.zip: bwh/
	PYTHONPATH=. ${SCRIPTDIR}/10-catalog-source.py -o $@ -s ${COLLECTION}.tgz $<

${COLLECTION}-converted.zip: ${COLLECTION}-source.zip
	PYTHONPATH=. ${SCRIPTDIR}/20-convert2xd.py -o $@ $<

#${COLLECTION}-cleaned.zip: ${COLLECTION}-converted.zip
#	PYTHONPATH=. ${SCRIPTDIR}/25-clean-headers.py -o $@ $<

${COLLECTION}-shelved.zip: ${COLLECTION}-cleaned.zip
	PYTHONPATH=. ${SCRIPTDIR}/30-shelve.py -o $@ $<

${COLLECTION}-puzzles.tsv: ${COLLECTION}-shelved.zip
	PYTHONPATH=. $(SCRIPTDIR)/40-catalog-puzzles.py -c $< -o $@

sync-corpus: $(CORPUS).tar.xz $(CORPUS).zip
	s3cmd ${S3CFG} put -P $^ s3://${BUCKET}/

$(CORPUS).tar.xz:
	find crosswords -name '*.xd' -print | sort | tar Jcf $@ --owner 0 --group 0 --no-recursion -T -

$(CORPUS).zip:
	find crosswords -name '*.xd' -print | sort | zip $@ -@

publishers.tsv: $(QUERYDIR)/enumpublishers.py
	PYTHONPATH=. $(QUERYDIR)/enumpublishers.py > $@

findgrids: src/findgrids.c
	gcc -std=c99 -ggdb -O3 -o $@ $<

transpose-diffs.txt:
	PYTHONPATH=. ${SCRIPTDIR}/transpose_corpus > transpose-diffs.txt

.PHONY: always

