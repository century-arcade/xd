export PYTHONPATH=.

GXD_GIT=https://gitlab.com/rabidrat/gxd.git
GXD_DIR=gxd
SRC_GIT=git@github.com:saulpw/gxd-sources
SRC_DIR=gxd-sources
WWW_DIR=wwwroot
PUB_DIR=pub
NOW=$(shell date +"%Y%m%d-%H%M%S")
YEAR=$(shell date +"%Y")
WWWZIP=/tmp/${NOW}-www.zip
RECENT_XDS=$(shell git -C ${GXD_DIR} log --pretty="format:" --since="30 days ago" --name-only | sort | uniq)
TODAY_XDS=$(shell git -C ${GXD_DIR} log --pretty="format:" --since="1 days ago" --name-only | sort | uniq)

S3_REGION=us-west-2
S3_WWW=s3://xd.saul.pw

.PHONY: gxd.sqlite

all: analyze gridmatches website

pipeline: setup import analyze gridmatches commit

netlify: setup-gxd analyze website

setup: setup-gxd setup-src

setup-gxd:
	[ ! -d ${GXD_DIR} ] && git clone ${GXD_GIT} ${GXD_DIR} || (cd ${GXD_DIR} && git pull)

setup-src:
	[ ! -d ${SRC_DIR} ] && git clone ${SRC_GIT} ${SRC_DIR} || (cd ${SRC_DIR} && git pull)

import:
	scripts/11-download-puzzles.py -o ${WWWZIP}
	scripts/18-convert2xd.py -o ${GXD_DIR}/ ${WWWZIP}
	mkdir -p ${SRC_DIR}/${YEAR}/
	cp ${WWWZIP} ${SRC_DIR}/${YEAR}/

checkdups:
	scripts/25-analyze-puzzle.py -o ${WWW_DIR}/ -c ${GXD_DIR} ${GXD_DIR}

analyze:
	mkdir -p ${WWW_DIR}
	mkdir -p ${PUB_DIR}
	scripts/21-clean-metadata.py ${GXD_DIR}
	scripts/27-pubyear-stats.py -c ${GXD_DIR}
	scripts/26-mkzip-clues.py -c ${GXD_DIR} -o ${WWW_DIR}/xd-clues.zip
	scripts/29-mkzip-metadata.py -c ${GXD_DIR} -o ${WWW_DIR}/xd-metadata.zip

website: website-static
	mkdir -p ${WWW_DIR}/pub/gxd
	zip -q -r ${WWW_DIR}/xd-puzzles.zip `cat ${GXD_DIR}/pubs.txt`
	scripts/37-pubyear-svg.py -o ${WWW_DIR}/ # /pub/ index
	scripts/33-mkwww-words.py -c ${GXD_DIR} -o ${WWW_DIR}/ # /pub/word/<ANSWER>
	scripts/34-mkwww-clues.py -c ${GXD_DIR} -o ${WWW_DIR}/ ${RECENT_XDS} # /pub/clue/<boiledclue>
	scripts/35-mkwww-diffs.py -c ${GXD_DIR} -o ${WWW_DIR}/ # /pub/<xdid>
	scripts/36-mkwww-deepclues.py -c ${GXD_DIR} -o ${WWW_DIR}/ ${RECENT_XDS} # /pub/clue/<xdid>

website-static:
	mkdir -p ${WWW_DIR}
	cp scripts/html/* ${WWW_DIR}
	pandoc www/about.md | scripts/wwwify.py 'About' > ${WWW_DIR}/about.html
	pandoc www/data.md | scripts/wwwify.py 'Data' > ${WWW_DIR}/data.html

commit:
	(cd ${GXD_DIR} && \
	git add . && \
	git commit -m "incoming for ${TODAY}" && \
	ssh-agent bash -c "ssh-add ${HOME}/.ssh/gxd_rsa; git push")
	(cd ${SRC_DIR} && \
	git add . && \
	git commit -m "incoming for ${TODAY}" && \
	git push)

gridmatches: gxd.sqlite src/gridcmp.so
	time python3 src/findmatches.py -N 100
	sqlite3 -header -separator '	' gxd.sqlite "select * from gridmatches;" > ${GXD_DIR}/similar.tsv

gxd.sqlite: ${GXD_DIR}
	time ./scripts/26-mkdb-sqlite.py $@ ${GXD_DIR}
	cat src/inputgridmatches.sql | sqlite3 $@

gxd.zip:
	find ${GXD_DIR} -name '*.xd' -print | sort | zip $@ -@

src/gridcmp.so: src/sqlite_gridcmp.c
	gcc -g -fPIC -shared $< -o $@
