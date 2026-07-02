#!/usr/bin/env python3
"""gen-diag-md.py — Logtriage Set-3 renderer: <target>/metrics.csv + diag_fired.csv -> <target>/diagnostics.md
via lib_diag.render_md. EVERY human-readable finding string comes from the diag_literals rows (NO-LITERALS);
this script only structures them. TARGET (arg1) = a MOD_NAME or `_global`. Standalone; run-log-diag invokes."""
import os
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
sys.path.insert(0, HERE)
import lib_io, lib_paths, lib_config, lib_diag

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "log-CURR")


def main():
    p = argparse.ArgumentParser(description="Set3: render diagnostics.md from metrics + fired rules.")
    p.add_argument("target", metavar="TARGET", help="MOD_NAME or _global (a subdir of log-CURR/)")
    a = p.parse_args()
    tdir = os.path.join(ROOT, a.target)
    _h, mrows = lib_io.read_csv(os.path.join(tdir, CFG["outputs"]["metrics"]))
    if _h is None:
        sys.exit(f"gen-diag-md: no metrics.csv for {a.target} — run ext-diag-eval's upstream first")
    fired = lib_io.read_csv_dicts(os.path.join(tdir, CFG["outputs"]["fired"]))
    out = os.path.join(tdir, CFG["outputs"]["report"])
    md = lib_diag.render_md(f"{a.target} (logs)", {k: v for k, v in mrows}, fired)
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(md)
    print(f"  [diag-md] {out} ({len(fired)} findings)")


if __name__ == "__main__":
    main()
