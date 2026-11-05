# xdlint

`xdlint` is the validator for the [.xd crossword format](https://github.com/century-arcade/xdformat).
It checks `.xd` files against the spec, plus a set of structural and quality
rules that come from fixes made again and again in the
[xd corpus](https://github.com/century-arcade/xd). Many findings have a
mechanical fix that `xdlint --fix` can apply.

It is a single module that uses only the standard library, with no dependencies.
Python 3.10 or newer.

## Install

    pip install xdlint

## Usage

    xdlint path [path ...]               # lint .xd files, or directories (recursive)
    xdlint --fix path ...                # apply mechanical fixes in place
    xdlint --fix --diff path ...         # show the fixes as a unified diff, change nothing
    xdlint --base BASE [--head HEAD]     # lint only the .xd files changed in a git diff
    xdlint --list-rules                  # print the rule catalog
    xdlint --version

`--max-severity {error,warning,info,debug}` (default `warning`) sets which
findings are printed, and xdlint exits 1 if any finding is at or above that
level. `--disable XD###,...` and `--enable-only XD###,...` select rules.
`--no-experimental` skips rules that interpret extensions the spec doesn't
cover yet. `--profile gxd` adds the editorial conventions of the gxd corpus.
Run `xdlint --help` for every option.

The .xd format is specified at
[century-arcade/xdformat](https://github.com/century-arcade/xdformat).
The `xdformat` package there is the parser; xdlint is the separate linter.

## Building and releasing

The source is `xdlint.py` at the root of the
[xd repository](https://github.com/century-arcade/xd); this directory only
packages it. The version is `__version__` in `xdlint.py`.

To build locally, from the repo root:

    cp xdlint.py LICENSE packaging/xdlint/
    python -m build packaging/xdlint
    twine check --strict packaging/xdlint/dist/*

To release version X.Y.Z:

1. Set `__version__ = "X.Y.Z"` in `xdlint.py` and merge that to master.
2. Tag that commit and push the tag:

       git tag xdlint-vX.Y.Z <commit>
       git push origin xdlint-vX.Y.Z

The `release-xdlint` workflow (`.github/workflows/release-xdlint.yml`) checks
that the tag matches `__version__` and is on master, builds the sdist and wheel,
runs the tests against the built wheel, uploads to PyPI with trusted publishing,
and creates a GitHub release with the files attached.
