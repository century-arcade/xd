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
  <!--a href="http://saul.pw"><small>saul.pw</small></a-->
  <a href="mailto:xd@saul.pw"><small>xd@saul.pw</small></a>

</body>
</html>
"""

html_redirect = """<html><head><meta http-equiv="refresh" content="0; URL='{url}'" />
<script>window.location.replace("{url}");</script></head><body>Redirecting to <a href="{url}">{url}</a></body></html>"""

def th(*cols, rowclass=''):
    r = '<tr class="%s"><th>' % rowclass
    r += '</th><th>'.join(str(x) for x in cols) + '</th></tr>'
    return r

def td(*cols, rowclass=''):
    r = '<tr class="%s"><td>' % rowclass
    r += '</td><td>'.join(str(x) for x in cols) + '</td></tr>'
    return r
