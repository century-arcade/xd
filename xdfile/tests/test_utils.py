"""unit tests for utils.py"""
import datetime

import os

from xdfile import utils

test_selection = 'nyt1955-01-01.xd'
TEST_DIRECTORY = os.path.abspath(os.path.dirname(__file__))


def test_parse_date():

    date = ('nyt', utils.parse_date_from_filename(test_selection))
    assert isinstance(date, tuple)
    assert date[0] == 'nyt'
    assert isinstance(date[1], datetime.date)
    assert date[1].strftime('%a %b %d %Y') == 'Sat Jan 01 1955'


def test_find_files():
    mygen = utils.find_files(TEST_DIRECTORY)
    for fullfn, contents in mygen:
        # It should throw out anything starting with '.'
        assert not fullfn.startswith('.')

