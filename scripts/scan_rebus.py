#!/usr/bin/env python3
"""One-shot scan of gxd corpus to bucket Rebus values by / vs | usage."""
import os
import re
import sys

base = sys.argv[1] if len(sys.argv) > 1 else 'gxd'
slash_only = []
pipe_only = []
both = []
plain_rebus = 0
literal_slash = []
total_files = 0
files_with_rebus = 0

rebus_re = re.compile(r'^Rebus:\s*(.+)$', re.MULTILINE)

for root, dirs, files in os.walk(base):
    for fn in files:
        if not fn.endswith('.xd'):
            continue
        total_files += 1
        fp = os.path.join(root, fn)
        try:
            with open(fp, encoding='utf-8') as f:
                txt = f.read()
        except Exception:
            continue
        m = rebus_re.search(txt)
        if not m:
            continue
        files_with_rebus += 1
        header_value = m.group(1).strip()
        parts = [p for p in header_value.split() if '=' in p]
        has_slash_op = False
        has_pipe_op = False
        has_literal_slash = False
        for p in parts:
            _, _, v = p.partition('=')
            if '/' in v:
                idx = v.index('/')
                if v[:idx] and v[idx + 1:]:
                    has_slash_op = True
                else:
                    has_literal_slash = True
            if '|' in v:
                pieces = v.split('|')
                if len(pieces) >= 2 and all(pieces):
                    has_pipe_op = True
        rel = os.path.relpath(fp, base).replace(os.sep, '/')
        if has_slash_op and has_pipe_op:
            both.append(rel)
        elif has_slash_op:
            slash_only.append(rel)
        elif has_pipe_op:
            pipe_only.append(rel)
        else:
            plain_rebus += 1
        if has_literal_slash:
            literal_slash.append(rel)

print(f'Total .xd files scanned:     {total_files}')
print(f'Files with Rebus: header:    {files_with_rebus}')
print(f'  plain (no / or |):         {plain_rebus}')
print(f'  uses / operator only:      {len(slash_only)}')
print(f'  uses | operator only:      {len(pipe_only)}')
print(f'  uses both / and |:         {len(both)}')
print(f'  uses literal / (1=/):      {len(literal_slash)}')
print()
print('=== files with /  operator only ===')
for f in slash_only:
    print(f'  {f}')
print()
print('=== files with |  operator only ===')
for f in pipe_only:
    print(f'  {f}')
print()
print('=== files with BOTH / and | ===')
for f in both:
    print(f'  {f}')
print()
print('=== files with literal / (1=/) ===')
for f in literal_slash:
    print(f'  {f}')
