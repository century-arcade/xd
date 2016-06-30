import cgi
import time
from collections import Counter
import xdfile
from calendar import HTMLCalendar
from datetime import date


def year_widget(dow_dict, total, fill_class='white'):
    # Generate SVG based widget for day of week dispersion for year
    b = []
    b.append('<svg class="year_widget" width="30" height="30">')
    b.append('<g transform="translate(0,0)"><rect class="%s" width="30" height="30"></rect></g>' % fill_class)
    weekdays = [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun' ]
    for i, v in enumerate(weekdays):
        _class = dow_dict[v]['class'] if 'class' in dow_dict[v].keys() else ''
        _length = str(dow_dict[v]['count']) if 'count' in dow_dict[v].keys() else '0'
        b.append('<g transform="translate(0,' + str(i*3+i) + ')"><rect class="' + _class + '" width="' + _length + '" height="3"></rect></g>')
    b.append('</svg>')
    return(' '.join(b))

def decade_widget(total, fill_class='green'):
    # Generate SVG based widget for decade showing total
    b = []
    b.append('<svg class="year_widget" width="30" height="30">')
    b.append('<g transform="translate(0,0)"><rect class="%s" width="30" height="30"></rect></g>' % fill_class)
    b.append('<text x="25" y="18">' + str(total) + '</text>')
    b.append('</svg>')
    return(' '.join(b))

class GridCalendar(HTMLCalendar):
    """
    Generate HTML calendar with links on certain pages with styles
    """
    def __init__(self, grids):
        super(GridCalendar, self).__init__()
        self.grids = grids

    def formatday(self, day, weekday):
        if day != 0:
            cssclass = self.cssclasses[weekday]
            cdate = str(date(self.year, self.month, day))
            # If links in supplied link and not empty
            if cdate in self.grids.keys():
                # Supply class or link via dict
                if self.grids[cdate]['class']:
                    cssclass += ' ' + self.grids[cdate]['class']
                if 'link' in self.grids[cdate].keys():
                    body = mkhref(str(day), self.grids[cdate]['link']) 
                else:
                    body = str(day)
                return self.day_cell(cssclass, '%s' % (body))
            return self.day_cell(cssclass, day)
        return self.day_cell('noday', '&nbsp;')

    def formatmonth(self, year, month, withyear=False):
        self.year, self.month = year, month
        return super(GridCalendar, self).formatmonth(year, month, withyear)
    
    def day_cell(self, cssclass, body):
        text = []
        text.append(mktag('td', cssclass))
        text.append(str(body))
        text.append(mktag('/td'))
        return ''.join(text)

    def formatyear(self, theyear, width=3, vertical=False):
        """
        Return a formatted year as a table of tables.
        """
        # Constants for months referenced later
        January = 1

        v = []
        a = v.append
        width = max(width, 1)
        a('<table border="0" cellpadding="0" cellspacing="0" class="year">')
        a('\n')
        
        # Align header horizontally
        if not vertical:
            a('<tr><th colspan="%d" class="year" id="%s">%s</th></tr>' % (width, theyear, theyear))
        for i in range(January, January+12, width):
            # months in this row
            months = range(i, min(i+width, 13))
            a('<tr>')
            if vertical:
                a('<td class="year-v" id="%s">%s</td>' % (theyear, '<br>'.join(str(theyear))))
            for m in months:
                a('<td>')
                a(self.formatmonth(theyear, m, withyear=False))
                a('</td>')
            a('</tr>')
        a('</table>')
        return ''.join(v)

def html_header(**kwargs):
    kwargs['date'] = time.strftime('%F')
    npuzzles = len(xdfile.g_corpus)
    kwargs['npuzzles'] = npuzzles

    h = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html>

<head>
    <meta http-equiv="Content-Type"
          content="text/html; charset=ISO-8859-1" />
    <title>{title}</title>
    <!-- <LINK href="style.css" rel="stylesheet" type="text/css"> -->
    <LINK href="/pub/style.css" rel="stylesheet" type="text/css">
  </HEAD>
</head>

<body>
<i>Generated on {date}""".format(**kwargs)
    if npuzzles:
        h += ' from a corpus of {npuzzles} puzzles'.format(**kwargs)
    h += '.</i><h1>{title}</h1>'.format(**kwargs)
    return h

html_footer = """
  <hr style="clear:both;"/>
  <!--a href="http://saul.pw"><small>saul.pw</small></a-->
  <a href="mailto:xd@saul.pw"><small>xd@saul.pw</small></a>

</body>
</html>
"""


def redirect_page(url):
    return """<html><head><meta http-equiv="refresh" content="0; URL='{url}'" />
<script>window.location.replace("{url}");</script></head><body>Redirecting to <a href="{url}">{url}</a></body></html>""".format(url=url)


def mktag(tagname, tagclass='', inner=None, tag_params=None):
    """ generates tag:
        <tagname * > or if tag_params dict passed <tagname * >inner</tagname>
        * tagclass or if tag_params dict passed will be overloaded by tag_params['class'] 
        <tagname param1="value1" param2="value2" ...>
    """
    ret = ''
    if tag_params:
        _params = []
        for p, v in tag_params.items():
            _params.append('%s="%s"' % (p, v))
    else:
        _params = [ 'class="%s"' % tagclass ] 
    
    ret += '<%s %s>' % (tagname, " ".join(_params))

    if inner is not None:
        ret += inner
        ret += mktag('/' + tagname)

    return ret


def mkhref(text, link, title=""):
    if title:
        return '<a href="%s" title="%s">%s</a>' % (link, title, text)
    else:
        return '<a href="%s">%s</a>' % (link, text)


def th(*cols, rowclass=''):
    return td(*cols, rowclass=rowclass, tag='th')


def td(*cols, rowclass='', href='', tag='td'):
    r = ''
    r += mktag('tr', rowclass)
    for x in cols:
        r += mktag(tag)
        if href:
            r += mkhref(href, str(x))
        else:
            r += str(x)
        r += mktag('/' + tag)
    r += mktag('/tr')
    return r


def td_with_class(*cols, classes=[], rowclass='', href='', tag='td'):
    """
    Print td with class defined per element provided by list
    """
    r = ''
    r += mktag('tr', rowclass)
    for i, x in enumerate(cols):
        try:
            class_ = classes[i]
        except IndexError:
            class_ = ''
        r += mktag(tag, class_)
        if href:
            r += mkhref(href, str(x))
        else:
            r += str(x)
        r += mktag('/' + tag)
    r += mktag('tr')
    return r


def tr_empty(class_="emptytd"):
    """
    Generates empty table row with class=emptytd by default
    """
    return '<tr><td class="' + class_ + '">&nbsp;</td></tr>'

# list of options, possibly duplicate.  presents and groups by strmaker(option)


def html_select_options(options, strmaker=str, force_top=""):
    def strnum(s, n):
        assert n > 0
        if n == 1:
            return s
        else:
            return "%s [x%s]" % (s, n)

    if not options:
        return strmaker(force_top)

    freq_sorted = []
    if force_top:
        freq_sorted.append((1, strmaker(force_top)))

    if isinstance(options, Counter):
        pairs = options.items()
    else:
        groups = {}
        for opt in options:
            s = strmaker(opt)
            if not s in groups:
                groups[s] = [opt]
            else:
                groups[s].append(opt)

        pairs = [(k, len(v)) for k, v in groups.items()]

    freq_sorted.extend(sorted([(v, k or "(misc)") for k, v in pairs], reverse=True))

    if not freq_sorted:
        return ""
    elif len(freq_sorted) == 1:
        n, k = freq_sorted[0]
        return strnum(k, n)

    r = mktag('div', 'options')
    r += mktag('select')

    for n, k in freq_sorted:
        r += '<option>%s</option>' % strnum(k, n)

    r += mktag('/select')
    r += mktag('/div')
    r += '<div class="num"> %s</div>' % len(freq_sorted)
    return r


def table_row(row, keys, rowclass="row", tag="td", tag_params=None):
    if isinstance(row, dict):
        row = [row[k] for k in keys]

    out = mktag('tr', rowclass, tag_params=tag_params)
    for k, v in zip(keys, row):
        try:
            v = str(v or "")
        except UnicodeDecodeError:
            v = "???"

        out += mktag(tag, k.strip())
        out += v
        out += mktag('/' + tag)  # end cell
    out += mktag('/tr') + '\n'  # end row
    return out


def html_table(rows, colnames, rowclass="row", tableclass=""):
    """
    Generates html table with class defined
    each row can be a list - then rowclass applied
    or dict - {row:row, class:rowclass, param:rowparam}
    """
    out = mktag('table', tableclass)
    out += table_row(colnames, colnames, tag='th')

    for r in rows:
        r_text = r['row'] if isinstance(r, dict) else r
        r_class = r['class'] if isinstance(r, dict) and 'class' in r.keys() else rowclass
        r_param = r['tag_params'] if isinstance(r, dict) and 'tag_params' in r.keys() else None
        out += table_row(r_text, colnames, rowclass=r_class, tag_params=r_param)

    out += mktag('/table')  # end table
    return out


def tsv_to_table(rows):
    return html_table(rows, rows[0]._fields)
