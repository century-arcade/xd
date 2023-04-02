#!/usr/bin/env python3

import sys
import time

def html_header(title='xd page'):
    # npuzzles = len(xdfile.g_corpus)
    h = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html>

<head>
    <meta http-equiv="Content-Type"
          content="text/html; charset=ISO-8859-1" />
    <title>{title}</title>
    <LINK href="/style.css" rel="stylesheet" type="text/css">
  </HEAD>
</head>

<body>
""".format(title=title)


    #h += '<nav id="primary_nav_wrap">'
    #h += navbar_helper(navbar_items, current_url)
    #h += '</nav>'

    h += '<hr style="clear:both;"/>'
    h += '<h2>{title}</h2>'.format(title=title)

    #if npuzzles:
        # h += ' from a corpus of {npuzzles} puzzles'.format(npuzzles=npuzzles)

    return h



def html_footer():
    dt = time.strftime('%F')
    return """
  <hr style="clear:both;"/>
<small><i>Generated on {date}</i>
<br>
a <a href="mailto:xd@saul.pw">saul.pw</a> project
</small>
</body>
</html>
""".format(date=dt)


def main():
    title = sys.argv[1] if len(sys.argv) > 1 else 'xd page'
    innerhtml = sys.stdin.read()
    htmlstr =html_header(title=title) + innerhtml + html_footer()
    print(htmlstr)


if __name__ == '__main__':
    main()
