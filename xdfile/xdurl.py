#!/usr/bin/env python3
"""Pack an .xd file into a short URL token for the static /solve player.

Token = base64url(mode byte + deflate-raw payload).  The payload is
compressed against a 32KB preset dictionary; the browser has no preset
dictionary support, so the player prepends the dictionary as stored deflate
blocks and discards that much output.

Mode byte: (dictionary version << 1) | slim; version 0 is no dictionary
(links made in the browser, which has CompressionStream but no zdict).  Slim drops clue numbers and answers,
which the player re-derives from the grid; it is used only when it
reconstructs the original text exactly.
"""

import base64
import re
import struct
import sys
import zlib
from pathlib import Path

DICT_VERSION = 1
DICT_SIZE = 32768
DICT_PATH = Path(__file__).resolve().parent.parent / 'scripts' / 'html' / f'xd-d{DICT_VERSION}.dict'
DEFAULT_BASE = 'https://xd.saul.pw/solve?p='

CLUE_RE = re.compile(r'^([AD])(\d+)\. (.*) ~ (.*)$')


def split_xd(text):
    """Return (headers, grid, head, rest) line lists; head = headers..grid inclusive."""
    lines = text.split('\n')
    i = 0
    while i < len(lines) and lines[i].strip():
        i += 1
    headers = lines[:i]
    while i < len(lines) and not lines[i].strip():
        i += 1
    j = i
    while j < len(lines) and lines[j].strip():
        j += 1
    return headers, lines[i:j], lines[:j], lines[j:]


def rebus_map(headers):
    for h in headers:
        k, _, v = h.partition(':')
        if k.strip().lower() == 'rebus':
            return dict(p.split('=', 1) for p in re.split(r'[\s,]+', v) if '=' in p)
    return {}


def expected_clues(grid_rows, rebus):
    """[(dir, num, answer)] for all across entries, then all down, in grid order."""
    rows = [r.strip() for r in grid_rows]
    h = len(rows)

    def is_cell(y, x):
        return 0 <= y < h and 0 <= x < len(rows[y]) and rows[y][x] not in '#_'

    def cellval(y, x):
        c = rows[y][x]
        return rebus.get(c, c.upper())

    across, down = [], []
    num = 0
    for y in range(h):
        for x in range(len(rows[y])):
            if not is_cell(y, x):
                continue
            starts_a = not is_cell(y, x - 1) and is_cell(y, x + 1)
            starts_d = not is_cell(y - 1, x) and is_cell(y + 1, x)
            if not (starts_a or starts_d):
                continue
            num += 1
            if starts_a:
                n, ans = x, ''
                while is_cell(y, n):
                    ans += cellval(y, n)
                    n += 1
                across.append(('A', num, ans))
            if starts_d:
                n, ans = y, ''
                while is_cell(n, x):
                    ans += cellval(n, x)
                    n += 1
                down.append(('D', num, ans))
    return across + down


def slim(text):
    """Drop `A1. ` and ` ~ ANSWER` from clue lines, or None if not reversible."""
    headers, grid, head, rest = split_xd(text)
    if not grid:
        return None
    exp = expected_clues(grid, rebus_map(headers))
    out, k = [], 0
    for line in rest:
        if k < len(exp) and line.strip():
            m = CLUE_RE.match(line)
            if not m or (m[1], int(m[2]), m[4]) != exp[k] or not m[3].strip():
                return None
            out.append(m[3])
            k += 1
        else:
            out.append(line)
    if k < len(exp):
        return None
    s = '\n'.join(head + out)
    return s if unslim(s) == text else None


def unslim(text):
    headers, grid, head, rest = split_xd(text)
    exp = expected_clues(grid, rebus_map(headers))
    out, k = [], 0
    for line in rest:
        if k < len(exp) and line.strip():
            d, n, ans = exp[k]
            out.append(f'{d}{n}. {line} ~ {ans}')
            k += 1
        else:
            out.append(line)
    return '\n'.join(head + out)


def stored_blocks(data):
    out = b''
    for i in range(0, len(data), 65535):
        chunk = data[i:i + 65535]
        out += b'\x00' + struct.pack('<HH', len(chunk), len(chunk) ^ 0xffff) + chunk
    return out


def load_dict(path=DICT_PATH):
    return Path(path).read_bytes()


def encode(text, zdict=None):
    zdict = load_dict() if zdict is None else zdict
    s = slim(text)
    body = (s if s is not None else text).encode('utf-8')
    c = zlib.compressobj(9, zlib.DEFLATED, -15, 9, zdict=zdict)
    payload = bytes([(DICT_VERSION << 1) | (s is not None)]) + c.compress(body) + c.flush()
    return base64.urlsafe_b64encode(payload).rstrip(b'=').decode('ascii')


def decode(token, zdict=None):
    raw = base64.urlsafe_b64decode(token + '=' * (-len(token) % 4))
    mode, payload = raw[0], raw[1:]
    if mode >> 1 == 0:
        zdict = b''
    elif mode >> 1 != DICT_VERSION:
        raise ValueError(f'unknown dictionary version {mode >> 1}')
    elif zdict is None:
        zdict = load_dict()
    out = zlib.decompressobj(-15).decompress(stored_blocks(zdict) + payload)
    text = out[len(zdict):].decode('utf-8')
    return unslim(text) if mode & 1 else text


def train(paths, out=DICT_PATH, nsamples=16000, seed=1):
    import random
    import zstandard  # pyright: ignore[reportMissingImports]

    files = sorted(f for p in paths for f in Path(p).rglob('*.xd'))
    random.Random(seed).shuffle(files)
    samples = []
    for f in files[:nsamples]:
        text = f.read_text(encoding='utf-8', errors='replace')
        samples.append((slim(text) or text).encode('utf-8'))
    d = zstandard.train_dictionary(40000, samples, threads=-1).as_bytes()[-DICT_SIZE:]
    Path(out).write_bytes(d)
    print(f'{out}: {len(d)} bytes from {len(samples)} of {len(files)} files', file=sys.stderr)


def main(argv=None):
    import argparse

    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(description="Pack .xd files into /solve URLs.",
                                 epilog='subcommands: train PATH... | decode TOKEN_OR_URL')
    if argv[:1] == ['train']:
        ap.add_argument('paths', nargs='+', help='.xd trees to sample')
        ap.add_argument('-o', '--output', default=str(DICT_PATH))
        ap.add_argument('-n', '--nsamples', type=int, default=16000)
        args = ap.parse_args(argv[1:])
        train(args.paths, args.output, args.nsamples)
    elif argv[:1] == ['decode']:
        ap.add_argument('token')
        args = ap.parse_args(argv[1:])
        sys.stdout.write(decode(args.token.rsplit('p=', 1)[-1]))
    else:
        ap.add_argument('-b', '--base', default=DEFAULT_BASE, help='URL prefix')
        ap.add_argument('files', nargs='*', help='.xd files to encode (- for stdin)')
        args = ap.parse_args(argv)
        for f in args.files or ['-']:
            text = sys.stdin.read() if f == '-' else Path(f).read_text(encoding='utf-8')
            print(args.base + encode(text))


if __name__ == '__main__':
    main()
