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
from xdfile.utils import parse_pubid

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


_DRYRUN_HEADER = '\t'.join((
    'status', 'pubid', 'xdid', 'shelf_path', 'prev_xdid',
    'ExternalSource', 'SourceFilename', 'Title', 'Author',
))


def _safe_parse_pubid(xdid):
    """parse_pubid raises AttributeError on unparseable input; never propagate."""
    try:
        return parse_pubid(xdid or '') or ''
    except AttributeError:
        return ''


def _emit_dryrun(args, status, pubid, xdid, path, prev_xdid,
                 ExternalSource, SourceFilename, xd=None):
    if not args.dry_run:
        return
    title = xd.get_header('Title') if xd is not None else ''
    author = xd.get_header('Author') if xd is not None else ''
    def _clean(s):
        return (s or '').replace('\t', ' ').replace('\n', ' ')
    print('\t'.join(_clean(s) for s in (
        status, pubid, xdid, path, prev_xdid,
        ExternalSource, SourceFilename, title, author,
    )))


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
    p.add_argument('--skip-unchanged', action='store_true', help='Skip writing .xd if output is byte-identical to the existing file. Receipt rows are still appended (use receipts.tsv as the source of truth for which SourceFilenames map to which xdid).')
    p.add_argument('--reimport', action='store_true', help='Re-parse and rewrite .xd for sources that have already been received (e.g. to pick up parser or decoder fixes).')
    p.add_argument('--conflict-mode', choices=['skip', 'rename', 'replace', 'overwrite'], default='skip',
                   help='How to handle a SourceFilename whose canonical xdid is already claimed by '
                        'a different SourceFilename (per receipts.tsv) AND whose converted .xd '
                        'differs from the canonical slot. '
                        '"skip" (default): warn and drop the loser. '
                        '"rename": mint a stable variant xdid (e.g. nys2007-03-27a) and shelve '
                        'the loser there. '
                        '"replace": newcomer becomes canonical; the prior claimant is demoted '
                        'to a variant (their content is moved to the variant path and a demotion '
                        'receipt is appended). '
                        '"overwrite": newcomer becomes canonical and writes over the prior content; '
                        'both source files end up mapped to the same xdid in receipts (history '
                        'preserved, but the prior content is lost from disk). '
                        'Equal-bytes "collisions" are never treated as conflicts in any mode: the '
                        'loser silently records a provenance receipt for the canonical xdid. '
                        'Caveat: with --include/--exclude filters, an unprocessed sibling can '
                        'silently go stale relative to a reimported canonical slot — no detection.')
    p.add_argument('--include', action='append', default=None,
                   help='Glob (fnmatch) pattern; only SourceFilenames matching at least one --include are processed. May be repeated.')
    p.add_argument('--exclude', action='append', default=None,
                   help='Glob (fnmatch) pattern; SourceFilenames matching any --exclude are skipped. May be repeated.')
    p.add_argument('--excludes-file', action='append', default=None,
                   help='File of exclude patterns/paths, one per line (or TSV; first column). May be repeated.')
    p.add_argument('-n', '--dry-run', action='store_true',
                   help='Run all parse/deduce/conflict logic but skip every disk write '
                        '(no .xd output, no receipts.tsv append, no provisional cleanup). '
                        'Prints a TSV line per processed file to stdout.')
    p.add_argument('--filter-pubid', default=None,
                   help='Comma-separated pubids; only process files whose computed pubid '
                        'matches one of these (case-insensitive). Applies after parse.')
    args = get_args(parser=p)

    includes = list(args.include or [])
    excludes = list(args.exclude or [])
    for fpath in args.excludes_file or []:
        excludes.extend(_load_excludes_file(fpath))

    filter_pubids = None
    if args.filter_pubid:
        filter_pubids = {p.strip().lower() for p in args.filter_pubid.split(',') if p.strip()}

    if args.dry_run:
        print(_DRYRUN_HEADER)

    outf = open_output()

    # Track shelf paths written during this run, keyed by path -> (ExternalSource, SourceFilename),
    # to identify the within-run canonical claimant when receipts have no prior claim.
    paths_written_this_run = {}
    # Variant xdids minted during this run, so a second collision in the same run
    # doesn't try to mint the same letter as the first.
    variants_minted_this_run = set()

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
                    if args.dry_run:
                        prev_pubid = _safe_parse_pubid(prev_xdid)
                        if not filter_pubids or prev_pubid.lower() in filter_pubids:
                            _emit_dryrun(args, 'SKIPPED_RECEIVED', prev_pubid, '', '',
                                         prev_xdid, ExternalSource, SourceFilename)
                    continue

                # try each parser by extension
                ext = parse_pathname(fn).ext.lower()
                possible_parsers = parsers.get(ext, parsers[".puz"])

                progress(fn)

                if ext == ".xd":
                    if not args.dry_run:
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

                            # Resolve pubid up front so --filter-pubid can gate both override
                            # and non-override paths. Same value gets passed down to
                            # deduce_xdid / get_shelf_path so resolution stays consistent.
                            if override_xdid:
                                pubid = _safe_parse_pubid(override_xdid)
                            else:
                                pubid = args.pubid or catalog.resolve_pubid(xd, mdtext)

                            if filter_pubids and (pubid or '').lower() not in filter_pubids:
                                debug("filter excluded pubid %r: %s" % (pubid, SourceFilename))
                                # xdid stays empty -> receipt-append branch is a no-op
                                break

                            if override_xdid:
                                xdid = override_xdid
                                path = catalog.shelf_path_from_xdid(override_xdid)
                                if not path:
                                    raise xdfile.NoShelfError("override xdid %s is not a recognized shelf format" % override_xdid)
                            else:
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

                            # Canonical-claimant resolution. Latest-receipt-per-xdid is the
                            # current claimant: receipts are append-only and every state
                            # change writes a new row, so the most-recent receipt mapping
                            # a SourceFilename to xdid is the live canonical claim. When
                            # no prior receipt exists for xdid, the first writer this run
                            # becomes canonical. Provisional xdids are hash-unique by
                            # construction and skip this entire decision.
                            own_key = (ExternalSource, SourceFilename)
                            am_canonical = True
                            canonical_owner_label = None
                            if xdid and not catalog.is_provisional(xdid):
                                run_owner = paths_written_this_run.get(path)
                                if run_owner and run_owner != own_key:
                                    am_canonical = False
                                    canonical_owner_label = run_owner
                                else:
                                    latest = metadb.latest_receipt_for_xdid(xdid)
                                    if (latest
                                            and (latest.ExternalSource, latest.SourceFilename) != own_key):
                                        am_canonical = False
                                        canonical_owner_label = (latest.ExternalSource, latest.SourceFilename)

                            is_equal_provenance = False
                            conflict_status = None  # set by the conflict branches below
                            if not am_canonical:
                                # Compare loser's converted bytes to the canonical-slot bytes.
                                # Equal -> silent provenance receipt; different -> dispatch
                                # on --conflict-mode.
                                full_canonical = os.path.join(outf.toplevel, path + ".xd")
                                try:
                                    with open(full_canonical, 'rb') as f:
                                        canonical_bytes = f.read()
                                except (FileNotFoundError, OSError):
                                    canonical_bytes = None
                                new_bytes = xdstr.encode('utf-8')

                                if canonical_bytes == new_bytes:
                                    is_equal_provenance = True
                                    debug("equal-bytes provenance for %s from (%s, %s); claimed by (%s, %s)" % (
                                        xdid, ExternalSource, SourceFilename,
                                        canonical_owner_label[0], canonical_owner_label[1]))
                                elif args.conflict_mode == 'rename':
                                    variant = catalog.mint_variant_xdid(
                                        xdid, ExternalSource, SourceFilename,
                                        in_run_claimed=variants_minted_this_run)
                                    if not variant:
                                        warn("xdid %s claimed by (%s, %s); could not mint variant for (%s, %s) (all letter slots used)" % (
                                            xdid, canonical_owner_label[0], canonical_owner_label[1],
                                            ExternalSource, SourceFilename))
                                        _emit_dryrun(args, 'OWNED', pubid or '', xdid, path, prev_xdid,
                                                     ExternalSource, SourceFilename, xd=xd)
                                        owned_by_other = True
                                        rejected = ""
                                        break
                                    warn("xdid %s claimed by (%s, %s); forking (%s, %s) to variant %s" % (
                                        xdid, canonical_owner_label[0], canonical_owner_label[1],
                                        ExternalSource, SourceFilename, variant))
                                    xdid = variant
                                    path = catalog.shelf_path_from_xdid(variant)
                                    if not path:
                                        raise xdfile.NoShelfError("variant xdid %s has no shelf path" % variant)
                                    variants_minted_this_run.add(variant)
                                    am_canonical = True
                                    canonical_owner_label = None
                                    conflict_status = 'RENAMED'
                                elif args.conflict_mode == 'replace':
                                    # Demote the prior canonical claimant to a variant: write
                                    # their disk bytes to a freshly-minted variant path and
                                    # append a demotion receipt for them. Newcomer then takes
                                    # the canonical write path normally.
                                    old_extsrc, old_sourcefilename = canonical_owner_label
                                    variant = catalog.mint_variant_xdid(
                                        xdid, old_extsrc, old_sourcefilename,
                                        in_run_claimed=variants_minted_this_run)
                                    if not variant:
                                        warn("xdid %s claimed by (%s, %s); cannot displace (no variant slots left); dropping (%s, %s)" % (
                                            xdid, old_extsrc, old_sourcefilename,
                                            ExternalSource, SourceFilename))
                                        _emit_dryrun(args, 'OWNED', pubid or '', xdid, path, prev_xdid,
                                                     ExternalSource, SourceFilename, xd=xd)
                                        owned_by_other = True
                                        rejected = ""
                                        break
                                    variant_path = catalog.shelf_path_from_xdid(variant)
                                    if not variant_path:
                                        raise xdfile.NoShelfError("variant xdid %s has no shelf path" % variant)
                                    warn("xdid %s claimed by (%s, %s); demoting them to %s, (%s, %s) becomes canonical" % (
                                        xdid, old_extsrc, old_sourcefilename, variant,
                                        ExternalSource, SourceFilename))
                                    if canonical_bytes is not None:
                                        if not args.dry_run:
                                            outf.write_file(variant_path + ".xd",
                                                            canonical_bytes.decode('utf-8'), dt)
                                    else:
                                        warn("canonical .xd missing on disk for %s; demotion receipt only, %s.xd will materialize on next reimport of (%s, %s)" % (
                                            xdid, variant_path, old_extsrc, old_sourcefilename))
                                    # Carry over CaptureTime/InternalSource from the demotee's
                                    # latest prior receipt — the demotion is about state, not
                                    # about reingesting the upstream file.
                                    old_prior = metadb.check_already_received(old_extsrc, old_sourcefilename)
                                    if old_prior:
                                        prior_latest = max(old_prior, key=lambda r: r.ReceivedTime)
                                        old_capture = prior_latest.CaptureTime
                                        old_internal = prior_latest.InternalSource
                                    else:
                                        old_capture = ""
                                        old_internal = ""
                                    receipts.append([
                                        old_capture,
                                        ReceivedTime,
                                        old_extsrc,
                                        old_internal,
                                        old_sourcefilename,
                                        variant,
                                    ])
                                    variants_minted_this_run.add(variant)
                                    paths_written_this_run[variant_path] = (old_extsrc, old_sourcefilename)
                                    am_canonical = True
                                    canonical_owner_label = None
                                    conflict_status = 'REPLACED'
                                elif args.conflict_mode == 'overwrite':
                                    # Newcomer's bytes replace the canonical-slot bytes.
                                    # Both source files remain mapped to xdid in receipts;
                                    # the prior claimant's disk content is lost (their
                                    # original receipt still records the historical claim).
                                    warn("xdid %s claimed by (%s, %s); overwriting canonical content with bytes from (%s, %s) (prior content lost)" % (
                                        xdid, canonical_owner_label[0], canonical_owner_label[1],
                                        ExternalSource, SourceFilename))
                                    am_canonical = True
                                    canonical_owner_label = None
                                    conflict_status = 'OVERWRITE'
                                else:
                                    # conflict_mode == 'skip' (default): warn and drop the loser.
                                    warn("xdid %s claimed by (%s, %s); not writing (%s, %s) (use --conflict-mode=rename/replace/overwrite to keep the new content)" % (
                                        xdid, canonical_owner_label[0], canonical_owner_label[1],
                                        ExternalSource, SourceFilename))
                                    _emit_dryrun(args, 'OWNED', pubid or '', xdid, path, prev_xdid,
                                                 ExternalSource, SourceFilename, xd=xd)
                                    owned_by_other = True
                                    rejected = ""
                                    break

                            # Bytes-equal optimization. --skip-unchanged checks the canonical
                            # write path. is_equal_provenance is always a no-op write (we know
                            # bytes match by definition).
                            unchanged = is_equal_provenance
                            if args.skip_unchanged and not is_equal_provenance:
                                try:
                                    full = os.path.join(outf.toplevel, path + ".xd")
                                    if os.path.exists(full):
                                        new_bytes = xdstr.encode('utf-8')
                                        if os.path.getsize(full) == len(new_bytes):
                                            with open(full, 'rb') as f:
                                                unchanged = f.read() == new_bytes
                                except AttributeError:
                                    pass

                            # Claim the slot for canonical writers (and freshly-renamed
                            # variants, which start their own claim). Equal-bytes provenance
                            # writers don't displace the canonical claim — they just record
                            # an additional receipt.
                            if not is_equal_provenance:
                                paths_written_this_run[path] = own_key

                            # Status precedence for dry-run reporting:
                            # equal-bytes provenance > conflict outcome > unchanged > write
                            if is_equal_provenance:
                                status = 'EQUAL_BYTES'
                            elif conflict_status:
                                status = conflict_status
                            elif unchanged:
                                status = 'UNCHANGED'
                            else:
                                status = 'WRITE'
                            _emit_dryrun(args, status, pubid or '', xdid, path, prev_xdid,
                                         ExternalSource, SourceFilename, xd=xd)

                            if unchanged:
                                debug("unchanged, skipping: %s" % (path + ".xd"))
                            elif not args.dry_run:
                                outf.write_file(path + ".xd", xdstr, dt)

                            # Promotion cleanup: a previously-provisional shelving
                            # has been replaced by a real (or different provisional)
                            # one. Remove the old provisional .xd so receipts and
                            # disk stay in sync.
                            if (catalog.is_provisional(prev_xdid)
                                    and prev_xdid != xdid
                                    and not unchanged
                                    and not args.dry_run):
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
                    #   - new provenance: this SourceFilename now also resolves to xdid that a
                    #     different SourceFilename had already claimed (byte-identical conversion)
                    # Skips when: parse failed (empty xdid), the slot was claimed by a divergent
                    # SourceFilename and we dropped (skip mode), or the latest receipt for this
                    # SourceFilename already maps to this same xdid (no new info).
                    if not xdid:
                        debug("no xdid (parse failed), receipt skip %s:%s" % (ExternalSource, SourceFilename))
                    elif owned_by_other:
                        debug("slot claimed by another, receipt skip %s:%s" % (ExternalSource, SourceFilename))
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

            if not args.dry_run:
                for r in receipts:
                    metadb.append_row('gxd/receipts', r)

        except Exception as e:
            error(str(e))
            if args.debug:
                raise


if __name__ == "__main__":
    main()
