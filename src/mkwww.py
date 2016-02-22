#!/usr/bin/python

import sys
import os.path
import datetime
import difflib

import xdfile
import downloadraw
import findsimilar

OUTPUT_DIR = "www/diffs/"

html_header = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html>

<head>
    <meta http-equiv="Content-Type"
          content="text/html; charset=ISO-8859-1" />
    <title>Crossword comparison</title>
    <style type="text/css">
        body { margin: auto; width: 800px; }
        table.diff {font-family:Courier; border:medium;}
        .diff_header {  background-color:#e0e0e0; color: #e0e0e0 }
        td.diff_header { text-align:right; width: 0px}
        table.diff td { padding-left: 5px }
        .diff_next {display: none; }
        .diff_add {background-color:#aaffaa}
        .diff_chg {background-color:#ffff77}
        .diff_sub {background-color:#ffaaaa}
    </style>
</head>

<body>
"""

html_footer = """
    <!--table class="diff" summary="Legends">
        <tr> <th colspan="2"> Legends </th> </tr>
        <tr> <td> <table border="" summary="Colors">
                      <tr><th> Colors </th> </tr>
                      <tr><td class="diff_add">&nbsp;Added&nbsp;</td></tr>
                      <tr><td class="diff_chg">Changed</td> </tr>
                      <tr><td class="diff_sub">Deleted</td> </tr>
                  </table></td>
             <td> <table border="" summary="Links">
                      <tr><th colspan="2"> Links </th> </tr>
                      <tr><td>(f)irst change</td> </tr>
                      <tr><td>(n)ext change</td> </tr>
                      <tr><td>(t)op</td> </tr>
                  </table></td> </tr>
    </table-->
</body>
</html>
"""

def get_url(xd):
    abbr, d = downloadraw.parse_date_from_filename(xd.filename)

    return downloadraw.get_source(abbr).url(d)

def get_base_filename(fn):
    path, b = os.path.split(fn)
    b, ext = os.path.splitext(b)

    return "".join(b.split("-"))

def gendiff(xd1, xd2):
    try:
        desc1 = '<a href="%s">%s</a>' % (get_url(xd1), xd1.filename)
    except:
        desc1 = xd1.filename

    try:
        desc2 = '<a href="%s">%s</a>' % (get_url(xd2), xd2.filename)
    except:
        desc2 = xd2.filename

    ret = html_header

    pct = findsimilar.grid_similarity(xd1, xd2) * 100

    nsquares = len(xd1.grid) * len(xd1.grid[0])
    if pct < 25:
        return "", pct

    shared = findsimilar.same_answers(xd1, xd2)
    ret += "<h2>%d%% similar grids, %d/%d shared answers</h2>" % (pct, len(shared), len(xd2.clues))
   
    s1 = xd1.to_unicode().splitlines()
    s2 = xd2.to_unicode().splitlines()
    hd = difflib.HtmlDiff(linejunk=lambda x: False)
    ret += hd.make_table(s1, s2, fromdesc=desc1, todesc=desc2, numlines=False)

    ret += "<br/>Shared answers: %s" % " ".join(shared)

    ret += html_footer

    return ret, pct


if __name__ == "__main__":

    index_list =  { } # [(olderfn, newerfn)] -> (pct, index_line)

    for inputfn in sys.argv[1:]:
      for line in file(inputfn).read().splitlines():
        if not line: continue
        fn1, fn2 = line.strip().split()
        print fn1, fn2

        try:
            abbr, d1 = downloadraw.parse_date_from_filename(fn1)
            abbr, d2 = downloadraw.parse_date_from_filename(fn2)
            if d2 < d1:
                fn1, fn2 = fn2, fn1 # always older on left
        except:
            pass # no date in filename

        if (fn1, fn2) in index_list:
            continue

        xd1 = xdfile.xdfile(file(fn1).read(), fn1)
        xd2 = xdfile.xdfile(file(fn2).read(), fn2)

        ret, pct = gendiff(xd1, xd2)

        if not ret:
            print "%d%%, skipping" % pct
            continue

        b1 = get_base_filename(fn1)
        b2 = get_base_filename(fn2)
        outfn = "%s-%s.html" % (b1, b2)

        file(OUTPUT_DIR + "/" + outfn, 'w').write(ret.encode("utf-8"))

        index_line = '%d%% <a href="%s">%s - %s</a>' % (pct, outfn, b1, b2)
        aut1 = xd1.get_header("Author")
        aut2 = xd2.get_header("Author")

        if aut1 != aut2:
            index_line += ': %s | %s' % (aut1, aut2)

        index_list[(fn1, fn2)] = (pct, index_line)

    index_html = file("%s/index.html" % OUTPUT_DIR, 'w')

    index_html.write('<body style="margin:auto; width:800px; background-color: #ffeeee">')
    index_html.write('<div style="padding: 10px; background-color: #ffeeee">')
    index_html.write('<h2 style="text-align: center">Published crosswords by similarity</h2>')
    for pct, L in sorted(index_list.values(), reverse=True):
        index_html.write('\n<br>' + L)

    
    index_html.write("</div></body>")

