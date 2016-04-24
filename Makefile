
CORPUS=gxd

S3CFG= -c src/aws/s3cfg.century-arcade 
BUCKET= xd.saul.pw
WWWDIR= www/xdiffs

SCRIPTDIR=$(shell pwd)/scripts
QUERYDIR=$(shell pwd)/queries

bwh-all:

bwh-extract:
	mkdir -p bwh
	tar -C bwh/ -zxf bwh-2015.tgz

bwh-catalog: bwh-2015-source.zip

bwh-convert: bwh-2015-xd.zip

bwh-shelve: bwh-2015-shelved.zip

bwh-clean:
	rm -f bwh-2015-shelved.zip
	rm -f bwh-2015-source.zip
	rm -f bwh-2015-xd.zip

bwh-2015-source.zip: bwh/
	PYTHONPATH=. ${SCRIPTDIR}/10-catalog-source.py -o $@ -s bwh-2015.tgz $<

bwh-2015-xd.zip: bwh-2015-source.zip
	PYTHONPATH=. ${SCRIPTDIR}/20-convert2xd.py -o $@ $<

bwh-2015-shelved.zip: always #bwh-2015-xd.zip
	PYTHONPATH=. ${SCRIPTDIR}/30-shelve.py -o $@ bwh/ #$<

sync-corpus: $(CORPUS).tar.xz $(CORPUS).zip
	s3cmd ${S3CFG} put -P $^ s3://${BUCKET}/

$(CORPUS).tar.xz:
	find crosswords -name '*.xd' -print | sort | tar Jcf $@ --owner 0 --group 0 --no-recursion -T -

$(CORPUS).zip:
	find crosswords -name '*.xd' -print | sort | zip $@ -@

puzzles.tsv: $(QUERYDIR)/enumpuzzles.py
	PYTHONPATH=. $(QUERYDIR)/enumpuzzles.py > $@

publishers.tsv: $(QUERYDIR)/enumpublishers.py
	PYTHONPATH=. $(QUERYDIR)/enumpublishers.py > $@

findgrids: src/findgrids.c
	gcc -std=c99 -ggdb -O3 -o $@ $<

transpose-diffs.txt:
	PYTHONPATH=. ${SCRIPTDIR}/transpose_corpus > transpose-diffs.txt

.PHONY: always

