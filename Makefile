PYTHONPATH=.

GXD_GIT=git@gitlab.com:rabidrat/xd.git
GXD_DIR=gxd
WWW_DIR=wwwroot
PUB_DIR=pub
NOW=$(shell date +"%Y%m%d-%H%M%S")
WWWZIP=/tmp/${NOW}-www.zip
RECENT_XDS=$(shell git -C ${GXD_DIR} log --pretty="format:" --since="30 days ago" --name-only | sort | uniq)
TODAY_XDS=$(shell git -C ${GXD_DIR} log --pretty="format:" --since="1 days ago" --name-only | sort | uniq)

S3_REGION=us-west-2
S3_WWW=s3://xd.saul.pw

all: analyze website

pipeline: setup import analyze website commit deploy

setup:
	git clone ${GXD_GIT} ${GXD_DIR}

import:
	scripts/11-download-puzzles.py -o ${WWWZIP}
	scripts/18-convert2xd.py -o ${GXD_DIR}/ ${WWWZIP}
#	${AWS} s3 cp --region ${S3_REGION} ${WWWZIP} ${S3_PRIV}/sources/

analyze:
	mkdir -p ${WWW_DIR}
	mkdir -p ${PUB_DIR}
	scripts/21-clean-metadata.py ${GXD_DIR}
	scripts/25-analyze-puzzle.py -o ${WWW_DIR}/ -c ${GXD_DIR} ${GXD_DIR}
	scripts/27-pubyear-stats.py -c ${GXD_DIR}
	scripts/26-mkzip-clues.py -c ${GXD_DIR} -o ${WWW_DIR}/xd-clues.zip
	scripts/28-mkzip-public.py -o ${WWW_DIR}/xd-public.zip ${GXD_DIR}/
	scripts/29-mkzip-metadata.py -c ${GXD_DIR} -o ${WWW_DIR}/xd-metadata.zip

website: website-static
	mkdir -p ${WWW_DIR}/pub/gxd
	scripts/37-pubyear-svg.py -o ${WWW_DIR}/ # /pub/ index
	scripts/33-mkwww-words.py -c ${GXD_DIR} -o ${WWW_DIR}/ # /pub/word/<ANSWER>
	scripts/34-mkwww-clues.py -c ${GXD_DIR} -o ${WWW_DIR}/ ${RECENT_XDS} # /pub/clue/<boiledclue>
	scripts/35-mkwww-diffs.py -c ${GXD_DIR} -o ${WWW_DIR}/ # /pub/<xdid>
	scripts/36-mkwww-deepclues.py -c ${GXD_DIR} -o ${WWW_DIR}/ ${RECENT_XDS} # /pub/clue/<xdid>
	scripts/38-mkwww-redirects.py -o ${WWW_DIR}/ ${GXD_DIR}/redirects.tsv

website-static:
	mkdir -p ${WWW_DIR}
	cp scripts/html/* ${WWW_DIR}
	markdown www/about.md | scripts/wwwify.py 'About' > ${WWW_DIR}/about.html
	markdown www/data.md | scripts/wwwify.py 'Data' > ${WWW_DIR}/data.html

deploy:
	aws s3 mv --recursive --region ${S3_REGION} ${WWW_DIR} ${S3_WWW}/ --acl public-read

commit:
	cd ${GXD_DIR}
	git add .
	git commit -m "incoming for ${TODAY}"
	ssh-agent bash -c "ssh-add ${HOME}/.ssh/gxd_rsa; git push"

gridmatches: gxd.sqlite gridcmp.so
	cat src/findmatches.sql | time sqlite3 gxd.sqlite

gxd.sqlite: ${GXD_DIR}
	time ./scripts/26-mkdb-sqlite.py $@ ${GXD_DIR}

gxd.zip:
	find ${GXD_DIR} -name '*.xd' -print | sort | zip $@ -@

gridcmp.so: src/sqlite_gridcmp.c
	gcc -g -fPIC -shared $< -o $@
