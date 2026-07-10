#!/usr/bin/env python3
"""run-toggle-file.py (ss2) — comment (--off) / uncomment (--on) the marker + marker-only-scope lines of ONE
file, BOM + line endings preserved. Marker toggle + empty-scope collapse come from lib_toggle (the ss1 finder
+ collapse); after toggling it runs the ss3 scope check as a safety net. DRY-RUN by default; --commit writes.
Usage: python run-toggle-file.py (--on|--off) [--commit] <file.txt>"""
import os
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_toggle


def toggle_one(path, on, commit, cfg):
    """Toggle ONE file; write when commit. Returns total lines changed (0 if none / not a target extension)."""
    n, marker_n, scope_n, text = lib_toggle.toggle_file(path, on, cfg)
    if not n:
        return 0
    print(f"  {'EDIT' if commit else 'would edit'} {n:3d} line(s) ({marker_n} marker + {scope_n} scope)  {path}")
    if commit:
        lib_toggle.write_file(path, text)
        problems = lib_toggle.check_scopes(lib_toggle.read_lines(path), cfg)
    else:
        problems = lib_toggle.check_scopes(text.splitlines(keepends=True), cfg)
    for p in problems:
        print(f"    !! scope-check {p}")
    return n


def main():
    p = argparse.ArgumentParser(description="Toggle debug/fingerprint markers in ONE file.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--on", action="store_true", help="UNCOMMENT (enable) the markers")
    g.add_argument("--off", action="store_true", help="COMMENT (disable) the markers")
    p.add_argument("--commit", action="store_true", help="write the file (default = dry-run)")
    p.add_argument("file", help="the .txt file to toggle")
    a = p.parse_args()
    if not os.path.isfile(a.file):
        sys.exit(f"run-toggle-file: not a file: {a.file}")
    n = toggle_one(a.file, a.on, a.commit, lib_toggle.config(HERE))
    print(f"toggle-file {'ON' if a.on else 'OFF'} {'(COMMIT)' if a.commit else '(dry-run)'}: {n} line(s)"
          + ("" if a.commit else "  — pass --commit to apply"))


if __name__ == "__main__":
    main()
