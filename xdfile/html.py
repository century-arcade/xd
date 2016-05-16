import cgi
from collections import Counter


html_header = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html>

<head>
    <meta http-equiv="Content-Type"
          content="text/html; charset=ISO-8859-1" />
    <title>{title}</title>
    <LINK href="style.css" rel="stylesheet" type="text/css">
    <LINK href="/style.css" rel="stylesheet" type="text/css">
  </HEAD>
</head>

<body>
<h1>{title}</h1>
"""

html_footer = """
  <hr style="clear:both;"/>
  <!--a href="http://saul.pw"><small>saul.pw</small></a-->
  <a href="mailto:xd@saul.pw"><small>xd@saul.pw</small></a>

</body>
</html>
"""

html_redirect = """<html><head><meta http-equiv="refresh" content="0; URL='{url}'" />
<script>window.location.replace("{url}");</script></head><body>Redirecting to <a href="{url}">{url}</a></body></html>"""


def mkhref(text, link, title=""):
    return '<a href="%s" title="%s">%s</a>' % (link, title, text)


def th(*cols, rowclass=''):
    return td(*cols, rowclass=rowclass, tag='th')


def td(*cols, rowclass='', href='', tag='td'):
    r = ''
    r += '<tr class="%s">' % rowclass
    for x in cols:
        r += '<%s>' % tag
        if href:
            r += '<a href="%s">' % href
        r += str(x)
        if href:
            r += '</a>'
        r += '</%s>' % tag
    r += '</tr>'
    return r


# list of options, possibly duplicate 
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
        freq_sorted.append( (1, strmaker(force_top)) )

    if isinstance(options, Counter):
        pairs = options.items()
    else:        
        groups = { }
        for opt in options:
            s = strmaker(opt)
            if not s in groups:
                groups[s] = [ opt ]
            else:
                groups[s].append(opt)

        pairs = [(k, len(v)) for k, v in groups.items()]

    freq_sorted.extend(sorted([(v, k or "(misc)") for k, v in pairs], reverse=True))

    if not freq_sorted:
        return ""
    elif len(freq_sorted) == 1:
        n, k = freq_sorted[0]
        return strnum(k, n)

    r = '<div class="options">'
    r += '<select>'

    for n, k in freq_sorted:
        r += '<option>%s</option>' % strnum(k, n)

    r += '</select>'
    r += '</div>'
    r += '<div class="num"> %s</div>' % len(freq_sorted)
    return r



def table_row(row, keys, rowclass="row", tag="td"):
    if isinstance(row, dict):
        row = [ row[k] for k in keys ]

    out = '<tr class="%s">' % rowclass
    for k, v in zip(keys, row):
        try:
            v = str(v or "")
        except UnicodeDecodeError:
            v = "???"

        out += '<%s class="%s">' % (tag, k.strip())
        out += v
        out += '</%s>'  % tag  # end cell
    out += '</tr>\n'  # end row
    return out


def html_table(rows, colnames, rowclass="row"):
    out = '<table>'
    out += table_row(colnames, colnames, tag='th')

    for r in rows:
        out += table_row(r, colnames, rowclass)

    out += '</table>'  # end table
    return out


