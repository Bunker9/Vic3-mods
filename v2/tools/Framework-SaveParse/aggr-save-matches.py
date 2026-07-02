#!/usr/bin/env python3
"""aggr-save-matches.py — SaveParse Set-2 aggregator (REFOCUSED 2026-07-02 onto the common pool): filter the
COMMON save-CURR/raw_flags.csv (built once by run-save-parse) down to THIS mod's persisted tokens — literal
data-<Mod> keywords + the <abbr>_fingerprint_* regex -> save-CURR/<Mod>/aggr_save_matches.csv. Numeric var
values decoded from fixed-point here (the raw pool is undecoded). NEVER re-reads the save. Standalone;
run-save-aggr invokes it."""
import os
import re
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config, lib_parse

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
INFIX = CFG["markers"]["fingerprint_infix"]
FACTOR = CFG["decode"]["fixed_point_factor"]
ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")
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
    fh, flags = lib_io.read_csv(os.path.join(ROOT, CFG["outputs"]["flags"]))
    if fh is None:
        sys.exit("aggr-save-matches: missing the common raw_flags.csv; run run-save-parse first (Set 1).")
    kws = [r[1] for r in kwrows]
    abbr = lib_parse.detect_prefix(kws, args.prefix)
    literal = set(kws)
    fp_re = re.compile(re.escape(abbr) + re.escape(INFIX) + r"[A-Za-z0-9_]+") if abbr else None
    ix = {c: i for i, c in enumerate(fh)}     # term, save_token, kind, section, doc_path, value, vtype, date, line_no, sample
    rows = []
    for r in flags:
        term = r[ix["term"]]
        if term in literal or (fp_re and fp_re.fullmatch(term)):
            rows.append([args.mod_name, term, r[ix["kind"]], r[ix["save_token"]], r[ix["section"]],
                         r[ix["doc_path"]], _decode(r[ix["value"]], r[ix["vtype"]]), r[ix["vtype"]],
                         r[ix["date"]], r[ix["line_no"]], r[ix["sample"]]])
    rows.sort(key=lambda r: (r[2], r[1], int(r[9]) if str(r[9]).isdigit() else 0))
    out = os.path.join(lib_paths.run_dir("save-CURR", args.mod_name), CFG["outputs"]["matches"])
    lib_io.write_csv(out, HEADER, rows)
    print(f"  [save-matches] {len(rows)} persisted occurrences from the common pool -> {out}")


if __name__ == "__main__":
    main(lib_args.parse_args("SaveParse Set2: filter the common raw_flags pool to this mod's tokens."))
