
import cgi
from collections import Counter

from xdfile.html import th, td, mkhref
from xdfile.metadatabase import publications, get_publication
import xdfile.utils
import xdfile

def mkcell(text, href="", title=""):
    r = '<div>'
    r += mkhref(text, href, title=title)
    r += '</div>'
    return r


def split_year(y):
    lsy = str(y)[2:]
    if y[3] != '0':
        msy = ' '  # unicode M space
    else:
        msy = str(y)[:2]

    return "%s<br/>%s" % (msy, lsy)

def pubyear_html():
    pubyears = xdfile.utils.parse_tsv("pub/pubyears.tsv", "pubyear")

    pubs = {}
    for pubid, year, num in pubyears:
        if pubid not in pubs:
            pubs[pubid] = Counter()
        try:
            pubs[pubid][int(year)] += int(num)
        except:
            pass

    allyears = "1910s 1920s 1930s".split() + [ str(y) for y in range(1940, 2017) ]

    ret = '<table class="pubyears">'
    yhdr = [ '' ] + [ split_year(y) for y in allyears ]
    yhdr.append("all")

    ret += th(*yhdr)

    def key_pubyears(x):
        pubid, y = x
        firstyear = xdfile.year_from_date(get_publication(pubid).row.FirstIssueDate)
        return firstyear or min(y.keys())

    xdtotal = 0
    for pubid, years in sorted(pubs.items(), key=key_pubyears):
        pubtotal = sum(years.values())
        if pubtotal < 10:
            continue
        xdtotal += pubtotal
        
        pub = publications().get(pubid)
        if pub:
            pubname = pub.row.PublicationName
            start, end = pub.row.FirstIssueDate, pub.row.LastIssueDate
        else:
            pubname, start, end = "", "", ""

        ret += '<tr>'
        ret += '<td class="pub">%s</td>' % (mkcell(pubname or pubid, "/" + pubid, ))
        for y in allyears:
            classes = []

            if y[-1] == 's':
                n = sum(v for k, v in years.items() if str(k)[:-1] == y[:-2])
                y = y[:-1]
                classes.append("decade")
            else:
                n = years[int(y)]

            y = int(y)
            if n >= 365:
                classes.append("daily")
            elif n >= 200:
                classes.append("semidaily")
            elif n >= 50:
                classes.append("weekly")
            elif n >= 12:
                classes.append("monthly")
            elif n > 0:
                pass
            elif start:
                if y < xdfile.year_from_date(start):
                    classes.append("block")
                if end and y > xdfile.year_from_date(end):
                    classes.append("block")
            else:
                classes.append("block")

            ret += '<td class="%s">%s</td>' % (" ".join(classes), mkcell(n or "", href="%s/%s" % (pubid, y)))
        ret += '<td>%s</td>' % pubtotal
        ret += '</tr>'

    yhdr = yhdr[:-1]
    yhdr.append(xdtotal)
    ret += th(*yhdr)
    ret += '</table>'
    return ret

