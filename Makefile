
CORPUS=gxd

S3CFG= -c src/aws/s3cfg.century-arcade 
BUCKET= xd.saul.pw
WWWDIR= www/xdiffs

SRCDIR=$(shell pwd)/src

sync-corpus: $(CORPUS).tar.xz $(CORPUS).zip
	s3cmd ${S3CFG} put -P $^ s3://${BUCKET}/

$(CORPUS).tar.xz:
	find crosswords -name '*.xd' -print | sort | tar Jcf $@ --owner 0 --group 0 --no-recursion -T -

$(CORPUS).zip:
	find crosswords -name '*.xd' -print | sort | zip $@ -@

puzzles.tsv: $(SRCDIR)/enumpuzzles.py
	$(SRCDIR)/enumpuzzles.py > $@

publishers.tsv: $(SRCDIR)/enumpublishers.py
	$(SRCDIR)/enumpublishers.py > $@

findgrids: src/findgrids.c
	gcc -std=c99 -ggdb -O3 -o $@ $<

.PHONY: always

