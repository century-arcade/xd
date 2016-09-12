#!/usr/bin/python3

# Usage:
#   $0 -o wwwroot/ pagebody.html [...]

from xdfile import html, utils

def main():
    args = utils.get_args()
    outf = utils.open_output()

    for htmlfn, contents in utils.find_files(*args.inputs):
        basepagename = utils.parse_pathname(htmlfn).base

        outf.write_html('%s/index.html' % basepagename, contents)

if __name__ == "__main__":
    main()

