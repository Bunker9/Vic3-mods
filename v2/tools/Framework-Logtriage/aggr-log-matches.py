#!/usr/bin/env python3
"""aggr-log-matches.py — Logtriage aggregator: join the game logs vs the data-<Mod> key lists ->
log-CURR/<Mod>/aggr_log_matches.csv (log_file, log_line_no, match_type[file|kw|dbg], match_id, matched_value,
severity, log_text). Ported from tools/aggr_log_matches.py onto Framework-common. Standalone-runnable; master
invokes as subprocess."""
import os
import re
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")


def _need(data, fname):
    h, rows = lib_io.read_csv(os.path.join(data, fname))
    if h is None:
        sys.exit(f"aggr-log-matches: missing {fname} in data dir; run Framework-ModParse first (run-modparse).")
    return rows


def main(args):
    data = lib_paths.data_dir(args.mod_name, create=False)
    files = _need(data, "raw_files.csv")          # file_id, rel_path, basename
    kws = _need(data, "raw_keywords.csv")          # kw_id, kw, kind
    dbgs = _need(data, "raw_debuglines.csv")       # dbg_id, text, file_id, line_no
    file_keys = [(int(r[0]), r[2]) for r in files]
    kw_keys = [(int(r[0]), r[1], re.compile(r"(?<![A-Za-z0-9_])" + re.escape(r[1]) + r"(?![A-Za-z0-9_])"))
               for r in kws]
    dbg_keys = [(int(r[0]), r[1]) for r in dbgs]
    logs_dir = lib_paths.resolve_logs_dir(lib_paths.game_config(), args.logs)
    rows = []
    for fname, severity in (tuple(x) for x in CFG["logs"]["files"]):
        path = os.path.join(logs_dir, fname)
        if not os.path.exists(path):
            continue
        for ln, line in enumerate(lib_io.read_text_lines(path), 1):
            for dbg_id, text in dbg_keys:
                if text and text in line:
                    rows.append([fname, ln, "dbg", dbg_id, text, severity, line])
            for kw_id, kw, rx in kw_keys:
                if rx.search(line):
                    rows.append([fname, ln, "kw", kw_id, kw, severity, line])
            for file_id, base in file_keys:
                if base in line:
                    rows.append([fname, ln, "file", file_id, base, severity, line])
    out = os.path.join(lib_paths.run_dir("log-CURR", args.mod_name), CFG["outputs"]["matches"])
    lib_io.write_csv(out, ["log_file", "log_line_no", "match_type", "match_id", "matched_value",
                           "severity", "log_text"], rows)
    print(f"  [matches] {len(rows)} across {logs_dir} -> {out}")
    return out


if __name__ == "__main__":
    main(lib_args.parse_args("Logtriage: join logs vs data-<Mod> keys.", logs=True))
