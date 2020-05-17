"""This is test_xdfile.py"""

import xdfile as xdfile

test_selection = 'nyt1955-01-01.xd'


def test_parse_pathname():
    fname = xdfile.parse_pathname(test_selection)
    assert fname.base == 'nyt1955-01-01'
    # xobject = xdfile.xdfile(xd_contents=testfile, xd_filename='derp')
