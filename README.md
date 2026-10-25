# xd

The xd project includes a [text format for crossword puzzles](doc/xd-format.md) and a pipeline for downloading, parsing, analyzing puzzles, and producing the website and released data at [xd.saul.pw](https://xd.saul.pw).

## Validating .xd files

[`xdlint.py`](xdlint.py) is the authoritative validator for the .xd format. It enforces the [spec](doc/xd-format.md) plus a set of structural and quality rules grounded in real-world fix patterns. Stdlib-only, no dependencies.

    xdlint.py path [path ...]              # lint files or directories
    xdlint.py --base BASE [--head HEAD]    # lint files changed in a git diff
    xdlint.py --list-rules                 # print the rule catalog
    xdlint.py --no-experimental ...        # skip rules interpreting unspec'd extensions
    xdlint.py --profile gxd ...            # also apply gxd's editorial policy

See [`doc/rebus-conventions.md`](doc/rebus-conventions.md) for the rebus / quantum / Schrödinger conventions the linter recognizes (these are extensions to the spec, not yet formalized).

### `--profile gxd`

The gxd corpus has editorial conventions beyond the format, written in gxd's `EDITORIAL.md` and `CONTRIBUTING.md`. `--profile gxd` checks them: it changes two severities and adds the XD8xx rules. Without `--profile`, xdlint's output is unchanged. No gxd rule is an error; a convention marked [established] or [practice] there is a warning, a [proposed] one is info.

| Code | Severity | Checks | gxd doc section |
|---|---|---|---|
| XD016 | error → info | grid has no answers | EDITORIAL.md, Incomplete puzzles (puzzles without answers are welcome) |
| XD103 | info → warning | editor folded into `Author:`; also matches `X; Ed. Y` | EDITORIAL.md, Headers, `Editor:` |
| XD801 | warning, fix | `Author:` starts with "By " | EDITORIAL.md, Headers, `Author:` |
| XD802 | warning, fix | editor credit in `Copyright:` | EDITORIAL.md, Headers, `Editor:` / `Copyright:` |
| XD803 | warning | `<pubid>-<number>.xd` without a matching `Number:` (skips `nytpack`, whose number is an NYT id, and provisional names) | CONTRIBUTING.md, Numbered series; EDITORIAL.md, `Number:` |
| XD804 | warning | the `Meta:` answer appears in the notes | EDITORIAL.md, Headers, `Meta:` |
| XD805 | warning | `{/x/}`-style markup in a header or the notes | EDITORIAL.md, Characters and typography |
| XD806 | info | `[sic]` in a clue (for review: the publisher's own `[sic]` matches too) | EDITORIAL.md, Clues and grid |
| XD807 | warning | `[XXX]` placeholder clue and no notes | EDITORIAL.md, Incomplete puzzles |
| XD808 | info | provenance in the notes ("Litzed by", "OCR", "downloaded from", ...) | EDITORIAL.md, Notes |
| XD809 | info, new imports | `&` joins authors (gxd uses "and") | EDITORIAL.md, Headers, `Author:` (proposed) |
| XD810 | info, new imports | a title that is only a date, not in the form `Tuesday, October 6, 2026` (an outlet label before the date, an open question in EDITORIAL.md, is not checked) | EDITORIAL.md, Headers, `Title:` (proposed) |

The two rules for new imports apply only to puzzles being added, since existing files are not changed: in `--base` mode they run on files the diff adds (not modified ones), and in path mode only with `--new-imports`.

See [`doc/rebus-conventions.md`](doc/rebus-conventions.md) for the rebus / quantum / Schrödinger conventions the linter recognizes (these are extensions to the spec, not yet formalized).

## Requirements

- python 3.7+
- git
- pandoc (to build website)
- sqlite (for grid comparison)
- gcc (to build sqlite plugin)

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
