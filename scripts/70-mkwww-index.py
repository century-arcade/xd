#!/usr/bin/env python3

from xdfile import utils, html, pubyear

def main():
    args = utils.get_args('make toplevel index.html')
    outf = utils.open_output()

    h = '<h2>The xd crossword corpus</h2>'
    h += 'All published crosswords (American-style, 15x15 and larger)'
    h += '<hr/>'
    h += pubyear.pubyear_html()

    outf.write_html('index.html', h)

main()    
