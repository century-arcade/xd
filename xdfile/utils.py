
from __future__ import print_function

from collections import namedtuple
import re
import os
import stat
import sys
import zipfile
import csv
import datetime
import time
import argparse

EOL = '\n'
COLUMN_SEPARATOR = '\t'

g_logs = []   # get with get_log()
g_args = None  # get with args()
g_currentProgress = None
g_numProgress = 0


def get_log():
    return EOL.join(g_logs)


def log(s, minverbose=0):
    g_logs.append("%s: %s" % (g_currentProgress or parse_pathname(sys.argv[0]).base, s))

    if g_args.verbose >= minverbose:
        print(" " + s.encode("utf-8"))


# print without logging if -d
def debug(s):
    if g_args.debug:
        print(" " + s.encode("utf-8"))


def progress(rest="", every=1):
    global g_currentProgress, g_numProgress
    if rest:
        g_numProgress += 1
        g_currentProgress = rest
        if g_numProgress % every == every - 1:
            print("\r% 6d %s" % (g_numProgress, rest), end="")
    else:
        g_currentProgress = ""
        g_numProgress = 0
        print()


def args_parser(desc=""):
    return argparse.ArgumentParser(description=desc)


def get_args(desc="", parser=None):
    global g_args

    if g_args:
        return g_args

    if not parser:
        parser = args_parser(desc)

    parser.add_argument('inputs', nargs='*', help='toplevel input(s)')
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

                    if ext and not fn.endswith(ext):  # only looking for one particular ext, don't log
                        continue

                    fullfn = os.path.join(thisdir, fn)
                    progress(fullfn)

                    if fn[0] == ".":
                        log("ignoring dotfile")
                        continue

                    yield fullfn, file(fullfn).read()
        else:
            try:
                # handle .zip files
                with zipfile.ZipFile(path, 'r') as zf:
                    for zi in sorted(zf.infolist(), key=lambda x: x.filename):
                        if ext and not zi.filename.endswith(ext):  # as above
                            continue

                        fullfn = zi.filename
                        progress(fullfn)

                        contents = zf.read(zi)
                        yield fullfn, contents
            except zipfile.BadZipfile:
                # handle individual files
                fullfn = path
                contents = file(path).read()
                yield fullfn, contents

    # reset progress indicator after processing all files
    progress()


def zip_create(fn):
     return zipfile.ZipFile(fn, 'w', allowZip64=True)



def filetime(fn):
    try:
        return os.path.getmtime(fn)
    except:
        return time.time()


def iso8601(timet):
    return datetime.datetime.fromtimestamp(int(timet)).isoformat(' ').split(' ')[0]


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
def parse_tsv(contents, objname):
    csvreader = csv.DictReader(contents.splitlines(), delimiter=COLUMN_SEPARATOR, quoting=csv.QUOTE_NONE)
    nt = namedtuple(objname, " ".join(csvreader.fieldnames))
    return [nt(**row) for row in csvreader]


def parse_xdid(xdid):
    m = re.search(r'([a-z]+)(\d+)-(\d+)-(\d+)', xdid)
    if m:
        abbr, y, m, d = m.groups()
        return abbr, datetime.date(int(y), int(m), int(d))
    else:
        log("no xdid found in '%s'" % xdid)


class OutputZipFile(zipfile.ZipFile):
    def __init__(self, fnzip, toplevel=""):
        zipfile.ZipFile.__init__(self, fnzip, 'w', allowZip64=True)
        self.toplevel = toplevel

    def write_file(self, fn, contents, timet=None):
        if not timet:
            timet = time.time()

        fullfn = os.path.join(self.toplevel, fn)

        zi = zipfile.ZipInfo(fullfn, datetime.datetime.fromtimestamp(timet).timetuple())
        zi.external_attr = 0444 << 16L
        zi.compress_type = zipfile.ZIP_DEFLATED
        self.writestr(zi, contents)

    def write(self, data):
        raise Exception("can't write directly to .zip")


class OutputFile:
    def __init__(self, outfp=None):
        self.toplevel = "xd"
        self.outfp = outfp

    def write_file(self, fn, contents, timet=None):
        self.outfp.write("\n--- %s ---\n" % fn)
        self.outfp.write(contents)

    def write(self, data):
        self.outfp.write(data)


def strip_toplevel(fn):
    return "/".join(fn.split("/")[1:])  # strip off leading directory

class OutputDirectory:
    def __init__(self, toplevel_dir):
        self.toplevel = toplevel_dir

    def write_file(self, fn, contents, timet=None):
        if not timet:
            timet = time.time()

        fullfn = os.path.join(self.toplevel, fn)  #  prepend our toplevel

        # make parent dirs
        try:
            os.makedirs(parse_pathname(fullfn).path)
        except Exception, e:
            pass  # log("%s: %s" % (type(e), str(e)))

        file(fullfn, 'w').write(contents)


def open_output(fnout=None):
    assert g_args

    if not fnout:
        fnout = g_args.output

    if not fnout:
        outf = OutputStdout()
    elif fnout.endswith(".zip"):
        outf = OutputZipFile(fnout, parse_pathname(fnout).base)
    elif not parse_pathname(fnout).ext:  # extensionless assumed to be directories
        outf = OutputDirectory(fnout)
    else:
        outf = OutputFile(file(fnout, 'w'))

    return outf
