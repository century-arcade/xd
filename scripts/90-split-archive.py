#!/usr/bin/env python3

""" Splits complex puzzle repos (like BWH) into separate zips """
import os
import sys
import re
import tempfile
import shutil
import zipfile


if len(sys.argv) > 1:
    input_dir = sys.argv[1]
else:
    print('Supply path with puzzles to be processed')
    sys.exit(2)

tempdirs = {}
for root, dirs, files in os.walk(input_dir):
    for file in files:
        fullname = os.path.join(root,file)
        # Remove dotfiles
        if file[0] == '.':
            os.remove(fullname)
            continue

        # Dont process .zip
        if '.zip' in file:
            continue

        m = re.match(r'^([a-z]{2,4})[\-0-9]{1}.*', file, flags=re.IGNORECASE)
        if not m:
            # Don't process those not matched pattern
            continue
        
        prefix = m.group(1).lower()
        if prefix not in tempdirs:
            tempdirs[prefix] = tempfile.mkdtemp(prefix=prefix + "_")
        
        print("Processing file %s -> %s" % (fullname, tempdirs[prefix]))
        ret = shutil.copy(fullname, tempdirs[prefix])
        if ret:
            os.remove(fullname)

for p in tempdirs:
    td = tempdirs[p]
    zip_file = os.path.join(input_dir, p + '.zip')
    with zipfile.ZipFile(zip_file, 'w') as myzip:
        for f in [f for f in os.listdir(td) if os.path.isfile(os.path.join(td, f))]:
            print("Zipping file %s to %s" % (f, zip_file))
            myzip.write(os.path.join(td, f), arcname=f)

print('Temp dirs cleanup')
for p in tempdirs:
    shutil.rmtree(tempdirs[p])
