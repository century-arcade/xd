
import os
import stat
import zipfile


def find_files(*paths):
    for path in paths:
        if stat.S_ISDIR(os.stat(path).st_mode):
            for thisdir, subdirs, files in os.walk(path):
                for fn in files:
                    if fn[0] == ".":
                        continue
                    for f, c in find_files(os.path.join(thisdir, fn)):
                        yield f, c
        else:
            try:
                with zipfile.ZipFile(path, 'r') as zf:
                    for zi in zf.infolist():
                        fullfn = zi.filename
                        contents = zf.read(zi)
                        yield fullfn, contents
            except:
                fullfn = path
                contents = file(path).read()
                yield fullfn, contents
