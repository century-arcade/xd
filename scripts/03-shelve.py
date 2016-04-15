#!/usr/bin/env python
#
# Usage: $0 [-o <output-xd> <input>
#
#   Renames the <input> file(s) according to metadata (in .xd, .tsv, or filenameb)
#   Appends to puzzles.tsv
#

        pfn = parse_filename(fn)
        acceptable_chars = string.lowercase + string.digits + "_-"
        base = "".join([ch for ch in pfn.base.lower() if ch in acceptable_chars])

        path, fn = os.path.split(fullfn)
        base_orig, ext = os.path.splitext(fn)

        try:


            outfn = get_target_location(xd)

            if g_args.toplevel:
                # the toplevel option is for moving some or all subset into a flattened directory
                fullfn = "%s/%s/%s.xd" % (g_args.toplevel, xd.filename.lstrip("crosswords/"), base)
            else:
                fullfn = outfn

            xd.filename = fullfn

            clean_headers(xd)

            if g_args.metadata_only:
                print(xd_metadata(xd))
            else:
                save_file(xd, outf)
        except Exception, e:
            log("error: %s: %s" % (unicode(e), type(e)))
            if g_args.debug:
                raise


def save_file(xd, outf):
    outfn = xd.filename

    xdstr = xd.to_unicode().encode("utf-8")

    # check for duplicate filename and contents

    xdhash = hash(xdstr)

    while outfn in all_files:
        if all_files[outfn] == xdhash:
            log("exact duplicate")
            return

        log("same filename, different contents: '%s'" % outfn)
        outfn += ".2"

    all_files[outfn] = xdhash

    if xdhash in all_hashes:
        log("duplicate contents of %s" % all_hashes[xdhash])
    else:
        all_hashes[xdhash] = outfn

    # write to output

    if isinstance(outf, zipfile.ZipFile):
        if year < 1980:
            year = 1980
        zi = zipfile.ZipInfo(outfn, (year, month, day, 9, 0, 0))
        zi.external_attr = 0444 << 16L
        zi.compress_type = zipfile.ZIP_DEFLATED
        outf.writestr(zi, xdstr)
    elif isinstance(outf, file):
        outf.write(xdstr)
    else:
        try:
            basedirs, fn = os.path.split(outfn)
            os.makedirs(basedirs)
        except:
            pass
        file(outfn, "w-").write(xdstr)
