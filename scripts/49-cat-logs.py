#!/usr/bin/env python3

# Usage:
#   $0 -o log.txt products/
#
#  concatenates .log files (even those in subdirs or .zip) and combines into a single combined.log

from xdfile.utils import find_files_with_time, open_output, get_args
import boto3
# from boto.s3.connection import S3Connection
import os


def main():
    args = get_args('aggregates all .log files')
    outf = open_output()

    s3 = boto3.resource('s3')
    s3path = "logs/"
    # bucket = conn.get_bucket(s3path)
    bucket = s3.Bucket(os.environ['DOMAIN'])

    for obj in sorted(bucket.objects.all(), key=lambda x: x.last_modified):
        # last_modified
        if s3path in obj.key:
            print("Name: %s LastModified:%s" % (obj.key.encode('utf-8'), obj.last_modified))

    for fn, contents, dt in sorted(find_files_with_time(*args.inputs, ext=".log"), key=lambda x: x[2]):  # earliest first
        outf.write_file(fn, contents.decode("utf-8"))

main()
