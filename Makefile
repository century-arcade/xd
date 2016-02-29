
S3CFG= -c src/aws/s3cfg.century-arcade 
SRCDIR=$(shell pwd)/src

BUCKET= xd.saul.pw
WWWDIR= www/xdiffs

SIMILAR_TXT=$(wildcard crosswords/*/similar.txt)
META_TXT=$(wildcard crosswords/*/meta.txt)

PUBLISHERS=chicago chronicle universal latimes wapost usatoday nysun crossroads nytimes wsj onion newsday

diffs: top-index
	for pubid in `cat publishers.txt` ; do \
		rm -rf ${WWWDIR}/$$pubid ; \
		${SRCDIR}/mkwww.py ${WWWDIR}/$$pubid ${SIMILAR_TXT} ; \
		cp ${SRCDIR}/style.css ${WWWDIR}/$$pubid ; \
	done

top-index:
	$(SRCDIR)/mkindex.py ${META_TXT} > ${WWWDIR}/index.html
	cp ${SRCDIR}/style.css ${WWWDIR}/


sync-diffs:
	s3cmd $(S3CFG) sync -P www/xdiffs s3://$(BUCKET)/

sync-corpus: xd-corpus.tar.xz xd-corpus.zip
	s3cmd ${S3CFG} put -P $^ s3://${BUCKET}/


deploy: xd-xdiffs.zip
	s3cmd $(S3CFG) put -P www/index.html s3://$(BUCKET)/
	s3cmd $(S3CFG) put -P www/style.css s3://$(BUCKET)/

xd-corpus.tar.xz:
	find crosswords -name '*.xd' -print | sort | tar Jcf $@ --owner 0 --group 0 --no-recursion -T -

xd-corpus.zip:
	find crosswords -name '*.xd' -print | sort | zip xd-corpus.zip -@

xd-xdiffs.zip:
	zip $@ $(SIMILAR_TXT) `./src/zipsimilar.py $(SIMILAR_TXT)`
	cp $@ 

.PHONY: always

