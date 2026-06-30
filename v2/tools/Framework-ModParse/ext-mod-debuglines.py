#!/usr/bin/env python3
"""ext-mod-debuglines.py — ModParse extractor: the mod's debug_log markers -> data-<Mod>/raw_debuglines.csv
(dbg_id, text, file_id, line_no). file_id FKs raw_files.csv (run ext-mod-files first). These markers are what
Framework-Logtriage cross-references for fired-vs-unfired. Standalone-runnable; master invokes as subprocess."""
import os
import re
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_modparse.toml")
DEBUG_RX = re.compile(r'^\s*debug_log\s*=\s*("(?P<q>[^"]*)"|(?P<b>\S+))')


def main(args):
    mod_path = lib_paths.resolve_mod_path(lib_paths.game_config(), args.mod_name, args.mod_path)
    if not mod_path:
        sys.exit("ext-mod-debuglines: no MOD_PATH.")
    data = lib_paths.data_dir(args.mod_name)
    _h, frows = lib_io.read_csv(os.path.join(data, CFG["outputs"]["files"]))
    relmap = {r[1]: int(r[0]) for r in frows} if frows else {}
    rows, dbg_id = [], 0
    for i, (rel, ap, _fn) in enumerate(lib_io.walk_files(mod_path, set(CFG["scan"]["extensions"])), 1):
        file_id = relmap.get(rel, i)
        for ln, line in enumerate(lib_io.read_text_lines(ap), 1):
            m = DEBUG_RX.match(line)
            if not m:
                continue
            dbg_id += 1
            rows.append([dbg_id, m.group("q") if m.group("q") is not None else m.group("b"), file_id, ln])
    out = os.path.join(data, CFG["outputs"]["debuglines"])
    lib_io.write_csv(out, ["dbg_id", "text", "file_id", "line_no"], rows)
    print(f"  [debuglines] {len(rows)} -> {out}")
    return out


if __name__ == "__main__":
    main(lib_args.parse_args("ModParse: extract debug_log markers.", mod_path=True))
