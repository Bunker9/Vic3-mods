#!/usr/bin/env python3
"""ext-log-lines.py — Logtriage Set-1 raw extractor (SORT-not-FILTER). Reads ALL configured *.log and writes, at
the COMMON log-CURR/ ROOT (mod-agnostic, once per run): raw_loglines.csv (EVERY non-blank line:
log_file,line_no,severity,text) and raw_errors.csv (EVERY line from an 'error'-severity log + a normalized
signature). NOTHING is dropped for lack of a mod token — the exact fault of the old triage (jomini_script_system /
building_manager errors are now CAPTURED). Standalone; run-log-sort invokes it. Flag: --logs DIR override."""
import os
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths, lib_config, lib_parse

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "log-CURR")


def main():
    p = argparse.ArgumentParser(description="Logtriage Set1: sort all *.log -> common raws (mod-agnostic).")
    p.add_argument("--logs", default=None, help="override the Vic3 logs dir")
    a = p.parse_args()
    logs_dir = lib_paths.resolve_logs_dir(lib_paths.game_config(), a.logs)
    os.makedirs(ROOT, exist_ok=True)
    all_rows, err_rows = [], []
    for fname, severity in CFG["logs"]["files"]:
        path = os.path.join(logs_dir, fname)
        if not os.path.isfile(path):
            continue
        for i, text in enumerate(lib_io.read_text_lines(path), 1):
            if not text.strip():
                continue
            all_rows.append([fname, i, severity, text])
            if severity == "error":                                  # error.log = ALL errors, none filtered
                err_rows.append([fname, i, severity, text, lib_parse.normalize_error(text)])
    lib_io.write_csv(os.path.join(ROOT, CFG["outputs"]["raw_loglines"]),
                     ["log_file", "line_no", "severity", "text"], all_rows)
    lib_io.write_csv(os.path.join(ROOT, CFG["outputs"]["raw_errors"]),
                     ["log_file", "line_no", "severity", "raw_text", "signature"], err_rows)
    print(f"  [log-lines] {len(all_rows)} lines, {len(err_rows)} error lines (from {logs_dir}) -> {ROOT}")


if __name__ == "__main__":
    main()
