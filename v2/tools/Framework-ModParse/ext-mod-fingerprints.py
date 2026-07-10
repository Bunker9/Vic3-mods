#!/usr/bin/env python3
"""ext-mod-fingerprints.py — ModParse extractor (NEW): the mod's ACTIVE (uncommented) save-fingerprint markers
-> data-<Mod>/raw_fingerprints.csv (fp_id, fp_name, op, file_id, line_no). op = set/change/has/other inferred
from the line. COMMENTED lines (fp toggled OFF) and comment-prose mentions are SKIPPED — the comment portion of
each line is stripped before matching, consistent with ext-mod-debuglines (fixed 2026-07-03: previously grabbed
fp tokens anywhere on a line, incl. comments, so a debug-OFF mod wrongly reported non-zero fps). Feeds
Framework-SaveParse (which fp markers to look for) AND the debug-var-standardization check (DEV-RULES: every
change'd var must be set first). Infix from config (default '_fingerprint_'). Standalone; master runs as subprocess."""
import os
import re
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_modparse.toml")
INFIX = CFG["markers"]["fingerprint_infix"]


def _op(line):
    if "change_variable" in line:
        return "change"
    if "set_variable" in line or "set_global_variable" in line:
        return "set"
    if "has_variable" in line or "has_global_variable" in line:
        return "has"
    return "other"


def main(args):
    mod_path = lib_paths.resolve_mod_path(lib_paths.game_config(), args.mod_name, args.mod_path)
    if not mod_path:
        sys.exit("ext-mod-fingerprints: no MOD_PATH.")
    data = lib_paths.data_dir(args.mod_name)
    _h, frows = lib_io.read_csv(os.path.join(data, CFG["outputs"]["files"]))
    relmap = {r[1]: int(r[0]) for r in frows} if frows else {}
    rx = re.compile(r"[A-Za-z0-9_]*" + re.escape(INFIX) + r"[A-Za-z0-9_]*")
    rows, fp_id = [], 0
    for i, (rel, ap, _fn) in enumerate(lib_io.walk_files(mod_path, set(CFG["scan"]["extensions"])), 1):
        file_id = relmap.get(rel, i)
        for ln, line in enumerate(lib_io.read_text_lines(ap), 1):
            code = line.split("#", 1)[0]                    # ACTIVE code only — never grab a toggled-OFF (commented)
            for name in dict.fromkeys(rx.findall(code)):    # or comment-prose fp mention (matches debuglines)
                fp_id += 1
                rows.append([fp_id, name, _op(line), file_id, ln])
    out = os.path.join(data, CFG["outputs"]["fingerprints"])
    lib_io.write_csv(out, ["fp_id", "fp_name", "op", "file_id", "line_no"], rows)
    print(f"  [fingerprints] {len(rows)} -> {out}")
    return out


if __name__ == "__main__":
    main(lib_args.parse_args("ModParse: extract save-fingerprint markers.", mod_path=True))
