# Project overview
xd is a crossword puzzle processing pipeline. It defines the `.xd` plain-text format and provides tools to convert from other formats (puz, ipuz, XML, JSON) into `.xd`.

# Key directories
- `xdfile/` — Main Python package: parser, converter modules, utilities
- `xdfile/tests/` — pytest tests
- `crossword/` — Local fork of the `crossword` Python library (used by puz2xd)
- `scripts/` — Utility scripts for processing and web serving
- `doc/` — Documentation including `xd-format.md` (the format spec)

# Important files
- `xdfile/xdfile.py` — Core `xdfile` class: parse_xd(), to_unicode(), grid/clue iteration
- `xdfile/utils.py` — Utilities: parse_pathname(), parse_date_from_filename(), file I/O
- `xdfile/puz2xd.py` — .puz → .xd converter (module version, used as library)
- `puz2xd-standalone.py` — .puz → .xd converter (standalone script, duplicates decode/xdfile logic)
- `xdfile/__init__.py` — Just `from .xdfile import *`

# .xd format structure
Sections separated by double blank lines:
1. Headers (key: value pairs)
2. Grid (rows of characters, `#` = block)
3. Clues (`A1. Clue text ~ ANSWER`)
4. Notes (optional)

# Architecture notes
- `puz2xd-standalone.py` duplicates the `xdfile` class and `decode()` from `xdfile/puz2xd.py` — changes to one should be mirrored in the other
- The `decode()` function handles character encoding cleanup for .puz files. It chains: byte replacements → urllib.parse.unquote → html.unescape → invalid entity cleanup
- `to_unicode()` automatically inserts blank lines between clue direction changes (A→D), so `parse_xd()` should NOT insert clue breaks for blank lines between directions
- `append_clue_break()` adds `(('', ''), '', '')` sentinel entries to the clues list — used as separators, not real clues

# Testing
```
# Needs venv with dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
pytest xdfile/tests/
```
