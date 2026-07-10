#!/usr/bin/env python3
"""chk-toggle-scopes.py (ss3) — STATIC check on ONE file: brace balance + no CONFIG'd-scope opener left active
but empty-except-limit (the empty-scope the toggle collapse is meant to handle). The safety net ss2 runs after
every toggle. Exit 0 = clean, 1 = problems printed. Executable check (chk-* form, NOT pytest).
Usage: python chk-toggle-scopes.py <file.txt>"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_toggle


def main():
    if len(sys.argv) != 2 or not os.path.isfile(sys.argv[1]):
        sys.exit("usage: chk-toggle-scopes.py <file.txt>")
    cfg = lib_toggle.config(HERE)
    problems = lib_toggle.check_scopes(lib_toggle.read_lines(sys.argv[1]), cfg)
    for p in problems:
        print(f"  FAIL {p}")
    if problems:
        sys.exit(f"chk-toggle-scopes: {len(problems)} problem(s) in {sys.argv[1]}")
    print(f"chk-toggle-scopes: OK (balanced, no empty scope) — {sys.argv[1]}")


if __name__ == "__main__":
    main()
