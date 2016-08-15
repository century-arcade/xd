#!/usr/bin/env python3

# Usage:
#   $0 -o log.txt products/
#
#  concatenates .log files (even those in subdirs or .zip) and combines into a single combined.log

from xdfile.utils import find_files_with_time, open_output, get_args
from boto.s3.connection import S3Connection
import os


def main():
    args = get_args('aggregates all .log files')
    outf = open_output()

    print(os.environ['AWS_ACCESS_KEY'],os.environ['AWS_SECRET_KEY'])
    conn = S3Connection(aws_access_key_id=os.environ['AWS_ACCESS_KEY'], aws_secret_access_key=os.environ['AWS_SECRET_KEY'])
    print(conn)
    s3path = "s3://" + os.environ['BUCKET'] + "/logs/"
    bucket = conn.get_bucket(s3path)
    print(bucket, s3path)
    for key in sorted(bucket.list(), key=lambda x: x.last_modified):
        # last_modified
        print("Name: %s LastModified:%s" % (key.name.encode('utf-8'), key.last_modified))

    for fn, contents, dt in sorted(find_files_with_time(*args.inputs, ext=".log"), key=lambda x: x[2]):  # earliest first
        outf.write_file(fn, contents.decode("utf-8"))

main()
