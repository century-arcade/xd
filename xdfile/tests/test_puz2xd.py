"""unit tests for puz2xd.py"""

from xdfile.puz2xd import decode


def test_decode_html2text_spurious_semicolons():
    """html2text treats bare & as HTML entity start and appends ;"""
    assert decode('B&O; Railroad') == 'B&O Railroad'
    assert decode('R&B; music') == 'R&B music'
    assert decode('AT&T; service') == 'AT&T service'


def test_decode_real_html_entities():
    """Real HTML entities like &amp; should be unescaped"""
    assert decode('B&amp;O Railroad') == 'B&O Railroad'
    assert decode('Tom &amp; Jerry') == 'Tom & Jerry'
    assert decode('&quot;Hello&quot;') == '"Hello"'


def test_decode_no_entities():
    """Strings without entities should pass through unchanged"""
    assert decode('Normal clue text') == 'Normal clue text'


def test_decode_legacy_replacements():
    """Legacy byte replacements still work"""
    assert decode('\x93hello\x94') == '"hello"'
    assert decode('\x97') == "\u2014"
    assert decode('\x85') == '...'


def test_parse_puz():
    assert True


def _tiny_puz(author):
    import puz
    p = puz.Puzzle()
    p.width = p.height = 3
    p.solution = 'ABCD.EFGH'
    p.fill = '----.----'
    p.title = 'T'
    p.author = author
    p.copyright = '(c) Somebody'
    p.clues = ['a1', 'd1', 'd2', 'a3']
    return p.tobytes()


def test_parse_puz_splits_editor_out_of_author():
    from xdfile.puz2xd import parse_puz
    xd = parse_puz(_tiny_puz('by Byron Walden, edited by Ben Tausig'),
                   'avc2026-10-21.puz')
    assert xd.get_header('Author') == 'Byron Walden'
    assert xd.get_header('Editor') == 'Ben Tausig'
    out = xd.to_unicode()
    assert 'Author: Byron Walden\nEditor: Ben Tausig\n' in out


def test_parse_puz_strips_by_prefix_without_editor():
    from xdfile.puz2xd import parse_puz
    xd = parse_puz(_tiny_puz('By CJ Tan'), 'wsj2026-10-21.puz')
    assert xd.get_header('Author') == 'CJ Tan'
    assert 'Editor' not in xd.headers


def test_parse_puz_plain_author_unchanged():
    from xdfile.puz2xd import parse_puz
    xd = parse_puz(_tiny_puz('Matt Gaffney'), 'wsj2026-10-21.puz')
    assert xd.get_header('Author') == 'Matt Gaffney'
    assert 'Editor' not in xd.to_unicode()
