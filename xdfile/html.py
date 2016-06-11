import cgi
import time
from collections import Counter
import xdfile


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


def mktag(tagname, tagclass=''):
    """ generates tag:
        <tag class="class">
    """
    if tagclass:
        return '<%s class="%s">' % (tagname, tagclass)
    else:
        return '<%s>' % (tagname)


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


def table_row(row, keys, rowclass="row", tag="td"):
    if isinstance(row, dict):
        row = [row[k] for k in keys]

    out = mktag('tr', rowclass)
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
    """
    out = mktag('table', tableclass)
    out += table_row(colnames, colnames, tag='th')

    for r in rows:
        out += table_row(r, colnames, rowclass=rowclass)

    out += mktag('/table')  # end table
    return out


def tsv_to_table(rows):
    return html_table(rows, rows[0]._fields)
