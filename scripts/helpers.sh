
if [ ! -n "$NOW" ]; then
    echo "config not available, run: source config"
    exit 1
fi

if [ -n "$NODRY" ]; then
    aws="aws"
    set -x
else
    aws="echo -e \naws"
fi

sh="sh"
python="/usr/bin/env python3"
