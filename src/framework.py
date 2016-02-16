
def main(parserfunc):
    import os.path
    import sys
    import argparse
    import xdfile

    parser = argparse.ArgumentParser(description='convert crosswords to .xd format')
    parser.add_argument('path', type=str, nargs='+', help='files, .zip, or directories to be converted')
    parser.add_argument('-o', dest='output', default=None,
                   help='output directory (default stdout)')

    args = parser.parse_args()

    for fullfn, contents in xdfile.find_files(*args.path):
        print "\r" + fullfn,
        _, fn = os.path.split(fullfn)
        base, ext = os.path.splitext(fn)
        xd = parserfunc(contents)
        xdstr = xd.to_unicode().encode("utf-8")
        if args.output:
            xdfn = "%s/%s.xd" % (args.output, base)
            file(xdfn, "w-").write(xdstr)
        else:
            print xdstr

    print
