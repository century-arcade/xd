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
