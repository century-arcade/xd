
import cgi
from collections import Counter

from xdfile.html import th, td, mkhref, tr_empty, td_with_class
from xdfile import utils, metadatabase as metadb
import xdfile

def mkcell(text, href="", title=""):
    r = '<div>'
    r += mkhref(text, href, title=title)
    r += '</div>'
    return r


def split_year(y):
    lsy = str(y)[2:]
    if y[3] != '0':
        #msy = ' '  # unicode M space
        msy = '&nbsp;' # Changed to &nbsp;
    else:
        msy = str(y)[:2]

    return "%s<br/>%s" % (msy, lsy)

def get_pubheader_classes(*years):
    """
    Assign classes to years header
    """
    classes = []
    for y in years:
        if "&nbsp" in str(y):
            classes.append("ord-year")
        else:
            classes.append("zero-year")    
    return classes
        

g_all_pubyears = None
def pubyear_html(pubyears=[]):
    global g_all_pubyears
    if not g_all_pubyears:
        g_all_pubyears = utils.parse_tsv_data(open("pub/pubyears.tsv").read(), "pubyear")

    pubs = {}
    for pubid, year, num in g_all_pubyears:
        if pubid not in pubs:
            pubs[pubid] = Counter()
        try:
            pubs[pubid][int(year)] += int(num)
        except Exception as e:
            utils.log(str(e))

    allyears = "1910s 1920s 1930s".split() + [ str(y) for y in range(1940, 2017) ]

    ret = '<table class="pubyears">'
    yhdr = [ '&nbsp;' ] + [ split_year(y) for y in allyears ]
    yhdr.append("all")
    ret += td_with_class(*yhdr, classes=get_pubheader_classes(*yhdr),
                        rowclass="pubyearhead",tag="th")
    # Insert empty row
    ret += tr_empty()
    
    def key_pubyears(x):
        pubid, y = x
        try:
            firstyear = xdfile.year_from_date(metadb.xd_publications()[pubid].FirstIssueDate)
        except:
            firstyear = None

        return firstyear or min(y.keys())

    xdtotal = 0
    for pubid, years in sorted(pubs.items(), key=key_pubyears):
        pubtotal = sum(years.values())
        xdtotal += pubtotal
        
        pub = metadb.xd_publications().get(pubid)
        if pub:
            pubname = pub.PublicationName
            start, end = pub.FirstIssueDate, pub.LastIssueDate
        else:
            pubname, start, end = "", "", ""

        ret += '<tr>'
        ret += '<td class="pub">%s</td>' % (mkcell(pubname or pubid, "/pub/" + pubid, ))
        for y in allyears:
            classes = []

            if y[-1] == 's':
                n = sum(v for k, v in years.items() if str(k)[:-1] == y[:-2])
                y = y[:-1]
                classes.append("decade")
            else:
                n = years[int(y)]

            y = int(y)

            if (pubid, y) in pubyears:
                classes.append('this')

            if n >= 365:
                classes.append('daily')
            elif n >= 200:
                classes.append('semidaily')
            elif n >= 50:
                classes.append('weekly')
            elif n >= 12:
                classes.append('monthly')
            elif n > 0:
                pass
            elif start:
                if y < xdfile.year_from_date(start):
                    classes.append("block")
                if end and y > xdfile.year_from_date(end):
                    classes.append("block")
            else:
                classes.append("block")

            ret += '<td class="%s">%s</td>' % (" ".join(classes), mkcell(n or "", href="/pub/%s%s" % (pubid, y)))
        ret += '<td>%s</td>' % pubtotal
        ret += '</tr>'

    yhdr = yhdr[:-1]
    yhdr.append(xdtotal)
    # Insert empty row
    ret += tr_empty()
    ret += td_with_class(*yhdr, classes=get_pubheader_classes(*yhdr),
                         rowclass="pubyearhead",tag="th")
    ret += '</table>'
    return ret

