#!/usr/bin/env python3
"""aggr-log-markers.py — Logtriage Set-2 aggregator: per-marker fired/unfired + re-fire flag + loc-for-all-kw,
plus the per-mod metrics.csv the Set-3 diagnostics engine evaluates. Reads data-<Mod> lists + the mod's
aggr_log_matches.csv (Set-2 matches over the common pool; run aggr-log-matches first). Outputs
log-CURR/<Mod>/aggr_markers_status.csv (marker,kind,fired,count,refire_suspect) + metrics.csv (metric,value).
Standalone; run-log-aggr invokes it."""
import os
import sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")


def _need(path, hint):
    h, rows = lib_io.read_csv(path)
    if h is None:
        sys.exit(f"aggr-log-markers: missing {os.path.basename(path)} — {hint}")
    return rows


def main(args):
    data = lib_paths.data_dir(args.mod_name, create=False)
    out_dir = lib_paths.run_dir("log-CURR", args.mod_name)
    dbgs = _need(os.path.join(data, "raw_debuglines.csv"), "run Framework-ModParse first")
    kws = _need(os.path.join(data, "raw_keywords.csv"), "run Framework-ModParse first")
    locs = lib_io.read_csv(os.path.join(data, "raw_loc.csv"))[1]         # loc_id, key, file_id, line_no
    matches = _need(os.path.join(out_dir, CFG["outputs"]["matches"]), "run aggr-log-matches first (Set 2)")
    counts = Counter((r[2], r[3]) for r in matches)                      # (match_type, match_id)
    refire_at = int(CFG["analysis"]["refire_flag"])
    marker_rows = []
    for dbg_id, text, _f, _l in dbgs:
        n = counts.get(("dbg", dbg_id), 0)
        marker_rows.append([text, "dbg", "yes" if n else "no", n, "yes" if n >= refire_at else "no"])
    loc_keys = {r[1] for r in locs}
    loc_missing = sorted(kw for _i, kw, _k in kws if kw not in loc_keys)
    fired_n = sum(1 for r in marker_rows if r[2] == "yes")
    metrics = [
        ["markers_total", len(marker_rows)], ["markers_fired", fired_n],
        ["unfired", len(marker_rows) - fired_n],
        ["refire_suspects", sum(1 for r in marker_rows if r[4] == "yes")],
        ["kw_hits", sum(n for (t, _i), n in counts.items() if t == "kw")],
        ["file_hits", sum(n for (t, _i), n in counts.items() if t == "file")],
        ["error_mentions", sum(1 for r in matches if r[5] == "error")],
        ["loc_missing", len(loc_missing)],
    ]
    lib_io.write_csv(os.path.join(out_dir, CFG["outputs"]["markers"]),
                     ["marker", "kind", "fired", "count", "refire_suspect"], marker_rows)
    lib_io.write_csv(os.path.join(out_dir, CFG["outputs"]["metrics"]), ["metric", "value"], metrics)
    print(f"  [markers] {fired_n}/{len(marker_rows)} fired; metrics -> {out_dir}")


if __name__ == "__main__":
    main(lib_args.parse_args("Logtriage Set2: marker status + per-mod metrics from the match rows."))
