# -*- coding: utf-8 -*-
import sys

PY3 = sys.version_info[0] >= 3

if PY3:
    range = range
    basestring = str
    str = str
else:
    range = xrange
    basestring = (unicode, str)
    str = unicode
