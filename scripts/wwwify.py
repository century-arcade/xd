#!/usr/bin/env python3

# Usage: pandoc page.md | wwwify.py [<title> [<current_url>]] > page.html

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from xdfile.html import html_header, html_footer


def main():
    title = sys.argv[1] if len(sys.argv) > 1 else ''
    current_url = sys.argv[2] if len(sys.argv) > 2 else None
    innerhtml = sys.stdin.buffer.read().decode('utf-8')
    htmlstr = html_header(current_url=current_url, title=title) + innerhtml + html_footer()
    # ascii+xmlcharrefreplace: match write_html, locale-proof stdout
    sys.stdout.write(htmlstr.encode('ascii', 'xmlcharrefreplace').decode('ascii') + '\n')


if __name__ == '__main__':
    main()
