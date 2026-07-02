#!/usr/bin/env python3
"""ext-save-blocks.py — SaveParse Set-1 raw extractor (MOD-AGNOSTIC, parse-once): ONE streaming pass over a
Vic3 save -> COMMON save-CURR/raw_<mgr>.csv per configured manager (id + top-level scalar fields, RAW IDs
only — enrichment is a separate join, UAT SP-02; no tags/probe literals, T101). Runs ONCE per run; every mod
reads these. Standalone; run-save-parse invokes it with the resolved --save."""
import os
import re
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths, lib_config, lib_parse

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
MANAGERS = CFG["managers"]   # mgr -> {out, fields}
ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")
_OPENER = re.compile(r'^\s*([\w:.\-]+)=\{')
_SCALAR = re.compile(r'^\s*([A-Za-z_]\w*)=("?[^"{}\n]*"?)\s*$')


def main():
    p = argparse.ArgumentParser(description="SaveParse Set1: raw per-manager block extractor (common, once).")
    p.add_argument("--save", default=None, help="save file (.v3); else resolved from config_game.toml")
    a = p.parse_args()
    save = lib_paths.resolve_save(lib_paths.game_config(), a.save)
    print(f"  ext-blocks: scan {save}")
    rows = {spec["out"]: [] for spec in MANAGERS.values()}
    named, depth, rec = [], 0, None
    for line in lib_parse.iter_save_lines(save):
        if rec is not None:
            m = _SCALAR.match(line)
            if m and m.group(1) in rec[2] and m.group(1) not in rec[4]:
                rec[4][m.group(1)] = m.group(2).strip().strip('"')
        opener = _OPENER.match(line)
        opens, closes = line.count('{'), line.count('}')
        if opener and opens > closes:
            named.append((depth, opener.group(1)))
            if rec is None and len(named) >= 3:
                gp, par, idk = named[-3][1], named[-2][1], named[-1][1]
                if gp in MANAGERS and par == 'database' and re.fullmatch(r'-?\d+', idk):
                    rec = (gp, MANAGERS[gp]["out"], MANAGERS[gp]["fields"], idk, {}, depth)
        depth += opens - closes
        if depth < 0:
            depth = 0
        while named and named[-1][0] >= depth:
            popped = named.pop()
            if rec is not None and popped[0] == rec[5] and popped[1] == rec[3]:
                _g, outname, fields, idk, data, _d = rec
                rows[outname].append([idk] + [data.get(f, '') for f in fields])
                rec = None
    os.makedirs(ROOT, exist_ok=True)
    for spec in MANAGERS.values():
        path = os.path.join(ROOT, spec["out"] + ".csv")
        lib_io.write_csv(path, ["id"] + spec["fields"], rows[spec["out"]])
        print(f"  -> {spec['out']}.csv: {len(rows[spec['out']])} rows")


if __name__ == "__main__":
    main()
