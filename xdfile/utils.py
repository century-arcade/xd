from collections import namedtuple, OrderedDict
import re
import os
import functools
import stat
import sys
import zipfile
import io
import csv
import string
import codecs
import datetime
import time
import argparse
import fnmatch

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

WEEKDAYS = [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun' ]

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def space_with_nbsp(text):
    """ Replace spaces with ;nbsp; """
    return text.replace(' ', '&nbsp;')

def split_xdid(xdid):
    """ Split xdid [nyt2015-07-01] into set
    If not matched return None
    """
    m = re.match('([a-z]+)(\d{4})-(\d{2})-(\d{2})', xdid)
    return m.groups() if m else [ None, None, None, None ] 

def br_with_n(text):
    """ Replace br with \n """
    return re.sub(r'<br.*?>','\n', text, flags=re.IGNORECASE)

def get_log():
    return EOL.join(g_logs) + EOL

def log(s, minverbose=0, severity='INFO'):
    # This can be made in more Python way
    if g_logfp.isatty(): # Colors only for atty term
        if severity.lower() == 'warning':
            s = bcolors.WARNING + s + bcolors.ENDC
        if severity.lower() == 'error':
            s = bcolors.FAIL + s + bcolors.ENDC

    if g_logfp:
        g_logfp.write("%s: %s\n" % (severity.upper(), s))
    g_logs.append("%s: [%s] %s" % (g_currentProgress or g_scriptname, severity.upper(), s))

#    if not g_args or g_args.verbose >= minverbose:
#        print(" " + s)

def info(_s, _m=0):
    log(_s, minverbose=_m, severity='info')

def warn(_s, _m=0):
    log(_s, minverbose=_m, severity='warning')

def error(_s, _m=0):
    log(_s, minverbose=_m, severity='error')

def summary(_s, _m=0):
    log(_s, minverbose=_m, severity='summary')

# print without logging if -d
def debug(s):
    if g_args.debug:
        print(" " + s)


def progress(rest=None, every=1):
    global g_currentProgress, g_numProgress
    if not sys.stdout.isatty():
        return
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

def to_timet(y, mon=1, d=1, h=0, m=0, s=0):
    return time.mktime(datetime.datetime(y, mon, d, h, m, s).timetuple())

def generate_zip_files(data):
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        for zi in sorted(zf.infolist(), key=lambda x: x.filename):
            zipdt = to_timet(*zi.date_time)
            yield zi.filename, zf.read(zi), zipdt

    except zipfile.BadZipfile as e:
        error("generate_zip_files(): %s" % str(e))


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
                            info("ignoring dotfile")
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
          error("find_files_with_time(): %s" % str(e))

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
        error("datestr_to_datetime(): %s" % str(e))
        if g_args.debug:
            raise
        dt = datetime.date.today()
    return dt


def parse_xdid(path):
    a = path.rindex('/')
    b = path.rindex('.')
    return path[a+1:b]


def parse_pathname(path):
    # Fix to proper split names like file.xml.1
    ext = os.extsep + os.extsep.join(os.path.basename(path).split(os.extsep)[1:])
    path, fn = os.path.split(path)
    ext = ext if fn else ''
    base = os.path.splitext(fn)[0]
    nt = namedtuple('Pathname', 'path base ext filename')
    return nt(path=path, base=base, ext=ext, filename=fn)


def parse_pubid(fn):
    m = re.search("(^[A-Za-z]*)", parse_pathname(fn).base)
    return m.group(1).lower()


def construct_date(y, m, d):
    thisyear = datetime.datetime.today().year
    year, mon, day = int(y), int(m), int(d)

    if year > 1900 and year <= thisyear:
        pass
    elif year < 100:
        if year >= 0 and year <= thisyear - 2000:
            year += 2000
        else:
            year += 1900
    else:
        debug("year outside 1900-%s: '%s'" % (thisyear, y))
        return None

    if mon < 1 or mon > 12:
        debug("bad month '%s'" % m)
        return None

    if day < 1 or day > 31:
        debug("bad day %s" % d)
        return None

    return datetime.date(year, mon, day)


def parse_iso8601(s):
    m = re.search(r'\d+(-\d+(-\d+))', s)
    if m:
        return m.group(0)


def parse_seqnum(s):
    m = re.search(r'-?\d+(-\d+(-\d+))', s)
    if m:
        return m.group(0)

# from original filename
def parse_date_from_filename(fn):
    base = parse_pathname(fn).base
    m = re.search("(\d{2,4})-?(\d{2})-?(\d{2})", base)
    if m:
        g1, g2, g3 = m.groups()
        # try YYMMDD first, then MMDDYY
        return construct_date(g1, g2, g3) or construct_date(g3, g1, g2)


def clean_filename(fn):
    badchars = """ "'\\"""

    basefn = parse_pathname(fn).base
    for ch in badchars:
        basefn = basefn.replace(ch, '_')

    return basefn


# newext always includes the '.' so it can be removed entirely with newext=""
def replace_ext(fn, newext):
    base, ext = os.path.splitext(fn)
    return base + newext


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

#class AttrDict(dict):
#    __getattr__ = dict.__getitem__
#    __setattr__ = dict.__setitem__

def autoconvert(v):
    if v is None:
        return ''
    elif v.isdigit():
        return int(v)
    else:
        return v


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
            r = AttrDict((k, autoconvert(v)) for k, v in row.items())
        else:
            r = AttrDict(row)
        yield r


def parse_tsv(fn, objname=None):
    try:
        fp = codecs.open(fn, encoding='utf-8')
        rows = parse_tsv_data(fp.read(), objname)
        return dict((r[0], r) for r in rows)
    except Exception as e:
        error("parse_tsv('%s') %s" % (fn, str(e)))
        if g_args.debug:
            raise
        return {}


def parse_tsv_rows(fn, objname=None):
    try:
        fp = codecs.open(fn, encoding='utf-8')
        return [r for r in parse_tsv_data(fp.read(), objname)]
    except Exception as e:
        error("parse_tsv_rows('%s'): %s" % (fn, str(e)))
        if g_args.debug:
            raise
        return []


class OutputZipFile(zipfile.ZipFile):
    def __init__(self, fnzip, toplevel="", log=True):
        zipfile.ZipFile.__init__(self, fnzip, 'w', allowZip64=True)
        self.toplevel = toplevel
        self.log = log

    def write_file(self, fn, contents, timet=None):
        if not timet:
            timet = time.time()

        fullfn = os.path.join(self.toplevel, fn)

        zi = zipfile.ZipInfo(fullfn, datetime.datetime.fromtimestamp(timet).timetuple())
        zi.external_attr = 0o444 << 16
        zi.compress_type = zipfile.ZIP_DEFLATED
        self.writestr(zi, contents)
        if g_args.debug:
            debug("wrote %s to %s" % (fullfn, self.filename))

    def write(self, data):
        raise Exception("can't write directly to .zip")

    def __del__(self):
        if self.log:
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
        from .html import html_header, html_footer

        basepagename = parse_pathname(fn).path
        htmlstr = html_header(current_url=basepagename, title=title) + innerhtml + html_footer()
        self.write(htmlstr.encode("ascii", 'xmlcharrefreplace').decode("ascii"))


def strip_toplevel(fn):
    if "/" in fn:
        return "/".join(fn.split("/")[1:])  # strip off leading directory
    else:
        return fn


def disambiguate_fn(fn, all_filenames):
    p = parse_pathname(fn)
    # append a, b, c, etc until finding one that hasn't been taken already
    i = 0
    while fn in all_filenames:
        info('%s already in use, disambiguating' % fn)
        fn = os.path.join(p.path, p.base + string.ascii_lowercase[i] + p.ext)
        i += 1

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
            if mode == 'a':
                # just keep appending to same file
                return self.files[fn]

            if mode == 'w':
                # make a new file with a disambiguated filename
                fn = disambiguate_fn(fn, self.files)

        fullfn = os.path.join(self.toplevel, fn)  #  prepend our toplevel

        # make parent dirs
        try:
            os.makedirs(parse_pathname(fullfn).path)
        except Exception as e:
            pass  # log("%s: %s" % (type(e), str(e)))

        f = codecs.open(fullfn, mode, encoding='utf-8')
        if mode[0] == 'a':
            self.files[fn] = f
        elif mode[0] == 'w':
            self.files[fn] = 'written once already'

        return f

    def close_file(self, fn):
        del self.files[fn]

    def write_file(self, fn, contents, timet=None):
        with self.open_file(fn, 'w') as f:
            f.write(contents)
        debug("wrote %s to %s" % (fn, self.toplevel))

    def write_html(self, fn, innerhtml, title=""):
        from .html import html_header, html_footer

        htmlstr = html_header(title=title) + innerhtml + html_footer()
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


# from https://wiki.python.org/moin/PythonDecoratorLibrary#Alternate_memoize_that_stores_cache_between_executions
# note that this decorator ignores **kwargs
def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        if args not in cache:
            cache[args] = obj(*args, **kwargs)
        return cache[args]
    return memoizer

# reversed xml escape table
rev_xml_escape_table = {
    '&apos;' : "'",
    '&quot;' : '"',
    '&amp;' : '&',
}

xml_escape_table = OrderedDict((
    ("’" , "'"),
    ("<b>", "{*"),
    ("</b>", "*}"),
    ("<i>", "{/"),
    ("</i>", "/}"),
    ("<em>", "{/"),
    ("</em>", "/}"),
    ("<u>", "{_"),
    ("</u>", "_}"),
    ("<strike>", "{-"),
    ("</strike>", "-}"),
    ("<92>", "&apos;"),
    ('&#34;', '&quot;'),
    ('&#39;', "'"),
    ('&#38;', "&amp;"),
    ('&', '&amp;'),
    ('"<"' , '"%3C"'),
    ('="" ', "=''"),
    ('…', "..."),
    ("\xC3\x82", ""), # Don't know what it this symbol for
    ('=""' + EOL, "=''" + EOL),
    ("\x05", "'"), # ^E seems to be junk
    ("\x12", "'"),  # ^R seems to be '
    ("\xC2\xA0", " "), # replace nbsp with space
    ("%C2%A0", " "), # replace nbsp with space
    ("%C3%82%27", "'"), # apostrophe
    ("\xA0", " "), # replace what left from nbsp with space
    ))
"""
xml_escape_table = {
    "’" : "'",
    "<b>": "{*",
    "</b>": "*}",
    "<i>": "{/",
    "</i>": "/}",
    "<em>": "{/",
    "</em>": "/}",
    "<u>": "{_",
    "</u>": "_}",
    "<strike>": "{-",
    "</strike>": "-}",
    "<92>" : "&apos;",
    '&#34;' : '"',
    '&#39;' : "'",
    '&': '&amp;',
    '"<"' : '"%3C"',
    '="" ' : "=''",
    '…' : "...",
    "\xC3\x82" : "", # Don't know what it this symbol for
    '=""' + EOL : "=''" + EOL,
    "\x05": "'", # ^E seems to be junk
    "\x12" : "'",  # ^R seems to be '
    "\xC2\xA0" : " ", # replace nbsp with space
    "%C2%A0" : " ", # replace nbsp with space
    "%C3%82%27" : "'", # apostrophe
    "\xA0" : " ", # replace what left from nbsp with space
}
"""

def __dict_replace(s, d):
    """Replace substrings of a string using a dictionary."""
    for key, value in d.items():
        s = s.replace(key, value)
    return s

def escape(data, entities={}):
    """Escape a string of data.
    based on: xml.sax.saxutils escape()
    """
    if entities:
        data = __dict_replace(data, entities)

    # finally, replace any leftover & with &amp so they will be properly
    # unescaped back to & later (otherwise xml parser drops them)
    #data.replace('&', '&amp;')
    return data

def consecutive(text):
    """ Remove two consecutive lines if equal """
    ret = []
    for l in text.splitlines():
        if not ret:
            ret.append(l)
        elif l != ret[-1]:
            ret.append(l)
    return EOL.join(ret)


