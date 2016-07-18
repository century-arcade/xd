#!/usr/bin/env python3

""" Splits complex puzzle repos (like BWH) into separate zips """
import os
import sys
import re
import tempfile
import shutil
import zipfile
import tarfile
from xdfile.utils import progress, iso8601, get_args, args_parser, open_output, parse_pathname
from xdfile.metadatabase import xd_sources_row, xd_sources_header


p = args_parser('process huge puzzles archive into separate .zip and create sources.tsv')
p.add_argument('-s', '--source', default=None, help='ExternalSource')
#p.add_argument('-i', '--input', default=None, help='Input')
args = get_args(parser=p)

outf = open_output()

if args.inputs:
    source = args.inputs[0]
else:
    print('Supply path | .zip | .tar.gz with puzzles to be processed')
    sys.exit(2)

if os.path.isdir(source) and not args.source:
    print('Provide source name for path input')
    sys.exit(2)

tempdirs = {}

archive = True
if os.path.isdir(source):
    archive = False
    ztemp = source
    source = sys.argv[2]
elif zipfile.is_zipfile(source):
    zipfile = zipfile.ZipFile(source, 'r')
    zitems = zipfile.namelist()
elif tarfile.is_tarfile(source):
    zipfile = tarfile.open(source, 'r:*')
    zitems = zipfile.getnames()
else:
    print('Incorrect archive supplied')
    sys.exit(2)

if archive:
    # First unpack .zip
    ztemp = tempfile.mkdtemp()
    print('Extracting to %s' % ztemp)
    for f in zitems:
        progress('Extracting %s' % f)
        zipfile.extract(f, path=ztemp)

for root, dirs, files in os.walk(ztemp):
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
        ret = shutil.copy2(fullname, tempdirs[prefix])
        if ret:
            os.remove(fullname)

outbase = parse_pathname(args.output).base
sources = []

for p in tempdirs:
    td = tempdirs[p]
    zip_file = p + '.zip'
    zip_file_fp = zip_file if archive else os.path.join(ztemp, zip_file)
    with zipfile.ZipFile(zip_file_fp, 'w') as myzip:
        for f in [f for f in os.listdir(td) if os.path.isfile(os.path.join(td, f))]:
            print("Zipping file %s to %s" % (f, zip_file_fp))
            myzip.write(os.path.join(td, f), arcname=f)
        sources.append(xd_sources_row(zip_file, source, iso8601())))


outf.write_file("%s.tsv" % outbase, xd_sources_header + "".join(sources))

print('Temp dirs cleanup')
if archive:
    shutil.rmtree(ztemp)

for p in tempdirs:
    shutil.rmtree(tempdirs[p])
