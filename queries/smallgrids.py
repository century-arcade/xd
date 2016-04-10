import xdfile

for xd in xdfile.corpus():
    if xd.width() < 15 and xd.height() < 15:
        print xd
