import re
import cgi
import time
from collections import Counter
import xdfile
from calendar import HTMLCalendar
from datetime import date
from xdfile import utils

from queries.similarity import grid_similarity


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
            if cdate in self.grids:
                # Supply class or link via dict
                if 'class' in self.grids[cdate]:
                    cssclass += ' ' + self.grids[cdate]['class']
                if 'link' in self.grids[cdate]:
                    htitle = self.grids[cdate]['title'] if self.grids[cdate]['title'] else ''
                    body = mkhref(str(day), self.grids[cdate]['link'], htitle) 
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

navbar_items = [
      ('Home','/'),
      ('About', '/about'),
      ('Data', '/data'),
      ('Most Popular', [
              ('Words','/words'),
              ('Clues','/clues'),
      ]),
]

#todo: output navbar_items like in https://codepen.io/philhoyt/pen/ujHzd
def navbar_helper(item, current_url):
    r = '<ul>'
    for name, dest in item:
        if dest == current_url:
            r += '<li class="current-menu-item">'
        else:
            r += '<li>'
        if isinstance(dest, list):
            r += navbar_helper(dest, current_url)
        else:
            r += '<a href="%s">%s</a>' % (dest, name)
        r += '</li>'
    r += '</ul>'
    return r

def html_header(current_url=None, title='xd page'):
    npuzzles = len(xdfile.g_corpus)

    h = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html>

<head>
    <meta http-equiv="Content-Type"
          content="text/html; charset=ISO-8859-1" />
    <title>{title}</title>
    <LINK href="/style.css" rel="stylesheet" type="text/css">
  </HEAD>
</head>

<body>
""".format(title=title)


    h += '<nav id="primary_nav_wrap">'
    h += navbar_helper(navbar_items, current_url)
    h += '</nav>'

    h += '<hr style="clear:both;"/>'
    h += '<h2>{title}</h2>'.format(title=title)
    if npuzzles:
        h += ' from a corpus of {npuzzles} puzzles'.format(npuzzles=npuzzles)

    return h



def html_footer():
    dt = time.strftime('%F')
    return """
  <hr style="clear:both;"/>
<small><i>Generated on {date}</i>
<br>
a <a href="mailto:xd@saul.pw">saul.pw</a> project
</small>
</body>
</html>
""".format(date=dt)


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


def html_select_options(options, strmaker=str, force_top="", add_total=True):
    if not options:
        return strmaker(force_top)

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

    return html_select_options_freq(pairs, strmaker=strmaker, force_top=force_top, add_total=add_total)


def html_select_options_freq(pairs, strmaker=str, force_top="", add_total=True):
    def strnum(s, n):
        assert n > 0
        if n == 1:
            return s
        else:
            return "%s [x%s]" % (s, n)

    freq_sorted = []

    if force_top:
        # TODO: get actual nuses if already in pairs
        freq_sorted.append((1, strmaker(force_top)))

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
    if add_total:
        r += '<span class="num"> %s</span>' % len(freq_sorted)
    return r


def table_row(row, keys, rowclass="row", tag="td", tag_params=None, inner_only=False):
    # row - list or dict
    # keys - assign as class for each itterable from row 
    # rowclass - class(es) for tr (row)
    # tag - tag to be used for cells in row - default: td
    # tag_params - 
    if isinstance(row, dict):
        row = [row[k] for k in keys]

    out = ''
    if not inner_only:
        out += mktag('tr', rowclass, tag_params=tag_params)

    for k, v in zip(keys, row):
        try:
            v = str(v or "")
        except UnicodeDecodeError:
            v = "???"

        if inner_only:
            out += mktag(tag, k.strip(), tag_params=tag_params)
        else:
            out += mktag(tag, k.strip())
        out += v
        out += mktag('/' + tag)  # end cell

    if not inner_only:
        out += mktag('/tr') + '\n'  # end row
    return out


def html_table(rows, colnames, rowclass="row", tableclass="", inner_only=False):
    """
    Generates html table with class defined
    each row can be a list - then rowclass applied
    or dict - {row:row, class:rowclass, param:rowparam}
    """
    out = ''
    if not inner_only:
        out += mktag('table', tableclass)
        out += table_row(colnames, colnames, tag='th')

    for r in rows:
        r_text = r['row'] if isinstance(r, dict) else r
        r_class = r['class'] if isinstance(r, dict) and 'class' in r.keys() else rowclass
        r_param = r['tag_params'] if isinstance(r, dict) and 'tag_params' in r.keys() else None
        out += table_row(r_text, colnames, rowclass=r_class, tag_params=r_param)

    if not inner_only:
        out += mktag('/table')  # end table
    return out


def tsv_to_table(rows):
    return html_table(rows, rows[0]._fields)

def markup_to_html(s):
    s = re.sub(r'{/(.*?)/}', r'<i>\1</i>', s)
    s = re.sub(r'{\*(.*?)\*}', r'<b>\1</b>', s)
    s = re.sub(r'{-(.*?)-}', r'<strike>\1</strike>', s)
    s = re.sub(r'{_(.*?)_}', r'<u>\1</u>', s)
    return s


def headers_to_html(xd):
    # headers
    r = '<div class="xdheaders"><ul class="xdheaders">'
    for k in "Title Author Editor Copyright".split():
        v = xd.get_header(k)
        if v:
            r += '<li class="%s">%s: <b>%s</b></li>' % (k, k, v)
        else:
            r += '<li></li>'
    r += '</ul></div>'
    return r


def grid_to_html(xd, compare_with=None):
    "htmlify this puzzle's grid"

    grid_html = '<div class="xdgrid">'
    for r, row in enumerate(xd.grid):
        grid_html += '<div class="xdrow">'
        for c, cell in enumerate(row):
            classes = [ "xdcell" ]

            if cell == xdfile.BLOCK_CHAR:
                classes.append("block")

            if compare_with:
                if cell == compare_with.cell(r, c):
                    classes.append("match")
                else:
                    classes.append("diff")

            grid_html += '<div class="%s">' % " ".join(classes)
            grid_html += cell  # TODO: expand rebus
            #  include other mutations that would still be valid
            grid_html += '</div>' # xdcell
        grid_html += '</div>' #  xdrow
    grid_html += '</div>' # xdgrid

    return grid_html


def grid_diff_html(xd, compare_with=None):
    if compare_with:
        r = mktag('div', tagclass='fullgrid')
    else:
        r = mktag('div', tagclass='fullgrid main')

    similarity_pct = ''
    if compare_with:
        real_pct = grid_similarity(xd, compare_with)
        if real_pct < 25:
            return ''

        similarity_pct = " (%d%%)" % real_pct

    xdlink = mktag('div', tagclass='xdid', inner=mkhref("%s %s" % (xd.xdid(), similarity_pct), '/pub/' + xd.xdid()))
    if compare_with is not None:
        r += xdlink
    else:
        r += mktag('b', inner=xdlink)
    r += headers_to_html(xd)
    r += grid_to_html(xd, compare_with)

    r += '</div>' # solution
    return r

