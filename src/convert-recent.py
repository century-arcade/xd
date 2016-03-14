#!/usr/bin/env python

import os.path
import sys
import zipfile
import xdfile

from ccxml2xd import parse_ccxml
from uxml2xd import parse_uxml
from ujson2xd import parse_ujson
from puz2xd import parse_puz
from xwordinfo2xd import parse_xwordinfo

def try_parse(puz, fn):
    errors = [ ]

    # just try everything to convert the puzzle
    funcs = [ parse_ccxml, parse_uxml, parse_ujson, parse_puz, parse_xwordinfo ]
    for f in funcs:
        try:
            xd = f(puz, fn)
            if xd:
                return xd, errors
            else:
                raise Exception("returned nothing")
        except Exception, e:
            errors.append("%s: %s" % (f.__name__, str(e)))

    return None, errors

def main():
    import argparse
    parser = argparse.ArgumentParser(description='convert recent puzzles to .xd')

    parser.add_argument('inputs', nargs='+', default=None, help='input .zip file')
    args = parser.parse_args()

    all_files = { }

    for zipfn in args.inputs:
      rawzf = zipfile.ZipFile(zipfn, 'r')

      for zi in rawzf.infolist():
        print "\rreading " + zi.filename, "   ",

        base, ext = os.path.splitext(zi.filename)

        contents = rawzf.read(zi)
        if base.endswith("-meta"):
            base = base[:-5]
            if base in all_files:
                all_files[base][2] = contents
            else:
                print "no puzzle data for meta"
        else:
            assert base not in all_files, "not unique base: " + base
            all_files[base] = [ ext, contents, None ]

    for base, pair in sorted(all_files.items()):
        ext, puz, meta = pair
        if ext in ".pdf .log".split():
            continue

        print "converting", base + ext,

        xd = None

        xd, errors = try_parse(puz, base + ext)
        if not xd:
            print '\n\t' + "\n\t".join(errors)
        else:
            for k, v in xdfile.xdfile(meta).headers:
                assert not xd.get_header(k)
                xd.headers.append((k, v))

            xdstr = xd.to_unicode().encode("utf-8")

            with file(base + ".xd", 'w') as outxd:
                outxd.write(xdstr)

            print "converted (%s bytes)" % len(xdstr)

if __name__ == "__main__":
    main()

