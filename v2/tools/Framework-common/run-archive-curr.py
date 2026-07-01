#!/usr/bin/env python3
"""run-archive-curr.py — Game-<game> data-area housekeeping: keep the CURR marker on ONLY the newest run.

Invoked as STEP 1 by Framework-Logtriage/run-logtriage (KIND = log-CURR) and Framework-SaveParse/run-saveparse
(KIND = save-CURR); also runnable standalone. Strips the CURR marker from every EXISTING `<kind>*` dir under
Game-<game>/  (log-CURR -> log-<mtime>, log-CURR-<label> -> log-<label>), so that AFTER the master then creates a
fresh `<kind>/` the newest run is the SOLE folder bearing CURR — the marker the report/unit-test layer uses to
find the latest correct data source. Idempotent; a no-op when no CURR dir exists.  Arg1 = KIND (log-CURR | save-CURR).

Lives in Framework-common beside run-scrub (both are game-agnostic housekeeping of the Game-<game> DATA area).
Game-<game>/ holds ONLY gitignored per-run DATA — no code/config there — so this script also CREATES the
Game-<game> data root if it does not yet exist (fresh clone / after scrub), which is why the masters call it
as their first step."""
import os
import sys
import glob
import time
HERE = os.path.dirname(os.path.abspath(__file__))   # Framework-common (this script's home; lib_paths is a sibling)
sys.path.insert(0, HERE)
import lib_paths

VALID = ("log-CURR", "save-CURR")


def _unique(path):
    """A non-colliding destination path (append _1, _2, ... if needed)."""
    if not os.path.exists(path):
        return path
    i = 1
    while os.path.exists(f"{path}_{i}"):
        i += 1
    return f"{path}_{i}"


def archive_curr(kind):
    """Rename every Game-<game>/<kind>* dir to DROP the CURR marker (the newest-only-CURR invariant)."""
    root = lib_paths.GAME_ROOT
    os.makedirs(root, exist_ok=True)                      # Game-<game>/ is a gitignored data sink — create if missing
    prefix = kind.split("-CURR", 1)[0]                    # 'log' / 'save'
    n = 0
    for d in sorted(glob.glob(os.path.join(root, kind + "*"))):
        if not os.path.isdir(d):
            continue
        suffix = os.path.basename(d)[len(kind):]          # '' (bare) or '-<label>'
        label = suffix[1:] if suffix.startswith("-") else suffix
        if not label:                                     # bare '<kind>' -> synthesize a label from its mtime
            label = time.strftime("%Y%m%d%H%M", time.localtime(os.path.getmtime(d)))
        dest = _unique(os.path.join(root, f"{prefix}-{label}"))
        os.rename(d, dest)
        print(f"  archived {os.path.basename(d)} -> {os.path.basename(dest)}")
        n += 1
    print(f"archive-curr {kind}: demoted {n} prior dir(s)")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in VALID:
        sys.exit(f"usage: run-archive-curr.py <{' | '.join(VALID)}>")
    archive_curr(sys.argv[1])


if __name__ == "__main__":
    main()
