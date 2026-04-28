#!/bin/bash
#
# Checks .xd files for errors. Thin shim around xdlint.py.
# Usage: $0 <DIR-or-FILE...>
#
exec python3 "$(dirname "$0")/xdlint.py" "$@"
