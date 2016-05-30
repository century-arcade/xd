#!/usr/bin/env python3

# Usage:
#   $0 -o wwwroot/ gxd/redirects.tsv

from xdfile import html, utils

args = utils.get_args()
outf = utils.open_output()

for tsvfn, contents in utils.find_files(*args.inputs):
    for row in utils.parse_tsv_data(contents.decode('utf-8'), "Redirect"):
        outf.write_file(row.SourcePath, html.redirect_page(row.DestURL))
