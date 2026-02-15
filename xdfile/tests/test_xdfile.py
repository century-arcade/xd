"""This is test_xdfile.py"""

import datetime

from xdfile.utils import parse_pathname, parse_date_from_filename

test_selection = 'nyt1955-01-01.xd'


def test_filename():
    fname = parse_pathname(test_selection).base
    assert fname == 'nyt1955-01-01'


def test_parse_date():
    date = parse_date_from_filename(test_selection)
    assert isinstance(date, datetime.date)
    assert date.strftime('%a %b %d %Y') == 'Sat Jan 01 1955'
