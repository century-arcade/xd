#!/usr/bin/env python

# apt-get install python-cherrypy3

import cherrypy
import string
import urllib

import mkwww
import findsimilar
import xdfile

body_html = """
<form method="get" action="find">
Paste the grid here in text format (use '#' as block):
<br/>

<textarea name="grid" rows="25" cols="25">
</textarea>
<br/>
<button type="submit">Find similar</button>
</form>"""

class httpxd(object):
    def __init__(self):
        self.corpus = xdfile.main_load()
        self.example_grid = '<div class="fixed">%s</div>' % "<br/>".join(self.corpus.values()[0].grid)

    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect("/search")

    @cherrypy.expose
    def search(self):
        return mkwww.html_header.format(title="Crossword Grid Search") + body_html + mkwww.html_footer

    @cherrypy.expose
    def style_css(self):
        cherrypy.response.headers['Content-Type']= 'text/css'
        return file("src/style.css").read()

    @staticmethod
    def xd_from_grid(grid):
        return xdfile.xdfile("Author: %s\n\n\n%s" % (cherrypy.request.remote.ip, grid))

    def error(self, errmsg):
        return mkwww.html_header.format(title="Crossword Grid Search") + body_html + '<div class="error">Error: %s</div>' % errmsg + mkwww.html_footer
    

    @cherrypy.expose
    def find(self, grid="", xd=""):
        xdobj = self.corpus.get(xd) or httpxd.xd_from_grid(grid)
        gridstr = "".join(filter(lambda x: x in string.uppercase, "".join(xdobj.grid).upper()))
        if len(gridstr) < 15: # one row, wouldn't really consider less than this a match anyway
            return self.error('please specify a more specific grid than "%s".  Example: <br/>%s' % (gridstr, self.example_grid))

        index_list = []
        dups = findsimilar.find_similar_to(xdobj, self.corpus.values())
        for pct, needle, other, same_answers in sorted(dups):
            pct *= 100
            if xd:
                parms = { "left": xdfile.get_base_filename(other.filename), "right": xd }
            else:
                parms = { "left": xdfile.get_base_filename(other.filename), "right": grid }
            index_line = '%d%% <a href="/diff/?%s">%s</a> %s' % (pct, urllib.urlencode(parms), xdfile.get_base_filename(other.filename), other.get_header("Author") or "")

            index_list.append((pct, index_line))

        r = mkwww.html_header.format(title="Crossword Search Results")
        r += "<ul>"

        fmt = '<li>%s</li>'
        sorted_list = sorted(index_list, reverse=True)
        matches = '\n'.join(fmt % L for pct, L in sorted_list if pct > 80 )
        partial = '\n'.join(fmt % L for pct, L in sorted_list if 50 < pct <= 80 )
        theme = '\n'.join(fmt % L for pct, L in sorted_list if 25 < pct <= 50 )
        unlikely = '\n'.join(fmt % L for pct, L in sorted_list if pct <= 25 )

        if matches:
            r += '\n<h3>Very similar</h3>\n' + matches

        if partial:
            r += '\n<h3>Partially similar</h3>\n' + partial

        if theme:
            r += '\n<h3>Possibly similar</h3>\n' + theme

        if not matches and not partial and not theme:
            r += "\n<h3>Nothing matched, but here's some dregs</h3>\n" + unlikely[:10]

        r += '</ul>'

        r += '<a href="/">search again</a>'
        r += mkwww.html_footer

        return r

    @cherrypy.expose
    def diff(self, left="", right=""):

        xd1 = self.corpus.get(left) or httpxd.xd_from_grid(left)
        xd2 = self.corpus.get(right) or httpxd.xd_from_grid(right)

        if xd1.grid and xd2.grid:
            diffstr, pct = mkwww.gendiff(xd1, xd2)
            return diffstr
        else:
            return self.error("Need two grids to diff")

cherrypy.config.update({'server.socket_host': '0.0.0.0',
                        'server.socket_port': 80,
                       })
cherrypy.quickstart(httpxd())
