#!/usr/bin/env python3
"""aggr-save-matches.py — SaveParse aggregator: scan the save for the mod's persisted tokens (from
data-<Mod>/raw_keywords.csv) + a generic <abbr>_fingerprint_* regex -> save-CURR/<Mod>/aggr_save_matches.csv.
One row per occurrence that PERSISTED. Numeric var values decoded from fixed-point (factor from config).
Ported from save-game-parser/aggr_save_matches.py. Standalone-runnable."""
import os
import re
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config, lib_parse

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
INFIX = CFG["markers"]["fingerprint_infix"]
FACTOR = CFG["decode"]["fixed_point_factor"]
HEADER = ["mod", "fp", "fp_type", "save_token", "section", "doc_path",
          "value", "vtype", "date", "line_no", "sample"]


def _decode(value, vtype):
    if vtype == "value" and re.fullmatch(r"-?\d+", value or ""):
        d = lib_parse.decode_value(value, FACTOR)
        return str(int(d)) if d == int(d) else f"{d:.5f}".rstrip("0").rstrip(".")
    return value


def main(args):
    data = lib_paths.data_dir(args.mod_name, create=False)
    _h, kwrows = lib_io.read_csv(os.path.join(data, "raw_keywords.csv"))
    if _h is None:
        sys.exit("aggr-save-matches: missing data-<Mod>/raw_keywords.csv; run run-modparse first.")
    kws = [r[1] for r in kwrows]
    abbr = lib_parse.detect_prefix(kws, args.prefix)
    literal = set(kws)
    fp_re = re.compile(re.escape(abbr) + re.escape(INFIX) + r"[A-Za-z0-9_]+") if abbr else None
    save = lib_paths.resolve_save(lib_paths.game_config(), args.save)
    print(f"  scan: {save}\n  keys: {len(literal)} kw + /{abbr}{INFIX}*/")
    matches = lib_parse.scan(save, literal, fp_re)
    rows = [[args.mod_name, m["term"], m["fp_type"], m["save_token"], m["section"], m["doc_path"],
             _decode(m["value"], m["vtype"]), m["vtype"], m["date"], m["line_no"], m["sample"]]
            for m in matches]
    rows.sort(key=lambda r: (r[2], r[1], r[9]))
    out = os.path.join(lib_paths.run_dir("save-CURR", args.mod_name), CFG["outputs"]["matches"])
    lib_io.write_csv(out, HEADER, rows)
    print(f"  -> {out}  ({len(rows)} persisted occurrences)")
    return matches


if __name__ == "__main__":
    main(lib_args.parse_args("SaveParse: scan a save for persisted tokens + fingerprints.", save=True))
