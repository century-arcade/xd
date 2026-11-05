# Contributing to xd

## Setting up the environment

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

## Running tests

```
pytest xdfile/tests/
```

## Validating .xd files

`xdlint.py` is the authoritative validator for the .xd format (stdlib-only). See the [README](README.md#validating-xd-files) for usage.

xdlint is also published to PyPI as its own distribution, [`xdlint`](https://pypi.org/p/xdlint), packaged from [`packaging/xdlint/`](packaging/xdlint/). To release: set `__version__` in `xdlint.py`, merge to master, then push a tag `xdlint-vX.Y.Z` on that commit; the `release-xdlint` workflow does the rest. Details in [packaging/xdlint/README.md](packaging/xdlint/README.md#building-and-releasing).

## Code style

The xd project mostly follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).
