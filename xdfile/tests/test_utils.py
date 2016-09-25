"""unit tests for utils.py"""
import os

from xdfile import utils

TEST_DIRECTORY = os.path.abspath(os.path.dirname(__file__))


def test_find_files():
    mygen = utils.find_files(TEST_DIRECTORY)
    for fullfn, contents in mygen:
        # It should throw out anything starting with '.'
        assert not fullfn.startswith('.')
