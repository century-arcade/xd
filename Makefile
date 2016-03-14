
S3CFG= -c src/aws/s3cfg.century-arcade 
S3CMD= s3cmd ${S3CFG}

SRCDIR=$(shell pwd)/src

BUCKET= xd.saul.pw
WWWDIR= www/xdiffs

SIMILAR_TXT=$(wildcard crosswords/*/similar.txt)
META_TXT=$(wildcard crosswords/*/meta.txt)

YEAR :=  $(shell date +"%Y")
TODAY := $(shell date +"%Y-%m-%d")

WWW_YEAR=${WWWDIR}/${YEAR}
SIMILAR_YEAR= crosswords/similar-${YEAR}.txt


GIT_CORPUS= git@gitlab.com:rabidrat/xd.git
RAWZIPFN= xd-${TODAY}-raw.zip

help:
	echo "Incorrect usage"

daily: branch-corpus scrape-raw upload-raw convert-recent commit-recent compare-ytd www upload-www

branch-corpus: always
#	git clone ${GIT_CORPUS}
	git checkout crosswords
	git checkout -b auto_${TODAY}

# download all puzzles since last date in corpus for each publisher in puzzles-source.txt
scrape-raw: always
	${SRCDIR}/scrape-raw.py -o ${RAWZIPFN} -s puzzle-sources.txt

upload-raw: always
	${S3CMD} put ${RAWZIPFN} s3://${BUCKET}/src/${YEAR}/

convert-recent: always
	${SRCDIR}/convert-recent.py ${RAWZIPFN}

commit-recent: always
	git add crosswords/
	git commit -m "automated commit"

compare-ytd: always
	${SRCDIR}/findsimilar.py crosswords/ crosswords/*/${YEAR}/*.xd > ${SIMILAR_YEAR}

www-diff-ytd: always
	mkdir -p ${WWW_YEAR}
	cp ${SRCDIR}/style.css ${WWW_YEAR}
	${SRCDIR}/mkwww.py -o ${WWW_YEAR} ${SIMILAR_YEAR}

www: www-diff-ytd www-index

upload-www: always
	${S3CMD} put -P ${WWWDIR} s3://${BUCKET}/

config-cloud: always
	${SRCDIR}/aws/configure-ec2.sh

deconfig-cloud: always
	${SRCDIR}/aws/deconfigure-autorun.sh


# need special one to do (YEAR-1) in new year
consolidate-ytd-raw: always
	mkdir raw/
	-${S3CMD} sync s3://${BUCKET}/src/${YEAR} raw/
	-${S3CMD} get s3://${BUCKET}/src/xd-${YEAR}-raw.zip raw/
	zipmerge xd-${YEAR}-raw.zip raw/*.zip
	${S3CMD} put xd-${YEAR}-raw.zip s3://${BUCKET}/src/
#	rm -rf raw/

# should be done manually at end-of-year, once consolidation is confirmed
remove-daily-raw: always
	${S3CMD} del s3://${BUCKET}/src/${YEAR}/


### ---

diffs: www-index
	for pubid in `cat publishers.txt` ; do \
		rm -rf ${WWWDIR}/$$pubid ; \
		${SRCDIR}/mkwww.py ${WWWDIR}/$$pubid ${SIMILAR_TXT} ; \
		cp ${SRCDIR}/style.css ${WWWDIR}/$$pubid ; \
	done

www-index:
	$(SRCDIR)/mkindex.py ${META_TXT} > ${WWWDIR}/index.html
	cp ${SRCDIR}/style.css ${WWWDIR}/


sync-diffs:
	${S3CMD} sync -P www/xdiffs s3://$(BUCKET)/

sync-corpus: xd-corpus.tar.xz xd-corpus.zip
	${S3CMD} put -P $^ s3://${BUCKET}/


deploy: xd-xdiffs.zip
	${S3CMD} put -P www/index.html s3://$(BUCKET)/
	${S3CMD} put -P www/style.css s3://$(BUCKET)/

xd-corpus.tar.xz:
	find crosswords -name '*.xd' -print | sort | tar Jcf $@ --owner 0 --group 0 --no-recursion -T -

xd-corpus.zip:
	find crosswords -name '*.xd' -print | sort | zip xd-corpus.zip -@

xd-xdiffs.zip:
	zip $@ $(SIMILAR_TXT) `./src/zipsimilar.py $(SIMILAR_TXT)`

.PHONY: always

