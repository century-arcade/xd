
from __future__ import print_function

from collections import namedtuple
import os
import stat
import sys
import zipfile
import datetime
import time
import argparse

EOL = '\n'
COLUMN_SEPARATOR = '\t'

g_logs = [ ]   # get with get_logs()
g_args = None  # get with args()
g_currentProgress = None
g_numProgress = 0


def get_log():
    return EOL.join(g_logs)


def log(s, minverbose=0):
    g_logs.append("%s: %s" % (g_currentProgress or sys.argv[0], s))

    if g_args.verbose >= minverbose:
        print(" " + s.encode("utf-8"))


def progress(rest="", every=1):
    global g_currentProgress, g_numProgress
    g_numProgress += 1
    g_currentProgress = rest
    if g_numProgress % every == every-1:
        print("\r% 6d %s" % (g_numProgress, rest), end="")
    if not rest:
        print()


def args_parser(desc=""):
    return argparse.ArgumentParser(description=desc)


def get_args(parser=None, desc=""):
    global g_args

    if g_args:
        return g_args

    if not parser:
        parser = args_parser(desc)

    parser.add_argument('inputs', nargs='+', help='toplevel input(s)')
    parser.add_argument('-o', '--output', dest='output', action='store')
    parser.add_argument('-q', '--quiet', dest='verbose', action='store_const', const=-1, default=0)
    parser.add_argument('-v', '--verbose', dest='verbose', action='count', default=0)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', default=False, help='abort on exception')
    parser.add_argument('-c', '--corpus', dest='corpusdir', default='crosswords', help='corpus source')
    g_args = parser.parse_args()

    return g_args


# walk all 'paths' recursively and yield (filename, contents) for non-hidden files
def find_files(*paths, **kwargs):
    ext = kwargs.get("ext")
    for path in paths:
        if stat.S_ISDIR(os.stat(path).st_mode):
            # handle directories
            for thisdir, subdirs, files in os.walk(path):
                for fn in sorted(files):
                    if ext and fn.endswith(ext):  # only looking for one particular ext, don't log
                        continue

                    fullfn = os.path.join(thisdir, fn)
                    progress(fullfn)

                    if fn[0] == ".":
                        log("ignoring dotfile")
                        continue

                    for f, c in find_files(fullfn):
                        yield f, c
        else:
            try:
                # handle .zip files
                with zipfile.ZipFile(path, 'r') as zf:
                    for zi in sorted(zf.infolist()):
                        fullfn = zi.filename
                        progress(fullfn)

                        contents = zf.read(zi)
                        yield fullfn, contents
            except:
                # handle individual files
                fullfn = path
                contents = file(path).read()
                yield fullfn, contents


def zip_append(zf, fn, contents, timet=None):
    if not timet:
        timet = time.time()
    zi = zipfile.ZipInfo(fn, datetime.datetime.fromtimestamp(timet).timetuple())
    zi.external_attr = 0444 << 16L
    zi.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(zi, contents)


def filetime(fn):
    return os.path.getmtime(fn)


def iso8601(timet):
    return datetime.datetime.fromtimestamp(timet).isoformat(' ')


def parse_pathname(path):
    path, fn = os.path.split(path)
    base, ext = os.path.splitext(fn)
    nt = namedtuple('Pathname', 'path base ext')
    return nt(path=path, base=base, ext=ext)


# newext always includes the '.' so it can be removed entirely with newext=""
def replace_ext(fn, newext):
    base, ext = os.path.splitext(fn)
    return base + newext


# always includes header row
#   returns a sequence of mappings
def parse_tsv(contents):
    return []

