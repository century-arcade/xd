"""This is test_xdfile.py"""

import datetime

import xdfile as xdfile

test_selection = 'nyt1955-01-01.xd'


def test_filename():
    fname = xdfile.get_base_filename(test_selection)
    assert fname == 'nyt1955-01-01'
    # xobject = xdfile.xdfile(xd_contents=testfile, xd_filename='derp')


def test_parse_date():

    date = xdfile.parse_date_from_filename(test_selection)
    assert isinstance(date, tuple)
    assert date[0] == 'nyt'
    assert isinstance(date[1], datetime.date)
    assert date[1].strftime('%a %b %d %Y') == 'Sat Jan 01 1955'
