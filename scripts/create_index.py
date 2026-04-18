#!/usr/bin/env python3
"""Enumerate xd files and output TSV of filename, dimensions, 1A/1D, and grid."""

import argparse
import hashlib
import io
import os
import signal
import sys
import tarfile
import zipfile


def parse_xd_minimal(contents):
    """Fast minimal parse: extract grid and 1A/1D. Stops reading as early as possible."""
    grid_rows = []
    answer_1a = ""
    answer_1d = ""
    section = 0
    blank_run = 2  # start high to trigger first section

    for line in contents.splitlines():
        stripped = line.strip()
        if not stripped:
            blank_run += 1
            continue

        if blank_run >= 2:
            section += 1
            blank_run = 0
        else:
            blank_run = 0

        if section == 2:
            grid_rows.append(stripped)
        elif section == 3:
            idx = stripped.find(".")
            if idx > 0:
                pos = stripped[:idx].strip()
                if pos in ("A1", "D1"):
                    ans_idx = stripped.rfind("~")
                    answer = stripped[ans_idx + 1:].strip() if ans_idx > 0 else ""
                    if pos == "A1":
                        answer_1a = answer
                    else:
                        answer_1d = answer
                    if answer_1a and answer_1d:
                        break
                elif pos > "D1":
                    break  # past D1, stop looking
        elif section > 3:
            break

    width = len(grid_rows[0]) if grid_rows else 0
    height = len(grid_rows)
    grid_flat = "".join(grid_rows)
    return grid_flat, width, height, answer_1a, answer_1d


def iter_tar(path):
    """Yield (name, contents_str) for every .xd member in a tar archive."""
    with tarfile.open(path, "r:*") as tf:
        for member in tf:
            if member.isfile() and member.name.endswith(".xd"):
                try:
                    f = tf.extractfile(member)
                    if f:
                        yield member.name, f.read().decode("utf-8", errors="replace")
                except Exception:
                    pass


def iter_directory(path):
    """Yield (filepath, contents_str) for every .xd file under path."""
    stack = [path]
    while stack:
        top = stack.pop()
        try:
            with os.scandir(top) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif entry.name.endswith(".xd"):
                        try:
                            with open(entry.path, "r", encoding="utf-8", errors="replace") as f:
                                yield entry.path, f.read()
                        except Exception:
                            pass
                    elif entry.name.endswith(".zip"):
                        try:
                            with zipfile.ZipFile(entry.path, "r") as zf:
                                for name in zf.namelist():
                                    if name.endswith(".xd"):
                                        try:
                                            data = zf.read(name)
                                            yield f"{entry.path}:{name}", data.decode("utf-8", errors="replace")
                                        except Exception:
                                            pass
                        except Exception:
                            pass
        except PermissionError:
            pass


def main():
    parser = argparse.ArgumentParser(description="Enumerate xd files and output grid TSV")
    parser.add_argument("path", help="Path to gxd directory or .tar/.tar.gz archive")
    parser.add_argument("--hash", action="store_true", help="Include MD5 hash of grid")
    parser.add_argument("--full-grid", action="store_true", help="Include full grid text")
    parser.add_argument("--dimensions", action="store_true", help="Include width and height columns")
    args = parser.parse_args()

    out = io.BufferedWriter(sys.stdout.buffer, buffer_size=1 << 16)
    cols = ["xdid", "1A", "1D"]
    if args.dimensions:
        cols += ["width", "height"]
    if args.full_grid:
        cols.append("grid")
    if args.hash:
        cols.append("hash")
    out.write(("\t".join(cols) + "\n").encode())

    count = 0
    warnings = 0
    warn_lines = []

    if os.path.isfile(args.path) and tarfile.is_tarfile(args.path):
        source = iter_tar(args.path)
    else:
        source = iter_directory(args.path)

    for filename, contents in source:
        xdid = os.path.splitext(os.path.basename(filename))[0]
        try:
            grid_flat, w, h, a1a, a1d = parse_xd_minimal(contents)
        except Exception as e:
            warn_lines.append(f"WARNING: {filename}: {e}")
            warnings += 1
            out.write((xdid + "\t" * (len(cols) - 1) + "\n").encode())
            count += 1
            continue

        if not grid_flat:
            warn_lines.append(f"WARNING: {filename}: no grid found")
            warnings += 1
            out.write((xdid + "\t" * (len(cols) - 1) + "\n").encode())
            count += 1
            continue

        count += 1
        if count % 1000 == 0:
            sys.stderr.write(f"\r{count} files ({warnings} warnings)...")
            sys.stderr.flush()

        fields = [xdid, a1a, a1d]
        if args.dimensions:
            fields += [str(w), str(h)]
        if args.full_grid:
            fields.append(grid_flat)
        if args.hash:
            fields.append(hashlib.md5(grid_flat.encode("utf-8")).hexdigest())
        out.write(("\t".join(fields) + "\n").encode())

    out.flush()
    sys.stderr.write(f"\r{count} files ({warnings} warnings).   \n")
    for w in warn_lines:
        sys.stderr.write(w + "\n")


if __name__ == "__main__":
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except AttributeError:
        pass
    try:
        main()
    except (BrokenPipeError, OSError):
        sys.stderr.close()
        sys.exit(0)
