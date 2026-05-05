#!/usr/bin/env python3

# Usage: $0 [-o <output-xd.zip>] <input>
#
#   Converts file in <input> to .xd, maintaining the original directory structure.
#   Appends to receipts.tsv
#

import fnmatch
import os
import time

from xdfile import IncompletePuzzleParse

from xdfile.utils import warn, debug, error
from xdfile.utils import find_files_with_time, parse_pathname, replace_ext, strip_toplevel
from xdfile.utils import args_parser, get_args, parse_tsv_data, iso8601, open_output, progress

from xdfile import metadatabase as metadb

from xdfile.ccxml2xd import parse_ccxml
from xdfile.uxml2xd import parse_uxml
from xdfile.ujson2xd import parse_ujson
from xdfile.puz2xd import parse_puz
from xdfile.xwordinfo2xd import parse_xwordinfo

from xdfile import catalog

import xdfile


def _load_excludes_file(fpath):
    out = []
    with open(fpath) as f:
        for i, line in enumerate(f):
            line = line.rstrip('\n')
            if not line:
                continue
            col0 = line.split('\t', 1)[0]
            if i == 0 and col0 == 'path':
                continue
            out.append(col0)
    return out


def _accept_path(path, includes, excludes):
    if includes and not any(fnmatch.fnmatch(path, pat) for pat in includes):
        return False
    if excludes and any(fnmatch.fnmatch(path, pat) for pat in excludes):
        return False
    return True


