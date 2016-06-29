
import cgi
from collections import Counter, defaultdict

from xdfile.html import th, td, mkhref, mktag, tr_empty, td_with_class, year_widget
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
    """
    for pubid, year, num, mon, tue, wed, thu, fri, sat, sun in g_all_pubyears:
        if pubid not in pubs:
            pubs[pubid] = Counter()
        try:
            pubs[pubid][int(year)] += int(num)
        except Exception as e:
            utils.log(str(e))
    """
    weekdays = [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun' ]
    dowl = []
    b = [] # Body
    
    # For header
    allyears = "1910s 1920s 1930s".split() + [ str(y) for y in range(1940, 2017) ]
    
    pubs = defaultdict(dict)
    # generate widget for each year
    for dowl in g_all_pubyears:
        dow = {}
        pubid, year, total = dowl[:3]
        hint = ''
        for i, d in enumerate(dowl[3:]):
            dow[weekdays[i]] = { 'count': int(d)/2, 'class':'' }
            dow[weekdays[i]]['class'] = 'red' if i == 6 else 'ord'
            hint += '%s - %s\n' % (weekdays[i], d)
        hint += 'Total: %s' % (total)
        pubs[pubid][year] = {
                'widget': year_widget(dow, total),
                'hint': hint,
                'total': int(total),
                }
   
    # main table
    b.append('<table class="pubyears">')
    yhdr = [ '&nbsp;' ] + [ split_year(y) for y in allyears ]
    yhdr.append("all")
    b.append(td_with_class(*yhdr, classes=get_pubheader_classes(*yhdr),
            rowclass="pubyearhead",tag="th"))
    b.append(tr_empty()) 
    
    for pubid in sorted(pubs.keys()):
        pub = metadb.xd_publications().get(pubid)
        if pub:
            pubname = pub.PublicationName
        else:
            pubname = ''
        
        # Pub id to first column 
        b.append(mktag('tr'))
        b.append(mktag('td','pub'))
        b.append(mkcell(pubname or pubid, "/pub/" + pubid, ))
        b.append(mktag('/td'))
        
        for yi in allyears:
            if yi in pubs[pubid].keys():
                b.append(mktag('td','this'))
                b.append(mkcell(pubs[pubid][yi]['widget'], href="/pub/%s%s" % (pubid, yi), 
                        title=pubs[pubid][yi]['hint']))
                b.append(mktag('/td'))
            else:
                b.append(mktag('td', 'block'))
                b.append('&nbsp;')
                b.append(mktag('/td'))
                
        b.append(mktag('td'))
        b.append(str(sum([ pubs[pubid][x]['total'] for x in pubs[pubid].keys() ])))
        b.append(mktag('/td'))
        b.append(mktag('/tr'))
   
    b.append(mktag('/table'))
    return (" ".join(b))
