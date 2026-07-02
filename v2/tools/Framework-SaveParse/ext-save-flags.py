#!/usr/bin/env python3
"""ext-save-flags.py — SaveParse Set-1 raw extractor (SORT-not-FILTER, MOD-AGNOSTIC, parse-once): dump EVERY
persisted `flag=` / `variable=` / `modifier=` / `global_variable=` assignment in the save (no mod filter —
attribution is Set-2's per-mod join) -> COMMON save-CURR/raw_flags.csv with the enclosing doc_path/section,
raw value/vtype (UNDECODED — Set-2 decodes) and a modifier's start_date. Standalone; run-save-parse invokes."""
import os
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths, lib_config, lib_parse

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")
HEADER = ["term", "save_token", "kind", "section", "doc_path", "value", "vtype", "date", "line_no", "sample"]


def main():
    p = argparse.ArgumentParser(description="SaveParse Set1: dump ALL persisted vars/modifiers (common, once).")
    p.add_argument("--save", default=None, help="save file (.v3); else resolved from config_game.toml")
    a = p.parse_args()
    save = lib_paths.resolve_save(lib_paths.game_config(), a.save)
    print(f"  ext-flags: scan {save}")
    recs = lib_parse.scan_kinds(save)
    rows = [[r["term"], r["save_token"], r["fp_type"], r["section"], r["doc_path"],
             r["value"], r["vtype"], r["date"], r["line_no"], r["sample"]] for r in recs]
    os.makedirs(ROOT, exist_ok=True)
    out = os.path.join(ROOT, CFG["outputs"]["flags"])
    lib_io.write_csv(out, HEADER, rows)
    print(f"  -> {CFG['outputs']['flags']}: {len(rows)} persisted var/modifier occurrences")


if __name__ == "__main__":
    main()