def main():
    global args
    parsers = {
        '.xml': [parse_ccxml, parse_uxml],
        '.json': [parse_ujson],
        '.puz': [parse_puz],
        '.html': [parse_xwordinfo],
        '.pdf': [],
        '.jpg': [],
        '.gif': [],
        '.xd': [],  # special case, just copy the input, in case re-emitting screws it up
    }

    p = args_parser('convert crosswords to .xd format')
    p.add_argument('--copyright', default=None, help='Default value for unspecified Copyright headers')
    p.add_argument('--extsrc', default=None, help='Value for receipts.ExternalSource')
    p.add_argument('--intsrc', default=None, help='Value for receipts.InternalSource')
    p.add_argument('--pubid', default=None, help='PublicationAbbr (pubid) to use')
    p.add_argument('--skip-unchanged', action='store_true', help='Skip writing .xd and appending receipt if output is byte-identical to existing file')
    p.add_argument('--reimport', action='store_true', help='Re-parse and rewrite .xd for sources that have already been received (e.g. to pick up parser or decoder fixes).')
    p.add_argument('--overwrite', action='store_true', help='Overwrite an existing shelf slot owned by a different (ExternalSource, SourceFilename). Without this, sibling-source duplicates and cross-source collisions are skipped with a warning.')
    p.add_argument('--include', action='append', default=None,
                   help='Glob (fnmatch) pattern; only SourceFilenames matching at least one --include are processed. May be repeated.')
    p.add_argument('--exclude', action='append', default=None,
                   help='Glob (fnmatch) pattern; SourceFilenames matching any --exclude are skipped. May be repeated.')
    p.add_argument('--excludes-file', action='append', default=None,
                   help='File of exclude patterns/paths, one per line (or TSV; first column). May be repeated.')
    args = get_args(parser=p)

    includes = list(args.include or [])
    excludes = list(args.exclude or [])
    for fpath in args.excludes_file or []:
        excludes.extend(_load_excludes_file(fpath))

    outf = open_output()

    # Track shelf paths written during this run, keyed by path -> (ExternalSource, SourceFilename),
    # to prevent a second source file in the same run from silently overwriting the first.
    paths_written_this_run = {}

    for input_source in args.inputs:
        try:
            # collect 'sources' metadata
            source_files = {}
            # collect receipts
            receipts = []

            for fn, contents, dt in find_files_with_time(input_source, ext='.tsv'):
                progress(fn)
                for row in parse_tsv_data(contents.decode('utf-8'), "Source"):
                    innerfn = strip_toplevel(row.SourceFilename).replace('\\', '/')
                    if innerfn in source_files:
                        warn("%s: already in source_files!" % innerfn)
                        continue
                    source_files[innerfn] = row

            # enumerate all files in this source, reverse-sorted by time
            #  (so most recent edition gets main slot in case of shelving
            #  conflict); filename is a tiebreaker so the winner is stable
            #  across runs even when mtimes are equal.
            for fn, contents, dt in sorted(find_files_with_time(input_source, strip_toplevel=False), reverse=True, key=lambda x: (x[2], x[0])):
                if fn.endswith(".tsv") or fn.endswith(".log"):
                    continue

                if not contents:  # 0-length files
                    continue

                innerfn = strip_toplevel(fn).replace('\\', '/')

                if not _accept_path(innerfn, includes, excludes):
                    debug("filter excluded: %s" % innerfn)
                    continue

                if innerfn in source_files:
                    srcrow = source_files[innerfn]
                    CaptureTime = srcrow.DownloadTime
                    ExternalSource = args.extsrc or srcrow.ExternalSource
                    SourceFilename = innerfn
                else:
                    debug("%s not in sources.tsv" % innerfn)
                    CaptureTime = iso8601(dt)
                    ExternalSource = args.extsrc or parse_pathname(input_source).filename
                    SourceFilename = innerfn

                ReceivedTime = iso8601(time.time())
                InternalSource = args.intsrc or parse_pathname(input_source).filename

                already_received = metadb.check_already_received(ExternalSource, SourceFilename)
                xdid = ""
                prev_xdid = ""  # unshelved by default

                # The latest receipt for this (ExternalSource, SourceFilename) is authoritative:
                # it reflects the most recent xdid (handles shelf-relocations) or '' if the
                # latest attempt failed to shelve.
                if already_received:
                    latest = max(already_received, key=lambda r: r.ReceivedTime)
                    prev_xdid = latest.xdid
                    if prev_xdid:
                        debug('already shelved as %s' % prev_xdid)

                # Default: skip files that have a successful, non-provisional prior shelving.
                # Files with empty latest xdid (never successfully shelved) and provisional
                # xdids (shelved into unshelved/) fall through to retry. --reimport reprocesses
                # everything.
                if prev_xdid and not catalog.is_provisional(prev_xdid) and not args.reimport:
                    debug("already shelved as %s, skipping: %s:%s" % (prev_xdid, ExternalSource, SourceFilename))
                    continue

                # try each parser by extension
                ext = parse_pathname(fn).ext.lower()
                possible_parsers = parsers.get(ext, parsers[".puz"])

                progress(fn)

                if ext == ".xd":
                    outf.write_file(fn, contents.decode('utf-8'), dt)
                elif not possible_parsers:
                    rejected = "no parser"
                else:
                    rejected = ""
                    unchanged = False
                    owned_by_other = False
                    for parsefunc in possible_parsers:
                        try:
                            try:
                                xd = parsefunc(contents, fn)
                            except IncompletePuzzleParse as e:
                                error("%s  %s" % (fn, e))
                                xd = e.xd
                            if not xd:
                                continue

                            xd.filename = replace_ext(strip_toplevel(fn), ".xd")
                            if not xd.get_header("Copyright"):
                                if args.copyright:
                                    xd.set_header("Copyright", args.copyright)

                            catalog.deduce_set_seqnum(xd)

                            xdstr = xd.to_unicode()

                            mdtext = "|".join((ExternalSource,InternalSource,SourceFilename))

                            # Manual xdid pin from overrides.tsv takes precedence over all
                            # automatic resolution. Use the pinned xdid for both the receipt
                            # and the shelf path; pubid is derived from the xdid format.
                            override_xdid = catalog.lookup_xdid_override(ExternalSource, SourceFilename)
                            if override_xdid:
                                xdid = override_xdid
                                path = catalog.shelf_path_from_xdid(override_xdid)
                                if not path:
                                    raise xdfile.NoShelfError("override xdid %s is not a recognized shelf format" % override_xdid)
                            else:
                                # Resolve pubid once and pass it down — keeps deduce_xdid and
                                # get_shelf_path consistent and avoids triple-resolution per file.
                                pubid = args.pubid or catalog.resolve_pubid(xd, mdtext)

                                # Strict deduction for the relocation comparison: ignore the
                                # provisional fallback, only flag real-vs-real divergences.
                                deduced_xdid_strict = catalog.deduce_xdid(xd, pubid, mdtext, strict=True)
                                if (args.reimport and prev_xdid and not catalog.is_provisional(prev_xdid)
                                        and deduced_xdid_strict and prev_xdid != deduced_xdid_strict):
                                    warn("shelf relocation: %s previously %s, current headers deduce %s" % (
                                        SourceFilename, prev_xdid, deduced_xdid_strict))
                                # Reuse prev_xdid only when it's a real (non-provisional) shelving
                                # AND current headers still support a real xdid. The latter check
                                # catches "regressions" where prev_xdid was set under different
                                # rules (e.g. a stricter pubregex was relaxed, or a Number heuristic
                                # was tightened) and keeping it would put xdid and path out of sync.
                                is_regression = (prev_xdid and not catalog.is_provisional(prev_xdid)
                                                 and not deduced_xdid_strict)
                                if prev_xdid and not catalog.is_provisional(prev_xdid) and deduced_xdid_strict:
                                    xdid = prev_xdid
                                else:
                                    xdid = catalog.deduce_xdid(xd, pubid, mdtext)
                                path = catalog.get_shelf_path(xd, pubid, mdtext)
                                if not path:
                                    raise xdfile.NoShelfError("no shelf path for %s" % xd.filename)

                                # Single warning per provisional shelving with whichever reason
                                # applies. Suppresses the duplicated/unclear messages that used
                                # to come from get_shelf_path AND the convert loop separately.
                                if catalog.is_provisional(xdid):
                                    if is_regression:
                                        warn("%s: unshelved as %s (was %s)" % (
                                            SourceFilename, xdid, prev_xdid))
                                    elif xdid.startswith(catalog.PROVISIONAL_MARKER):
                                        warn("%s: unshelved as %s (no pubid resolved)" % (
                                            SourceFilename, xdid))
                                    else:
                                        warn("%s: unshelved as %s (no Date or Number)" % (
                                            SourceFilename, xdid))

                            # Always-on ownership guard: refuse to overwrite if a different
                            # (ExternalSource, SourceFilename) already owns this xdid. This
                            # catches both cross-source overwrites and same-source sibling
                            # duplicates (same logical puzzle filed under multiple paths in
                            # the archive). Provisional xdids are hash-unique by construction
                            # and don't need this guard. --overwrite overrides.
                            if not args.overwrite and xdid and not catalog.is_provisional(xdid):
                                latest = metadb.latest_receipt_for_xdid(xdid)
                                if latest and (latest.ExternalSource, latest.SourceFilename) != (ExternalSource, SourceFilename):
                                    warn("xdid %s already owned by (%s, %s); not overwriting from (%s, %s) (use --overwrite to override)" % (
                                        xdid, latest.ExternalSource, latest.SourceFilename, ExternalSource, SourceFilename))
                                    owned_by_other = True
                                    rejected = ""
                                    break

                            # Within-run collision guard: if another source in this run already
                            # wrote this shelf path, skip rather than silently overwrite. Sort
                            # order makes this deterministic — the earliest-processed file
                            # (most recent mtime, filename desc on tie) keeps the slot.
                            own_key = (ExternalSource, SourceFilename)
                            run_owner = paths_written_this_run.get(path)
                            if run_owner and run_owner != own_key:
                                warn("shelf slot %s already written this run by %s; not overwriting with %s" % (
                                    path + ".xd", run_owner[1], SourceFilename))
                                owned_by_other = True
                                rejected = ""
                                break

                            unchanged = False
                            if args.skip_unchanged:
                                try:
                                    full = os.path.join(outf.toplevel, path + ".xd")
                                    if os.path.exists(full):
                                        new_bytes = xdstr.encode('utf-8')
                                        if os.path.getsize(full) == len(new_bytes):
                                            with open(full, 'rb') as f:
                                                unchanged = f.read() == new_bytes
                                except AttributeError:
                                    pass

                            # Claim the slot regardless of whether we actually write, so a later
                            # source in the same run can't sneak in behind a --skip-unchanged no-op.
                            paths_written_this_run[path] = own_key

                            if unchanged:
                                debug("unchanged, skipping: %s" % (path + ".xd"))
                            else:
                                outf.write_file(path + ".xd", xdstr, dt)

                            # Promotion cleanup: a previously-provisional shelving
                            # has been replaced by a real (or different provisional)
                            # one. Remove the old provisional .xd so receipts and
                            # disk stay in sync.
                            if (catalog.is_provisional(prev_xdid)
                                    and prev_xdid != xdid
                                    and not unchanged):
                                try:
                                    old_relpath = catalog.provisional_path(prev_xdid, ExternalSource) + ".xd"
                                    full_old = os.path.join(outf.toplevel, old_relpath)
                                    if os.path.exists(full_old):
                                        os.unlink(full_old)
                                        debug("promoted: removed old provisional %s" % old_relpath)
                                except AttributeError:
                                    pass

                            rejected = ""
                            break  # stop after first successful parsing
                        except xdfile.NoShelfError as e:
                            error("could not shelve: %s" % str(e))
                            rejected += "[shelver] %s  " % str(e)
                        except Exception as e:
                            error("%s could not convert [%s]: %s" % (parsefunc.__name__, fn, str(e)))
                            rejected += "[%s] %s  " % (parsefunc.__name__, str(e))
                            # raise

                    if rejected:
                        error("could not convert: %s" % rejected)

                    # Receipt policy: append when the xdid we just assigned is non-empty AND
                    # represents a state change from the latest prior receipt. This covers:
                    #   - brand-new sources (no prior receipt)
                    #   - retries that succeeded (prior xdid empty, new xdid assigned)
                    #   - provisional-to-real promotions (prior xdid was provisional, new is real)
                    # Skips when: parse failed (empty xdid), the xdid is unchanged from latest
                    # (no new info), the slot is owned by another key, or write was a no-op.
                    if not xdid:
                        debug("no xdid (parse failed), receipt skip %s:%s" % (ExternalSource, SourceFilename))
                    elif owned_by_other:
                        debug("slot owned, receipt skip %s:%s" % (ExternalSource, SourceFilename))
                    elif unchanged:
                        debug("unchanged receipt skip %s:%s" % (ExternalSource, SourceFilename))
                    elif already_received and prev_xdid == xdid:
                        debug("xdid unchanged from latest receipt, skip %s:%s" % (ExternalSource, SourceFilename))
                    else:
                        receipts.append([
                            CaptureTime,
                            ReceivedTime,
                            ExternalSource,
                            InternalSource,
                            SourceFilename,
                            xdid
                        ])

            for r in receipts:
                metadb.append_row('gxd/receipts', r)

        except Exception as e:
            error(str(e))
            if args.debug:
                raise


if __name__ == "__main__":
    main()
