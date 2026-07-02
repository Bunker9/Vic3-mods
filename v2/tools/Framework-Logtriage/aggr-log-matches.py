#!/usr/bin/env python3
"""aggr-log-matches.py — Logtriage Set-2 aggregator (REFOCUSED 2026-07-02 onto the common pool): join the
COMMON log-CURR/raw_loglines.csv (built once by run-log-sort, SORT-not-FILTER) against the mod's data-<Mod>
key lists -> log-CURR/<Mod>/aggr_log_matches.csv (log_file, log_line_no, match_type[file|kw|dbg], match_id,
matched_value, severity, log_text). NEVER re-reads the game logs. Standalone; run-log-aggr invokes it."""
import os
import re
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "log-CURR")


def _need(path, hint):
    h, rows = lib_io.read_csv(path)
    if h is None:
        sys.exit(f"aggr-log-matches: missing {os.path.basename(path)} — {hint}")
    return rows


def main(args):
    data = lib_paths.data_dir(args.mod_name, create=False)
    mp_hint = "run Framework-ModParse first (run-modparse)"
    files = _need(os.path.join(data, "raw_files.csv"), mp_hint)          # file_id, rel_path, basename
    kws = _need(os.path.join(data, "raw_keywords.csv"), mp_hint)         # kw_id, kw, kind
    dbgs = _need(os.path.join(data, "raw_debuglines.csv"), mp_hint)      # dbg_id, text, file_id, line_no
    lines = _need(os.path.join(ROOT, CFG["outputs"]["raw_loglines"]), "run run-log-sort first (Set 1)")
    file_keys = [(int(r[0]), r[2]) for r in files]
    kw_keys = [(int(r[0]), r[1], re.compile(r"(?<![A-Za-z0-9_])" + re.escape(r[1]) + r"(?![A-Za-z0-9_])"))
               for r in kws]
    dbg_keys = [(int(r[0]), r[1]) for r in dbgs]
    rows = []
    for fname, ln, severity, text in lines:
        for dbg_id, t in dbg_keys:
            if t and t in text:
                rows.append([fname, ln, "dbg", dbg_id, t, severity, text])
        for kw_id, kw, rx in kw_keys:
            if rx.search(text):
                rows.append([fname, ln, "kw", kw_id, kw, severity, text])
        for file_id, base in file_keys:
            if base in text:
                rows.append([fname, ln, "file", file_id, base, severity, text])
    out = os.path.join(lib_paths.run_dir("log-CURR", args.mod_name), CFG["outputs"]["matches"])
    lib_io.write_csv(out, ["log_file", "log_line_no", "match_type", "match_id", "matched_value",
                           "severity", "log_text"], rows)
    print(f"  [matches] {len(rows)} from the common pool -> {out}")


if __name__ == "__main__":
    main(lib_args.parse_args("Logtriage Set2: join common raw_loglines vs data-<Mod> keys."))
