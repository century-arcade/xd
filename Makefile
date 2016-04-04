
CORPUS=gxd

S3CFG= -c src/aws/s3cfg.century-arcade 
BUCKET= xd.saul.pw
WWWDIR= www/xdiffs

SCRIPTDIR=$(shell pwd)/scripts

sync-corpus: $(CORPUS).tar.xz $(CORPUS).zip
	s3cmd ${S3CFG} put -P $^ s3://${BUCKET}/

$(CORPUS).tar.xz:
	find crosswords -name '*.xd' -print | sort | tar Jcf $@ --owner 0 --group 0 --no-recursion -T -

$(CORPUS).zip:
	find crosswords -name '*.xd' -print | sort | zip $@ -@

puzzles.tsv: $(SCRIPTDIR)/enumpuzzles.py
	PYTHONPATH=. $(SCRIPTDIR)/enumpuzzles.py > $@

publishers.tsv: $(SCRIPTDIR)/enumpublishers.py
	PYTHONPATH=. $(SCRIPTDIR)/enumpublishers.py > $@

findgrids: src/findgrids.c
	gcc -std=c99 -ggdb -O3 -o $@ $<

transpose-diffs.txt:
	PYTHONPATH=. ${SCRIPTDIR}/transpose_corpus > transpose-diffs.txt

.PHONY: always

