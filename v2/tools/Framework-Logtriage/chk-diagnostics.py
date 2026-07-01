#!/usr/bin/env python3
"""chk-diagnostics.py — STATIC self-test of the diagnostics evaluator (chk- class; run `python chk-diagnostics.py`,
NOT via pytest). DATA-DRIVEN: reads diag_snippets.example.csv (condition, metrics, expected, sample_snippet) and
asserts lib_diag.evaluate(condition, metrics) == expected. Exits non-zero on any failure. Proves the conditions in
diag_literals eval TRUE/FALSE correctly before the engine touches real runs. No literals in code — cases ARE the CSV."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
sys.path.insert(0, HERE)   # lib_diag is a sibling in this framework
import lib_io
import lib_diag


def _metrics(s):
    out = {}
    for kv in (s or "").split(";"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def main():
    rows = lib_io.read_csv_dicts(os.path.join(HERE, "diag_snippets.example.csv"))
    fails = 0
    for r in rows:
        got = lib_diag.evaluate(r["condition"], _metrics(r["metrics"]))
        want = r["expected"].strip().lower() in ("true", "1", "yes")
        ok = (got == want)
        fails += (not ok)
        print(f"  {'ok  ' if ok else 'FAIL'} {r['id']}: evaluate('{r['condition']}', {{{r['metrics']}}}) = {got} (want {want})")
    print(f"chk-diagnostics: {len(rows) - fails}/{len(rows)} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
