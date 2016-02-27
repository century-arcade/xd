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
    <title>{title}</title>
    <LINK href="../style.css" rel="stylesheet" type="text/css">
  </HEAD>
</head>

<body>
<h2>{title}</h2>
"""

index_html_header = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html>

<head>
    <meta http-equiv="Content-Type"
          content="text/html; charset=ISO-8859-1" />
    <title>Published crosswords by similarity</title>
    <LINK href="../style.css" rel="stylesheet" type="text/css">
  </HEAD>
</head>
    <body id="index">
    <div>
    <h2>Published crosswords by similarity</h2>

The earlier puzzle is always on the left side.
<br/>
    """


html_footer = """
  <hr style="clear:both;"/>
      <a href="http://saul.pw">
          <small>saul.pw</small>
    </a>
</div>

<script type="text/javascript">
  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', 'UA-30170773-1']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();
</script>

</body>
</html>
"""

def get_url(xd):
    abbr, d = downloadraw.parse_date_from_filename(xd.filename)

    return downloadraw.get_source(abbr).url(d)

def gendiff(xd1, xd2):
    try:
        desc1 = '<a href="%s">%s</a>' % (get_url(xd1), xd1.filename)
    except:
        desc1 = xd1.filename

    try:
        desc2 = '<a href="%s">%s</a>' % (get_url(xd2), xd2.filename)
    except:
        desc2 = xd2.filename


    pct = findsimilar.grid_similarity(xd1, xd2) * 100

    nsquares = len(xd1.grid) * len(xd1.grid[0])

    shared = findsimilar.same_answers(xd1, xd2)
   
    ret = html_header.format(title="%d%% similar grids, %d/%d shared answers" % (pct, len(shared), len(xd2.clues)))

    s1 = xd1.to_unicode()
    s2 = xd2.to_unicode()

    hd = difflib.HtmlDiff(linejunk=lambda x: False)
    diff_html = hd.make_table(s1.splitlines(), s2.splitlines(), fromdesc=desc1, todesc=desc2, numlines=False)

    ret += diff_html

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

        if True:
            abbr, d1 = downloadraw.parse_date_from_filename(fn1)
            abbr, d2 = downloadraw.parse_date_from_filename(fn2)
            if d2 < d1:
                fn1, fn2 = fn2, fn1 # always older on left
        else:
            pass # no date in filename

        if (fn1, fn2) in index_list:
            continue

        xd1 = xdfile.xdfile(file(fn1).read(), fn1)
        xd2 = xdfile.xdfile(file(fn2).read(), fn2)

        ret, pct = gendiff(xd1, xd2)

        if not ret:
            print "%d%%, skipping" % pct
            continue

        b1 = xdfile.get_base_filename(fn1)
        b2 = xdfile.get_base_filename(fn2)
        outfn = "%s-%s.html" % (b1, b2)

        file(OUTPUT_DIR + "/" + outfn, 'w').write(ret.encode("utf-8"))

        index_line = '%d%% <a href="%s">%s - %s</a>' % (pct, outfn, b1, b2)
        aut1 = xd1.get_header("Author")
        aut2 = xd2.get_header("Author")

        if aut1 != aut2:
            index_line += ' <b>%s | %s</b>' % (aut1, aut2)
        else:
            index_line += ' %s' % aut1

        index_list[(fn1, fn2)] = (pct, index_line, b1, b2)

    index_html = file("%s/index.html" % OUTPUT_DIR, 'w')

    index_html.write(index_html_header)

    matches = sorted((b2, L) for pct, L, b1, b2 in index_list.values() if pct >= 75)
    partials = sorted((b2, L) for pct, L, b1, b2 in index_list.values() if pct >= 50 and pct < 75)
    themes = sorted((b2, L) for pct, L, b1, b2 in index_list.values() if pct >= 25 and pct < 50)

    index_html.write('<ul>')

    index_html.write("\n<h3>Matches (%d)</h3>" % len(matches))
    for b1, L in sorted(matches):
        index_html.write('\n<li>' + L + '</li>')

    index_html.write("\n<h3>Partial matches (%d)</h3>" % len(partials))
    for b1, L in sorted(partials):
        index_html.write('\n<li>' + L + '</li>')

    index_html.write("\n<h3>Possible theme reuse (%d)</h3>" % len(themes))
    for b1, L in sorted(themes):
        index_html.write('\n<li>' + L + '</li>')

    index_html.write('</ul>')
    
    index_html.write(html_footer)

