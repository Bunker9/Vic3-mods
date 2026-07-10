#!/usr/bin/env python3
"""ext-toggle-markers.py (ss1) — find debug_log(_scopes) / _fingerprint_ marker lines in ONE file and print
their locations (commented or not). Read-only; the finder primitive the toggle + check stages build on.
Usage: python ext-toggle-markers.py <file.txt>"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_toggle


def main():
    if len(sys.argv) != 2 or not os.path.isfile(sys.argv[1]):
        sys.exit("usage: ext-toggle-markers.py <file.txt>")
    cfg = lib_toggle.config(HERE)
    hits = lib_toggle.find_markers(lib_toggle.read_lines(sys.argv[1]), cfg)
    for lineno, text in hits:
        print(f"  {lineno:5d}: {text}")
    print(f"ext-toggle-markers: {len(hits)} marker line(s) in {sys.argv[1]}")


if __name__ == "__main__":
    main()
