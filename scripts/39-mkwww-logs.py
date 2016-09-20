#!/usr/bin/env python3

# Usage:
#   $0 -o wwwroot/ products/ 
# 
#  takes all .log files and generates wwwroot/<YYYYMMDD>/index.html

import cgi

from xdfile.utils import find_files_with_time, open_output, get_args, iso8601

def main():
    args = get_args('aggregates all .log files into one .html')
    outwww = open_output()
    log_html = ''
    for fn, contents, dt in sorted(find_files_with_time(*args.inputs, ext=".log"), key=lambda x: x[2]):  # earliest first
        log_html += '\n\n<h2>%s</h2><pre>%s</pre>' % (fn, cgi.escape(contents.decode("utf-8")))

    datestr = iso8601()
    outwww.write_html("logs.html", log_html, title="logs for " + datestr)

main()
