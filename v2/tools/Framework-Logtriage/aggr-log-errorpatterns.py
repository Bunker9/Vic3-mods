#!/usr/bin/env python3
"""aggr-log-errorpatterns.py — Logtriage Set-1 aggregator: group the COMMON log-CURR/raw_errors.csv by normalized
signature -> log-CURR/_global/error_patterns.csv (signature, count, example) most-common first. Dep-free grouping
via lib_parse.normalize_error (masks files/quotes/numbers); a fuller template-miner (drain3) is an OPTIONAL future
dep, not used by default. The curated append-only rule-out list is the smoke_detector (separate). Standalone;
run-log-sort invokes it."""
import os
import sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "log-CURR")


def main():
    _h, rows = lib_io.read_csv(os.path.join(ROOT, CFG["outputs"]["raw_errors"]))
    counts, example = Counter(), {}
    for r in rows:                                     # log_file, line_no, severity, raw_text, signature
        sig = r[4]
        counts[sig] += 1
        example.setdefault(sig, r[3])
    out_rows = [[sig, n, example[sig]] for sig, n in counts.most_common()]
    gdir = os.path.join(ROOT, "_global")
    os.makedirs(gdir, exist_ok=True)
    lib_io.write_csv(os.path.join(gdir, CFG["outputs"]["error_patterns"]),
                     ["signature", "count", "example"], out_rows)
    print(f"  [error-patterns] {len(out_rows)} distinct signatures ({sum(counts.values())} error lines)")


if __name__ == "__main__":
    main()
