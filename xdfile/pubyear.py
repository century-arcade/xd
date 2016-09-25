from collections import defaultdict

from xdfile.html import mkhref, mktag, tr_empty, td_with_class
from xdfile import utils, metadatabase as metadb
from xdfile.utils import space_with_nbsp
from datetime import date


def mkcell(text, href="", title=""):
    r = '<div>'
    r += mkhref(text, href, title=title)
    r += '</div>'
    return r


def split_year(y):
    lsy = str(y)[2:]
    if y[3] != '0':
        msy = '&nbsp;'  # Changed to &nbsp;
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


def year_widget(dow_dict, total, fill_class=None):
    # Generate SVG based widget for day of week dispersion for year
    fill_class = fill_class or 'white'
    b = []
    b.append('<svg class="year_widget" width="30" height="30">')
    b.append('<g transform="translate(0,0)"><rect class="%s" width="30" height="30"></rect></g>' % fill_class)
    for i, v in enumerate(utils.WEEKDAYS):
        _class = dow_dict[v]['class'] if 'class' in dow_dict[v].keys() else ''
        _length = str(dow_dict[v]['count']) if 'count' in dow_dict[v].keys() else '0'
        _length = _length if  int(_length) < 26 else '30' # for all 52/2 have full filled row
        b.append('<g transform="translate(0,' + str(i*3+i) + ')"><rect class="' + _class + '" width="' + _length + '" height="3"></rect></g>')
    b.append('</svg>')
    return(' '.join(b))

def decade_widget(total, fill_class=None):
    # Generate SVG based widget for decade showing total
    fill_class = fill_class or 'green'
    b = []
    b.append('<svg class="year_widget" width="30" height="30">')
    b.append('<g transform="translate(0,0)"><rect class="%s" width="30" height="30"></rect></g>' % fill_class)
    b.append('<text x="25" y="18">' + str(total) + '</text>')
    b.append('</svg>')
    return(' '.join(b))


g_all_pubyears = None
def pubyear_html(pubyears=[], skip_decades=None):
    """
    skip_decades, default  { 'start': 1910, 'end': 1970 }
    """
    global g_all_pubyears
    if not g_all_pubyears:
        g_all_pubyears = utils.parse_tsv_data(open("pub/pubyears.tsv").read(), "pubyear")


    # Read similars to make background of widgets
    similar_d = defaultdict(dict)
    for xdid, v in utils.parse_tsv('gxd/similar.tsv', "similar").items():
        xd_split = utils.split_xdid(xdid)
        if xd_split:
            pubid, year, mon, day = xd_split
            if year in similar_d[pubid]:
                similar_d[pubid][year].append(int(v.similar_grid_pct))
            else:
                similar_d[pubid][year] = [ int(v.similar_grid_pct) ] 

    b = [] # Body
    
    # Making collapsed decades depends on args
    skip_decades = skip_decades if skip_decades else { 'start': 1910, 'end': 1970 } 
    allyears = []
    for i in range(skip_decades['start']//10, skip_decades['end']//10 + 1):
        allyears.append("%s0s" % i)
    allyears.extend([ str(y) for y in range(skip_decades['end'] + 10, date.today().year + 1) ])
    
    pubs = defaultdict(dict)
    # generate widget for each year
    for dowl in g_all_pubyears:
        dow = {}
        pubid, year, total = dowl[:3]
        hint = ''
        for d, v in zip(utils.WEEKDAYS, dowl[3:]):
            dow[d] = { 'count': int(v)//2, 'class':'' }
            dow[d]['class'] = 'red' if d == 'Sun' else 'ord'
            hint += '%s - %s\n' % (d, v)
        hint += 'Total: %s\n' % (total)
        # Define fill class based on average similarity
        fill_class = None # default fill class for widget
        if year in similar_d[pubid]:
            s_avg = sum(similar_d[pubid][year]) / len(similar_d[pubid][year]) 
            hint += 'Avg similarity: %.2f%%' % (s_avg)
            # Example if average > 10 %
            fill_class = 'similar10' if s_avg >= 10 else None

        # Fill pubs with defferent blocks will be used below
        pubs[pubid][year] = {
                'dow_data': dow,
                'widget': year_widget(dow, total, fill_class),
                'hint': hint,
                'total': int(total),
                }
    # Process for all decades
    for dec_year in [x for x in allyears if 's' in x]:
        for pubid in pubs:
            year_key = dec_year[:-2] # Remove last year and "s" from the end
            total = 0
            for yf in [x for x in pubs[pubid] if year_key in x]:
                total += pubs[pubid][yf]['total']
            hint = 'Total: %s' % (total)
            if total > 0:
                pubs[pubid][dec_year] = {
                    'widget': decade_widget(total),
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

    # Process each pubid sorted by earliest year
    for pubid in sorted(pubs, key=lambda x:min(pubs[x])):
        pub = metadb.xd_publications().get(pubid)
        pubname = pub.PublicationName if pub else ''
        # Pub id to first column
        b.append(mktag('tr'))
        b.append(mktag('td','pub'))
        b.append(mkcell(space_with_nbsp(pubname or pubid), "/pub/" + pubid, ))
        b.append(mktag('/td'))

        # Process each year not collapsed into decade
        for yi in allyears:
            if yi in pubs[pubid] and pubs[pubid][yi]['total'] > 0:
                b.append(mktag('td','this'))
                # Put link directly to year or to decade
                href = "/pub/%s%s" % (pubid, yi) if 's' not in yi else "/pub/%s/index.html#%s" % (pubid, yi[:-1])
                b.append(mkcell(pubs[pubid][yi]['widget'], href=href, 
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
