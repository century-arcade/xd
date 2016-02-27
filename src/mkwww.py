#!/usr/bin/python

import sys
import os.path
import datetime
import difflib

import xdfile
import downloadraw
import findsimilar

html_header = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html>

<head>
    <meta http-equiv="Content-Type"
          content="text/html; charset=ISO-8859-1" />
    <title>{title}</title>
    <LINK href="style.css" rel="stylesheet" type="text/css">
  </HEAD>
</head>

<body>
<h2>{title}</h2>
"""

html_footer = """
  <hr style="clear:both;"/>
  <div><a href="http://saul.pw"><small>saul.pw</small></a></div>

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
        desc1 = '<a href="">%s</a>' % xd1.filename

    try:
        desc2 = '<a href="%s">%s</a>' % (get_url(xd2), xd2.filename)
    except:
        desc2 = '<a href="">%s</a>' % xd2.filename


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

    pubid = sys.argv[1]
    if len(sys.argv) > 2:
        inputfn = sys.argv[2]
    else:
        inputfn = "crosswords/%s/similar.txt" % pubid

    OUTPUT_DIR = "www/xdiffs/" + pubid

    pubxd = xdfile.xdfile(file("crosswords/%s/meta.txt" % pubid).read()) # just to parse some cached metadata

    index_list =  { } # [(olderfn, newerfn)] -> (pct, index_line)

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

        try:
            xd1 = xdfile.xdfile(file(fn1).read(), fn1)
            xd2 = xdfile.xdfile(file(fn2).read(), fn2)
        except Exception, e:
            print str(e)
            continue
            

        ret, pct = gendiff(xd1, xd2)

        if not ret:
            print "%d%%, skipping" % pct
            continue

        b1 = xdfile.get_base_filename(fn1)
        b2 = xdfile.get_base_filename(fn2)
        outfn = "%s-%s.html" % (b1, b2)

        file(OUTPUT_DIR + "/" + outfn, 'w').write(ret.encode("utf-8"))

        index_line = '%d%% <a href="%s">%s - %s</a>' % (pct, outfn, b1, b2)
        aut1 = (xd1.get_header("Author") or xd1.get_header("Creator") or "")
        aut2 = (xd2.get_header("Author") or xd2.get_header("Creator") or "")
        if aut1.startswith("By "):
            aut1 = aut1[3:]
        if aut2.startswith("By "):
            aut2 = aut2[3:]

        if aut1 != aut2:
            index_line += ' <b>%s | %s</b>' % (aut1, aut2)
        else:
            index_line += ' %s' % aut1

        index_list[(fn1, fn2)] = (pct, index_line, b1, b2)

    out = html_header.format(title="%s crossword similarity" % pubid)

    out += "The left side is always the earlier published puzzle.  Each group is sorted by the right-side publisher and then date.  <b>Bold</b> highlights that the authors are different for the two puzzles.<br/>"

    out += "<br/>%s has %s crosswords from %s" % (pubid, pubxd.get_header("num_xd"), pubxd.get_header("years"))


    matches = sorted((b2, L) for pct, L, b1, b2 in index_list.values() if pct >= 80)
    partials = sorted((b2, L) for pct, L, b1, b2 in index_list.values() if pct >= 50 and pct < 80)
    themes = sorted((b2, L) for pct, L, b1, b2 in index_list.values() if pct >= 20 and pct < 50)

    out += '<ul>'

    out += "\n<h3>%d puzzles match 80-100%% of another grid</h3>" % len(matches)
    for b1, L in sorted(matches):
        out += '\n<li>' + L + '</li>'

    out += "\n<h3>%d puzzles partially match 50-80%% of another grid</h3>" % len(partials)
    for b1, L in sorted(partials):
        out += '\n<li>' + L + '</li>'

    out += '<hr/>'
    out += "\n<h3>%d puzzles may reuse theme entries, matching 20-50%% of another grid</h3>" % len(themes)
    for b1, L in sorted(themes):
        out += '\n<li>' + L + '</li>'

    if len(matches) + len(partials) + len(themes) < 3:
        out += "\n<h3>some dregs (<20%)</h3>"
        dregs = sorted(((pct, L) for pct, L, b1, b2 in index_list.values() if pct < 20), reverse = True)
        for pct, L in sorted(dregs):
            out += '\n<li>' + L + '</li>'

    out += '</ul>'
    
    out += html_footer
    file("%s/index.html" % OUTPUT_DIR, 'w').write(out)


