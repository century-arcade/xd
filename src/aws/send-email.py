#!/usr/bin/env python3

import xdfile.cloud
import sys

xdfile.cloud.xd_send_email(sys.argv[1], fromaddr='system@xd.saul.pw', subject=sys.argv[2], body=open(sys.argv[3], 'r').read())
