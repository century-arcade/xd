#!/usr/bin/python3

# Usage: $0 -o xd-public.zip gxd/

# makes .zip of all public .xd files

from xdfile import metadatabase as metadb
from xdfile import utils


def main():
    args = utils.get_args()
    outf = utils.open_output()  # should be .zip

    outf.log = False
    outf.toplevel = 'xd'
    outf.write_file('README', open('doc/zip-README').read())

    for fn, contents in sorted(utils.find_files(*args.inputs, ext='.xd')):
        xdid = utils.parse_xdid(fn)
        if metadb.is_public(xdid):
            outf.write_file(utils.strip_toplevel(fn), contents)


if __name__ == "__main__":
    main()
