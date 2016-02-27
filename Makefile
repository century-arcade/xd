S3CFG=src/aws/s3cfg.century-arcade 
BUCKET=xd.saul.pw
WWWDIR=www/

diffs:
	src/mkindex.py `find crosswords -name meta.txt` > $(WWWDIR)/xdiffs/index.html

sync-diffs:
	s3cmd -c $(S3CFG) sync -P www/diffs s3://$(BUCKET)/

deploy:
	s3cmd -c $(S3CFG) put -P www/index.html s3://$(BUCKET)/
	s3cmd -c $(S3CFG) put -P www/style.css s3://$(BUCKET)/
