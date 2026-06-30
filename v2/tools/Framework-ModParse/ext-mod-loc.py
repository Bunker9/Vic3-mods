#!/usr/bin/env python3
"""ext-mod-loc.py — ModParse extractor: the mod's localization keys -> data-<Mod>/raw_loc.csv
(loc_id, key, file_id, line_no). Parses `key:0 "..."` in .yml. Framework-Logtriage uses this for the
loc-for-all-kw check (every player-facing kw must have a loc entry). Standalone-runnable; master invokes
as subprocess."""
import os
import re
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_modparse.toml")
LOC_RX = re.compile(r'^\s*(?P<key>[A-Za-z0-9_.]+):\d+\s+"')


def main(args):
    mod_path = lib_paths.resolve_mod_path(lib_paths.game_config(), args.mod_name, args.mod_path)
    if not mod_path:
        sys.exit("ext-mod-loc: no MOD_PATH.")
    data = lib_paths.data_dir(args.mod_name)
    _h, frows = lib_io.read_csv(os.path.join(data, CFG["outputs"]["files"]))
    relmap = {r[1]: int(r[0]) for r in frows} if frows else {}
    rows, loc_id = [], 0
    for i, (rel, ap, fn) in enumerate(lib_io.walk_files(mod_path, set(CFG["scan"]["extensions"])), 1):
        if not fn.lower().endswith((".yml", ".yaml")):
            continue
        file_id = relmap.get(rel, i)
        for ln, line in enumerate(lib_io.read_text_lines(ap), 1):
            m = LOC_RX.match(line)
            if m:
                loc_id += 1
                rows.append([loc_id, m.group("key"), file_id, ln])
    out = os.path.join(data, CFG["outputs"]["loc"])
    lib_io.write_csv(out, ["loc_id", "key", "file_id", "line_no"], rows)
    print(f"  [loc] {len(rows)} -> {out}")
    return out


if __name__ == "__main__":
    main(lib_args.parse_args("ModParse: extract localization keys.", mod_path=True))
