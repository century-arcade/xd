#!/usr/bin/env python3

from xdfile import utils, html, pubyear

def main():
    args = utils.get_args('make toplevel index.html')
    outf = utils.open_output()

    h = pubyear.pubyear_html()

    outf.write_html('pub/index.html', h, title='The xd crossword puzzle corpus')

main()    
