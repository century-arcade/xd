#!/usr/bin/env python3

from xdfile.cloud import xd_send_email
import sys

xd_send_email(sys.argv[1], fromaddr='system@xd.saul.pw', subject=sys.argv[2], body=open(sys.argv[3], 'r').read())
