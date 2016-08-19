#!/usr/bin/python3

from datetime import date
from xdfile import utils
import xdfile

pys = '''
<svg class="year_widget" width="30" height="30">
  <g transform="translate(0,0)">
    <rect class="%s" width="30" height="30"></rect>
  </g>
%s
</svg>
'''


def rect(x, y, w, h, *classes):
  return '<rect transform="translate({x},{y})" class="{classes}" width="{w}" height="{h}"></rect>'.format(x=x, y=y, w=w, h=h, classes=''.join(classes))


def year_from(dt):
    return int(dt.split('-')[0])

def weekdays_between(dta, dtb):
    return 0


def pubyear_svg(corpus, nsusp, ndup, npub, npriv):
    bgclass = "notexists"
#    if bgclass not in publications.tsv:
#       bgclass = "exists"

    rects = ''

    for i in range(0, 7):
        y = i*3

        # TODO: find first xd of weekday i
        firstxd = corpus[i]
        lastxd = corpus[1-i]

        sz = firstxd.width() * firstxd.height()
        h = 3 if sz > 17*17 else 2

        x = 0
        w = 6

        rects += '''<g id="mon" transform="translate(0,{y})">'''.format(y=y)

        npre = weekdays_between(date(year_from(firstxd.Date), 1, 1), firstxd.Date, i)
        w = npre
        rects += rect(x, y, w, h, 'prexd')
        x += w

        w = nsusp
        rects += rect(x, y, w, h, 'suspxd')
        x += w

        w = ndup
        rects += rect(x, y, w, h, 'dupxd')
        x += w

        w = npriv
        rects += rect(x, y, w, h, 'privxd')
        x += w

        w = npub
        rects += rect(x, y, w, h, 'pubxd')
        x += w

        npost = weekdays_between(lastxd.Date, date(year_from(lastxd.Date), 12, 31), i)
        w = npost
        rects += rect(x, y, w, h, 'postxd')
        rects += '</g>'

    return pys % (bgclass, rects)


def main():
    p = utils.args_parser(desc="annotate puzzle clues with earliest date used in the corpus")
    p.add_argument('-a', '--all', default=False, help='analyze all puzzles, even those already in similar.tsv')
    args = utils.get_args(parser=p)
    outf = utils.open_output()

    prev_similar = utils.parse_tsv('gxd/similar.tsv', "similar")
    pubyears = {}
    for xd in xdfile.corpus():
        pubyear = xd.publication_id() + str(xd.year())
        if pubyear not in pubyears:
            pubyears[pubyear] = []
        pubyears[pubyear].append(xd)

    print('''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
    <meta charset="utf-8">
    <meta name="description" content="">
    <meta name="keywords" content="">
    <meta name="author" content="">
    <title></title>
    <link href="style.css" rel="stylesheet" type="text/css">
    <script src="script.js"></script>
</head>
<body>
%s
</body>
</html>''' % pubyear_svg(pubyears['up2011'], 'up', 2011))


if __name__ == "__main__":
    main()

