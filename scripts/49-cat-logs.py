#!/usr/bin/env python3

# Usage:
#   $0 -o log.txt products/ 
# 
#  concatenates .log files (even those in subdirs or .zip) and combines into a single combined.log

from xdfile.utils import find_files_with_time, open_output, get_args

def main():
    args = get_args('aggregates all .log files')
    outf = open_output()

    for fn, contents, dt in sorted(find_files_with_time(*args.inputs, ext=".log"), key=lambda x: x[2]):  # earliest first
        outf.write_file(fn, contents.decode("utf-8"))

main()
