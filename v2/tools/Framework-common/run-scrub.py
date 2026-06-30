#!/usr/bin/env python3
"""run-scrub.py — MASTER cleanup: wipe ALL generated framework DATA under Game-<game>/ (data-*, log-CURR* /
log-*, save-CURR* / save-*), leaving CODE + the tracked configs (config_*.toml) + benign.csv. DRY-RUN by
default; --commit actually deletes; --mod M scopes to one mod's outputs. Configs never match the data globs,
so they are always safe."""
import os
import sys
import glob
import shutil
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_paths

PATTERNS = ["data-{m}", "log-CURR*/{m}", "save-CURR*/{m}", "log-*/{m}", "save-*/{m}"]
ALL_PATTERNS = ["data-*", "log-CURR*", "save-CURR*", "log-*", "save-*"]


def main():
    p = argparse.ArgumentParser(description="Scrub generated framework data (dry-run unless --commit).")
    p.add_argument("--commit", action="store_true", help="actually delete (default = dry-run)")
    p.add_argument("--mod", default=None, help="scope to one mod's outputs (else all)")
    a = p.parse_args()
    root = lib_paths.GAME_ROOT
    pats = [pat.format(m=a.mod) for pat in PATTERNS] if a.mod else ALL_PATTERNS
    targets = sorted({os.path.normpath(t) for pat in pats
                      for t in glob.glob(os.path.join(root, pat)) if os.path.isdir(t)})
    if not targets:
        print("scrub: nothing to remove.")
        return
    print(f"scrub {'(COMMIT)' if a.commit else '(dry-run)'} — {len(targets)} dir(s) under {root}:")
    for t in targets:
        print(f"  {'DELETED' if a.commit else 'would delete'}  {os.path.relpath(t, root)}")
        if a.commit:
            shutil.rmtree(t, ignore_errors=True)
    if not a.commit:
        print("  (dry-run; pass --commit to actually delete)")


if __name__ == "__main__":
    main()
