"""A puzzle's place in the corpus: its pubid, xdid, date and year.

These are gxd conventions, not part of the .xd format, so they are functions
of a parsed puzzle and not methods of the xdfile class. They work on any
xdfile, whoever made it: the corpus loader, a converter, a test.

    from xdfile import ids
    ids.xdid(xd)      # 'nyt1955-01-01'
    ids.pubid(xd)     # 'nyt'
"""

import re

from .utils import parse_pubid, parse_pathname, dated_xdid


def number_slug(num):
    num = str(num).strip()
    if num.isdigit():
        return '%03d' % int(num)
    return re.sub(r'[^A-Za-z0-9]', '_', num)


def pubid(xd):
    """The publication id, read from the puzzle's filename ('nyt'); None
    for a puzzle with no filename."""
    if not xd.filename:
        return None
    return parse_pubid(xd.filename)


def date(xd):
    """The Date header; without one, what follows the pubid in the filename."""
    dt = xd.get_header("Date")
    pub = pubid(xd)
    if not dt and pub:
        dt = parse_pathname(xd.filename).base[len(pub):]
        if dt[:1] == '-' and dt[1:5].isdigit() and dt[5:6] == '-':  # club72-2020-01-01
            dt = dt[1:]
    return dt


def year(xd):
    return date(xd).split('-')[0]


def xdid(xd):
    """The puzzle's id, from its pubid and its Number or Date."""
    pub = pubid(xd)
    num = xd.get_header("Number")
    if num:
        return '%s-%s' % (pub, number_slug(num))

    assert date(xd)
    return dated_xdid(pub, date(xd))
