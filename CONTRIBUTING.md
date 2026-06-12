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

## Code style

The xd project mostly follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).
