
from collections import namedtuple
import re
import os
import stat
import sys
import zipfile
import io
import csv
import codecs
import datetime
import time
import argparse

from .html import html_header, html_footer

EOL = '\n'
COLSEP = '\t'
COLUMN_SEPARATOR = COLSEP

g_logs = []   # get with get_log()
g_args = None  # get with args()
g_currentProgress = None
g_numProgress = 0

g_logfp = sys.stderr

# save on start to auto-log at end
g_scriptname = None

def get_log():
    return EOL.join(g_logs) + EOL


def log(s, minverbose=0):
    if g_logfp:
        g_logfp.write(s + "\n")
    g_logs.append("%s: %s" % (g_currentProgress or g_scriptname, s))

#    if not g_args or g_args.verbose >= minverbose:
#        print(" " + s)


# print without logging if -d
def debug(s):
    if g_args.debug:
        print(" " + s)


def progress(rest=None, every=1):
    global g_currentProgress, g_numProgress
    if rest:
        g_numProgress += 1
        g_currentProgress = rest
        if g_numProgress % every == 0:
            print("\r% 6d %s " % (g_numProgress, rest), end="")
            sys.stdout.flush()
    else:
        g_currentProgress = ""
        g_numProgress = 0
        print()
        sys.stdout.flush()


def args_parser(desc=""):
    log("[%s]: %s" % (desc, " ".join(sys.argv)))
    return argparse.ArgumentParser(description=desc)


def get_args(desc="", parser=None):
    global g_args, g_scriptname
    g_scriptname = parse_pathname(sys.argv[0]).base

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


def find_files(*paths, **kwargs):
    for fn, data, dt in find_files_with_time(*paths, **kwargs):
        yield fn, data


def generate_zip_files(data):
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        for zi in sorted(zf.infolist(), key=lambda x: x.filename):
            zipdt = time.mktime(datetime.datetime(*zi.date_time).timetuple())
            yield zi.filename, zf.read(zi), zipdt

    except zipfile.BadZipfile as e:
        log(str(e))


# walk all 'paths' recursively and yield (filename, contents) for non-hidden files
def find_files_with_time(*paths, **kwargs):
    ext = kwargs.get("ext")
    should_strip_toplevel = kwargs.get("strip_toplevel", True)
    for path in paths:
      try:
        if stat.S_ISDIR(os.stat(path).st_mode):
            # handle directories
            for thisdir, subdirs, files in os.walk(path):
                for fn in sorted(files):
                    fullfn = os.path.join(thisdir, fn)

                    if fn.endswith('.zip'):
                        for zipfn, zipdata, zipdt in generate_zip_files(open(fullfn, 'rb').read()):
                            if ext and not zipfn.endswith(ext):
                                continue
                            yield fn + ":" + zipfn, zipdata, zipdt

                    elif ext and not fn.endswith(ext):  # only looking for one particular ext, don't log
                        continue

                    else:
                        progress(fullfn)

                        if fn[0] == ".":
                            log("ignoring dotfile")
                            continue

                        yield fullfn, open(fullfn, 'rb').read(), filetime(fullfn)

        elif path.endswith('.zip'):
            for zipfn, zipdata, zipdt in generate_zip_files(open(path, 'rb').read()):
                if ext and not zipfn.endswith(ext):  # as above
                    continue

                progress(zipfn)

                if should_strip_toplevel:
                    zipfn = strip_toplevel(zipfn)

                yield zipfn, zipdata, zipdt

        else: 
            if ext and not path.endswith(ext):
                continue

            # handle individual files
            fullfn = path
            yield fullfn, open(fullfn, 'rb').read(), filetime(fullfn)

      except FileNotFoundError as e:
          log(str(e))

    # reset progress indicator after processing all files
    progress()


def filetime(fn):
    try:
        return os.path.getmtime(fn)
    except:
        return time.time()


# date only
def iso8601(timet=None):
    if not timet:
        timet = time.time()
    return datetime.datetime.fromtimestamp(int(timet)).isoformat(' ').split(' ')[0]


# YYYY-MM-DD to datetime.date
def datestr_to_datetime(s):
    try:
        return datetime.date(*[int(x) for x in s.split("-")])
    except Exception as e:
        log(str(e))
        if g_args.debug:
            raise
        dt = None
    return dt


def parse_pathname(path):
    path, fn = os.path.split(path)
    base, ext = os.path.splitext(fn)
    nt = namedtuple('Pathname', 'path base ext filename')
    return nt(path=path, base=base, ext=ext, filename=fn)


def parse_pubid_from_filename(fn):
    m = re.search("(^[A-Za-z]*)", parse_pathname(fn).base)
    return m.group(1).lower()


# newext always includes the '.' so it can be removed entirely with newext=""
def replace_ext(fn, newext):
    base, ext = os.path.splitext(fn)
    return base + newext


