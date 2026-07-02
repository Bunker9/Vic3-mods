#!/usr/bin/env python3
"""aggr-log-smoke.py — Logtriage Set-3 GLOBAL aggregator: raw_errors.csv × the smoke_detector (the curated
rule-out list at log-CURR ROOT) -> _global/metrics.csv (error_lines, suppressed, tracked_errors,
unreviewed_errors, new_signatures) AND updates smoke_detector.csv in place: per-pattern hit counts + a first
example accrue, and every UNSEEN signature is APPENDED with human_agreed blank for human review. Append-only
curation — no row is ever deleted or reordered. Mod-agnostic, runs once per run; run-log-diag invokes it."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "log-CURR")


def main():
    _h, errs = lib_io.read_csv(os.path.join(ROOT, CFG["outputs"]["raw_errors"]))
    if _h is None:
        sys.exit("aggr-log-smoke: missing raw_errors.csv — run run-log-sort first (Set 1)")
    smoke_path = os.path.join(ROOT, CFG["smoke"]["root"])
    smoke = lib_io.read_csv_dicts(smoke_path)                  # human_agreed, pattern, count, example
    hits = {i: 0 for i in range(len(smoke))}
    suppressed = tracked = unreviewed = 0
    unseen = {}
    for _f, _n, _sev, raw, sig in errs:                        # log_file, line_no, severity, raw_text, signature
        row_i = next((i for i, r in enumerate(smoke) if r["pattern"] and (r["pattern"] in raw or r["pattern"] in sig)), None)
        if row_i is None:
            unreviewed += 1
            unseen.setdefault(sig, raw)
            continue
        hits[row_i] += 1
        agreed = smoke[row_i]["human_agreed"].strip().upper()
        suppressed += (agreed == "Y")
        tracked += (agreed == "N")
        unreviewed += (agreed not in ("Y", "N"))
    for i, r in enumerate(smoke):                              # accrue counts + first example (append-only)
        r["count"] = str(int(r.get("count") or 0) + hits[i])
    for sig, raw in unseen.items():
        smoke.append({"human_agreed": "", "pattern": sig, "count": "1", "example": raw})
    lib_io.write_csv(smoke_path, ["human_agreed", "pattern", "count", "example"],
                     [[r["human_agreed"], r["pattern"], r["count"], r.get("example", "")] for r in smoke])
    gdir = os.path.join(ROOT, "_global")
    os.makedirs(gdir, exist_ok=True)
    metrics = [["error_lines", len(errs)], ["suppressed", suppressed], ["tracked_errors", tracked],
               ["unreviewed_errors", unreviewed], ["new_signatures", len(unseen)]]
    lib_io.write_csv(os.path.join(gdir, CFG["outputs"]["metrics"]), ["metric", "value"], metrics)
    print(f"  [smoke] {len(errs)} error lines: {suppressed} suppressed, {tracked} tracked, "
          f"{unreviewed} unreviewed (+{len(unseen)} new signatures appended)")


if __name__ == "__main__":
    main()
