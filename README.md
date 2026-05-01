# xd

The xd project includes a [text format for crossword puzzles](doc/xd-format.md) and a pipeline for downloading, parsing, analyzing puzzles, and producing the website and released data at [xd.saul.pw](https://xd.saul.pw).

## Validating .xd files

[`xdlint.py`](xdlint.py) is the authoritative validator for the .xd format. It enforces the [spec](doc/xd-format.md) plus a set of structural and quality rules grounded in real-world fix patterns. Stdlib-only, no dependencies.

    xdlint.py path [path ...]              # lint files or directories
    xdlint.py --base BASE [--head HEAD]    # lint files changed in a git diff
    xdlint.py --list-rules                 # print the rule catalog
    xdlint.py --no-experimental ...        # skip rules interpreting unspec'd extensions

See [`doc/rebus-conventions.md`](doc/rebus-conventions.md) for the rebus / quantum / Schrödinger conventions the linter recognizes (these are extensions to the spec, not yet formalized).

## Requirements

- python 3.7+
- git
- markdown (to build website)
- sqlite (for grid comparison)
- gcc (to build sqlite plugin)
- aws-cli (to deploy)

# Running the pipeline

1. Checkout the gxd repo (private; join [#crosswords on the Discord](https://saul.pw/chat) to discuss getting access).

    make setup

2. Download new puzzles from known sources, convert to .xd, shelve, and commit to gxd repo.

    make import

Raw puz/etc files saved to .zip in /tmp, and .xd files saved to `gxd` directory.

3. Analyze puzzles

    make analyze

Output in `pub` directory.

4. Build website

    make website

Output in `wwwroot` directory.

5. Generate `gxd.sqlite` database (400MB)

    make gxd.sqlite

6. Find similar grids (takes ~12 hours)

    make gridmatches

Similarity scores saved to `gridmatches` table in gxd.sqlite.