# should always include header row
#   returns a sequence of mappings or tuples, depending on whether objname is specified
def parse_tsv_data(contents, objname=None):
    csvreader = csv.DictReader(contents.splitlines(), delimiter=COLUMN_SEPARATOR, quoting=csv.QUOTE_NONE, skipinitialspace=True)
    if objname:
        if not csvreader.fieldnames:
            return

        nt = namedtuple(objname, " ".join(csvreader.fieldnames))

    for row in csvreader:
        if objname:
            r = nt(**row)
        else:
            r = row

        yield r

def parse_tsv(fn, objname=None):
    fp = codecs.open(fn, encoding='utf-8')
    return dict((r[0], r) for r in parse_tsv_data(fp.read(), objname))


class OutputZipFile(zipfile.ZipFile):
    def __init__(self, fnzip, toplevel=""):
        zipfile.ZipFile.__init__(self, fnzip, 'w', allowZip64=True)
        self.toplevel = toplevel

    def write_file(self, fn, contents, timet=None):
        if not timet:
            timet = time.time()

        fullfn = os.path.join(self.toplevel, fn)

        zi = zipfile.ZipInfo(fullfn, datetime.datetime.fromtimestamp(timet).timetuple())
        zi.external_attr = 0o444 << 16
        zi.compress_type = zipfile.ZIP_DEFLATED
        self.writestr(zi, contents)

        log("wrote %s to %s" % (fullfn, self.filename))

    def write(self, data):
        raise Exception("can't write directly to .zip")

    def __del__(self):
        self.write_file(g_scriptname + ".log", get_log().encode('utf-8'))
        zipfile.ZipFile.__del__(self)


class OutputFile:
    def __init__(self, outfp=None):
        self.toplevel = "xd"
        self.outfp = outfp

    def write_file(self, fn, contents, timet=None):
        self.outfp.write("\n--- %s ---\n" % fn)
        self.outfp.write(contents)

    def write(self, data):
        self.outfp.write(data)

    def write_row(self, fields):
        self.write(COLUMN_SEPARATOR.join(fields) + EOL)

    def write_html(self, fn, innerhtml, title=""):
        htmlstr = html_header(title=title) + innerhtml + html_footer
        self.write(htmlstr.encode("ascii", 'xmlcharrefreplace').decode("ascii"))


def strip_toplevel(fn):
    if "/" in fn:
        return "/".join(fn.split("/")[1:])  # strip off leading directory
    else:
        return fn

class OutputDirectory:
    def __init__(self, toplevel_dir):
        self.toplevel = toplevel_dir
        self.files = {}

    def exists(self, fn):
        fullfn = os.path.join(self.toplevel, fn)  #  prepend our toplevel
        return os.path.exists(fullfn)

    def open_file(self, fn, mode='w'):
        if fn in self.files:
            return self.files[fn]

        fullfn = os.path.join(self.toplevel, fn)  #  prepend our toplevel

        # make parent dirs
        try:
            os.makedirs(parse_pathname(fullfn).path)
        except Exception as e:
            pass  # log("%s: %s" % (type(e), str(e)))

        f = codecs.open(fullfn, mode, encoding='utf-8')
        self.files[fn] = f
        return f

    def write_file(self, fn, contents, timet=None):
        self.open_file(fn, 'w').write(contents)
        log("wrote %s to %s" % (fn, self.toplevel))

    def write_html(self, fn, innerhtml, title=""):
        htmlstr = html_header(title=title) + innerhtml + html_footer
        self.write_file(fn, htmlstr.encode("ascii", 'xmlcharrefreplace').decode("ascii"))


    def write_row(self, fn, headerstr, values):
        write_header = not self.exists(fn)
            
        fp = self.open_file(fn, 'a')

        if write_header:
            fp.write(COLUMN_SEPARATOR.join(headerstr.split()) + EOL)

        fp.write(COLUMN_SEPARATOR.join(str(x) for x in values) + EOL)


def open_output(fnout=None):
    assert g_args
    global g_logfp

    if not fnout:
        fnout = g_args.output

    if not fnout:
        outf = OutputFile(sys.stdout)
    elif fnout.endswith(".zip"):
        outf = OutputZipFile(fnout, parse_pathname(fnout).base)
    elif not parse_pathname(fnout).ext:  # extensionless assumed to be directories
        outf = OutputDirectory(fnout)
#        g_logfp = outf.open_file(g_scriptname + ".log")
    else:
        # make parent dirs
        try:
            os.makedirs(parse_pathname(fnout).path)
        except Exception as e:
            pass  # log("%s: %s" % (type(e), str(e)))
        outf = OutputFile(codecs.open(fnout, 'w', encoding="utf-8"))

    return outf

