import base64
import zlib
from pathlib import Path

from xdfile import xdurl

SAMPLE = Path(__file__).parent / 'nyt1955-01-01.xd'

REBUS = '''Title: Tiny rebus
Rebus: 1=ONE


1AB
C#D
EFG


A1. First ~ ONEAB
A3. Last ~ EFG

D1. Down one ~ ONECE
D2. Down three ~ BDG
'''


def test_slim_drops_numbers_and_answers():
    s = xdurl.slim(REBUS)
    assert s is not None
    assert 'First\nLast\n\nDown one\nDown three\n' in s
    assert '~' not in s
    assert xdurl.unslim(s) == REBUS


def test_slim_refuses_mismatched_answer():
    assert xdurl.slim(REBUS.replace('~ EFG', '~ EFX')) is None


def test_slim_refuses_clue_metadata():
    assert xdurl.slim(REBUS.replace('A3. Last ~ EFG\n', 'A3. Last ~ EFG\nA3 ^Refs: D1\n')) is None


def mode(token):
    return base64.urlsafe_b64decode(token[:4])[0]


def test_roundtrip_slim_with_dict():
    token = xdurl.encode(REBUS)
    assert xdurl.decode(token) == REBUS
    assert mode(token) == (xdurl.DICT_VERSION << 1) | 1


def test_roundtrip_full_fallback():
    for text in (REBUS.replace('~ EFG', '~ EFX'), SAMPLE.read_text(encoding='utf-8')):
        token = xdurl.encode(text)
        assert xdurl.decode(token) == text
        assert mode(token) == xdurl.DICT_VERSION << 1


def test_decode_without_dict():
    s = xdurl.slim(REBUS).encode()
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    token = base64.urlsafe_b64encode(b'\x01' + c.compress(s) + c.flush()).rstrip(b'=').decode()
    assert xdurl.decode(token) == REBUS


def test_stored_prefix_primes_window():
    zdict = xdurl.load_dict()
    c = zlib.compressobj(9, zlib.DEFLATED, -15, zdict=zdict)
    payload = c.compress(b'Title: hello') + c.flush()
    out = zlib.decompressobj(-15).decompress(xdurl.stored_blocks(zdict) + payload)
    assert out[len(zdict):] == b'Title: hello'
