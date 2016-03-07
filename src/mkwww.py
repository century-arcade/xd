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
<h1>{title}</h1>
"""

html_footer = """
  <hr style="clear:both;"/>
  <a href="http://saul.pw"><small>saul.pw</small></a>

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

    shared = findsimilar.same_answers(xd1, xd2)
   
    ret = html_header.format(title="%d%% similar grids, %d/%d shared answers" % (pct, len(shared), len(xd2.clues)))

    s1 = xd1.to_unicode()
    s2 = xd2.to_unicode()

    hd = difflib.HtmlDiff(linejunk=lambda x: False)
    diff_html = hd.make_table(s1.splitlines(), s2.splitlines(), fromdesc=desc1, todesc=desc2, numlines=False)

    ret += '<div class="answers"><br/>Shared answers:<br/> %s</div>' % " ".join(shared)

    ret += diff_html

    ret += html_footer

    return ret, pct

def get_list_band_html(index_list, gridrel, lowpct, highpct):
    matches = [ (pct, L) for pct, L, Ltxt, b1, b2 in index_list.values() if pct >= lowpct and pct < highpct ]

    r = "\n<h3>%d puzzles match %d-%d%% of a%s %s grid</h3>" % (len(matches), lowpct, highpct, (gridrel[0] in "aeiou") and "n" or "", gridrel)
    for b1, L in sorted(matches, reverse=True):
        r += '\n<li>' + L + '</li>'

    r += '<hr/>'
    return r

def get_index_html(pubid, pubxd, index_list, gridrel):
    out = html_header.format(title="%s crossword similarity" % pubid)

    out += "The left side is always the earlier published puzzle. <b>Bold</b> highlights that the authors are different for the two puzzles.<br/>"

    out += "<br/>%s : %s crosswords from %s" % (pubid, pubxd.get_header("num_xd"), pubxd.get_header("years"))

    out += '<h2>%s puzzles that are similar to %s puzzles</h2>' % (pubid, gridrel)

    if gridrel == "earlier":
        out += '<a href="from.html">show similarities to later puzzles instead</a>'
    else:
        out += '<a href="index.html">show similarities to earlier puzzles instead</a>'

    out += '<ul>'
    out += get_list_band_html(index_list, gridrel, 75, 100)
    out += get_list_band_html(index_list, gridrel, 50, 75)
    out += get_list_band_html(index_list, gridrel, 25, 50)
    out += '</ul>'


    out += html_footer

    return out

if __name__ == "__main__":

    OUTPUT_DIR = sys.argv[1]
    pubid = OUTPUT_DIR.split("/")[-1]

    if len(sys.argv) > 2:
        similar_txts = sys.argv[2:]
    else:
        similar_txts = [ "crosswords/%s/similar.txt" % pubid ]

    os.makedirs(OUTPUT_DIR)

    pubxd = xdfile.xdfile(file("crosswords/%s/meta.txt" % pubid).read()) # just to parse some cached metadata

    left_index_list =  { } # [(olderfn, newerfn)] -> (pct, index_line)
    right_index_list =  { } # [(olderfn, newerfn)] -> (pct, index_line)

    for inputfn in similar_txts:
      for line in file(inputfn).read().splitlines():
        if not line: continue
        parts = line.strip().split(' ', 2)
        if len(parts) == 2:
            fn1, fn2 = parts
        elif len(parts) == 3:
            fn1, fn2, rest = parts
        else:
            print "ERROR in %s: %s" % (inputfn, line)
            continue

        if pubid not in fn1 and pubid not in fn2:
            continue

        try:
            abbr, d1 = downloadraw.parse_date_from_filename(fn1)
            abbr, d2 = downloadraw.parse_date_from_filename(fn2)
            if d2 < d1:
                fn1, fn2 = fn2, fn1 # always older on left
        except:
            pass # no date in filename

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

        print fn1, fn2

        b1 = xdfile.get_base_filename(fn1)
        b2 = xdfile.get_base_filename(fn2)
        outfn = "%s-%s.html" % (b1, b2)

        index_line = '%d%% <a href="%s">%s - %s</a>' % (pct, outfn, b1, b2)

        index_txt = " ".join([ fn1, fn2, str(int(pct))])

        aut1 = (xd1.get_header("Author") or xd1.get_header("Creator") or "")
        aut2 = (xd2.get_header("Author") or xd2.get_header("Creator") or "")
        if aut1.startswith("By "):
            aut1 = aut1[3:]
        if aut2.startswith("By "):
            aut2 = aut2[3:]

        if aut1 != aut2:
            index_line += ' <b>%s | %s</b>' % (aut1, aut2)
            index_txt += " *"
        else:
            index_line += ' %s' % aut1

        added = False
        if pubid in fn2:
            right_index_list[(fn1, fn2)] = (pct, index_line, index_txt, b1, b2)
            added = True

        if pubid in fn1:
            left_index_list[(fn1, fn2)] = (pct, index_line, index_txt, b1, b2)
            added = True
    
        if added:
            file(OUTPUT_DIR + "/" + outfn, 'w').write(ret.encode("utf-8"))



    file("%s/index.html" % OUTPUT_DIR, 'w').write(get_index_html(pubid, pubxd, right_index_list, "earlier"))
    file("%s/from.html" % OUTPUT_DIR, 'w').write(get_index_html(pubid, pubxd, left_index_list, "later"))
    with file("%s/index.txt" % OUTPUT_DIR, 'w') as f:
        for pct, L, Ltxt, b1, b2 in sorted(left_index_list.values(), reverse=True):
            if pct < 25:
                break
            f.write(Ltxt + '\n')
        f.write('\n')
        for pct, L, Ltxt, b1, b2 in sorted(right_index_list.values(), reverse=True):
            if pct < 25:
                break
            f.write(Ltxt + '\n')



