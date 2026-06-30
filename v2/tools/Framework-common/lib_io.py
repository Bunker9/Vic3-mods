#!/usr/bin/env python3
"""lib_io — deterministic text/CSV IO for THE debug framework. No paths/literals (see lib_paths)."""
import os
import csv


def read_text_lines(path):
    """Read a text file as BOM-stripped, decode-robust lines."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read().splitlines()


def walk_files(root, exts):
    """Sorted [(rel_path, abs_path, basename)] for every file under root whose ext is in exts.
    rel_path uses forward slashes (stable across OS); deterministic order (idempotent data-<Mod>)."""
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if os.path.splitext(fn)[1].lower() in exts:
                ap = os.path.join(dirpath, fn)
                out.append((os.path.relpath(ap, root).replace("\\", "/"), ap, fn))
    return sorted(out, key=lambda t: t[0])


def write_csv(path, header, rows, sort=False):
    """Write a CSV. sort=True => rows sorted stringwise for IDEMPOTENT output (the data-<Mod> contract,
    vision §A): same source ⇒ byte-identical file regardless of when run. Never writes timestamps."""
    rows = list(rows)
    if sort:
        rows = sorted(rows, key=lambda r: [str(c) for c in r])
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def read_csv(path):
    """Return (header, rows) or (None, []) if absent/empty."""
    if not os.path.exists(path):
        return None, []
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = list(csv.reader(f))
    return (r[0], r[1:]) if r else (None, [])


def read_csv_dicts(path):
    """Return list[dict] keyed by header (convenience for downstream joins). [] if absent."""
    header, rows = read_csv(path)
    if header is None:
        return []
    return [dict(zip(header, r)) for r in rows]
