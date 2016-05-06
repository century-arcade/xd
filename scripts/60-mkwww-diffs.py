#!/usr/bin/env python3

# Usage:
#   $0 -o <www_dir> <similarities.xsv>

import os.path
import difflib

from xdfile.utils import get_args, log, get_log, open_output, find_files, parse_tsv, progress
import xdfile

style_css = """
        table.diff {font-family:Courier; border:medium;}
        .diff_header {  background-color:#e0e0e0; color: #e0e0e0 }
        td.diff_header { text-align:right; width: 0px}
        table.diff td { padding-left: 5px }
        .diff_next {display: none; }
        .diff_add {background-color:#aaffaa}
        .diff_chg {background-color:#ffff77}
        .diff_sub {background-color:#ffaaaa}

span.visible { color: blue; }
.fixed {font-family:Courier; }
div, textarea { margin-top: 1em; }

body { 
    padding: 10px;
    background-color: #ffeeee 
}
body div { padding: 10px; background-color: #ffeeee }
"""

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


def same_answers(a, b):
    ans1 = set(sol for pos, clue, sol in a.clues)
    ans2 = set(sol for pos, clue, sol in b.clues)
    return ans1 & ans2


def get_url(xd):
    raise Exception("notimpl")


def gendiff(xd1, xd2, pct):
    try:
        desc1 = '<a href="%s">%s</a>' % (get_url(xd1), xd1.filename)
    except:
        desc1 = '<a href="">%s</a>' % xd1.filename

    try:
        desc2 = '<a href="%s">%s</a>' % (get_url(xd2), xd2.filename)
    except:
        desc2 = '<a href="">%s</a>' % xd2.filename

    shared = same_answers(xd1, xd2)

    ret = html_header.format(title="%s%% similar grids, %d/%d shared answers" % (pct,
                                                                                 len(shared),
                                                                                 len(xd2.clues)))

    s1 = xd1.to_unicode()
    s2 = xd2.to_unicode()

    hd = difflib.HtmlDiff(linejunk=lambda x: False)
    diff_html = hd.make_table(s1.splitlines(), s2.splitlines(), fromdesc=desc1, todesc=desc2, numlines=False)

    ret += '<div class="answers"><br/>Shared answers:<br/> %s</div>' % " ".join(shared)

    ret += diff_html

    if int(pct) < 50:
        # it might be easier to see partial similarities this way, due to limitations of HtmlDiff
        xdt1 = xd1.transpose()
        xdt2 = xd2.transpose()

        diff_html += "<hr><p>With both puzzles transposed (may be easier to see vertical similarities)</p>"
        diff_html += hd.make_table(xdt1.to_unicode().splitlines(), xdt2.to_unicode().splitlines(), fromdesc=desc1 + " (transposed)", todesc=desc2 + " (transposed)", numlines=False)

    ret += html_footer

    return ret


def get_list_band_html(index_list, lowpct, highpct):
    matches = [(b2, L) for pct, L, b1, b2 in list(index_list.values()) if pct >= lowpct and pct < highpct]

    r = "\n<h3>%d puzzles match %d-%d%% of another grid</h3>" % (len(matches), lowpct, highpct)
    for b1, L in sorted(matches):
        r += '\n<li>' + L + '</li>'

    r += '<hr/>'
    return r


def get_index_html(index_list, subset=""):
    out = html_header.format(title="%s crossword similarity" % subset)

    out += "The left side is always the earlier published puzzle. <b>Bold</b> highlights that the authors are different for the two puzzles.<br/>"

    out += '<h2>%s grids that are similar to other puzzles</h2>' % subset

    out += '<ul>'
    out += get_list_band_html(index_list, 75, 100)
    out += get_list_band_html(index_list, 50, 75)
    out += get_list_band_html(index_list, 25, 50)
    out += '</ul>'

    out += html_footer

    return out


def main():
    parser = get_parser(desc="make www pages from similarity query results")
    parser.add_option('-n', '--name', dest="subset", help="user-facing name of the given subset")
    args = get_args(parser=parser)

    outf = open_output()

    right_index_list = {}  # [(olderfn, newerfn)] -> (pct, index_line, b1, b2)

    # find all tsv/xsv/csv files
    for xsvfn, xsv in find_files(*args.inputs, ext='sv'):
        for row in parse_tsv_data(xsv, "Similarity"):
            fn1, fn2 = row.needle, row.match

            progress("%s - %s" % (fn1, fn2))

            if fn1.endswith(".transposed"):
                fn1, _ = os.path.splitext(fn1)
                flTranspose = True
            else:
                flTranspose = False

            xd1 = xdfile.xdfile(file(fn1).read(), fn1)
            xd2 = xdfile.xdfile(file(fn2).read(), fn2)

            if flTranspose:
                xd1 = xd1.transpose()

            # always earlier on left
            if xd2.date() < xd1.date():
                xd1, xd2 = xd2, xd1

            pct = int(row.percent)

            if pct < 20:
                log("%s%%, skipping" % pct)
                continue

            ret = gendiff(xd1, xd2, pct)

            b1 = xd1.xdid()
            b2 = xd2.xdid()

            outfn = "%s-%s.html" % (b1, b2)

            if flTranspose:
                index_line = '%d%% <a href="%s">%s (transposed) - %s</a>' % (pct, outfn, b1, b2)
            else:
                index_line = '%d%% <a href="%s">%s - %s</a>' % (pct, outfn, b1, b2)

            aut1 = xd1.get_header("Author")
            aut2 = xd2.get_header("Author")

            if aut1 != aut2:
                index_line += ' <b>%s | %s</b>' % (aut1, aut2)
            else:
                index_line += ' %s' % aut1

            right_index_list[(fn1, fn2)] = (pct, index_line, b1, b2)

            outf.write_file(outfn, ret)

    outf.write_file("style.css", style_css)
    outf.write_file("index.html", get_index_html(right_index_list, args.subset))
    outf.write_file("mkwww.log", get_log())

if __name__ == "__main__":
    main()
