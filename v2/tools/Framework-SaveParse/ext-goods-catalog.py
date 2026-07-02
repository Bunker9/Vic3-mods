#!/usr/bin/env python3
"""ext-goods-catalog.py — SaveParse Set-1 catalog builder (the ENRICH lookup, UAT SP-02): goods id -> name.
The save keys goods by NUMERIC id = the definition ORDER across <game_files_path>/<goods_dir>/*.txt (files
sorted, top-level keys in file order). Writes COMMON save-CURR/goods_ids.csv. If game_files_path is blank,
falls back to copying the tracked goods_ids.example.csv seed (if it has rows) — a literal lookup list, no
hardcoding in code. Cross-check note: a state's trade.goods ids vs its traded_goods names must agree."""
import os
import re
import sys
import shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
G = CFG["goods"]
ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")
_TOPKEY = re.compile(r"^([A-Za-z_]\w*)\s*=\s*\{")   # column-0 definition opener


def main():
    os.makedirs(ROOT, exist_ok=True)
    dest = os.path.join(ROOT, G["catalog_root"])
    game = (lib_paths.game_config() or {}).get("game_files_path") or ""
    gdir = os.path.join(game, *G["goods_dir"].split("/")) if game else ""
    if gdir and os.path.isdir(gdir):
        names = []
        for _rel, ap, _fn in lib_io.walk_files(gdir, {".txt"}):
            for line in lib_io.read_text_lines(ap):
                m = _TOPKEY.match(line)
                if m:
                    names.append(m.group(1))
        lib_io.write_csv(dest, ["goods_id", "goods_name"], [[i, n] for i, n in enumerate(names)])
        print(f"  -> {G['catalog_root']}: {len(names)} goods from {gdir} (id = definition order)")
        return
    seed = os.path.join(HERE, G["catalog_example"])
    if os.path.isfile(seed) and len(lib_io.read_csv(seed)[1]) > 0:
        shutil.copyfile(seed, dest)
        print(f"  -> {G['catalog_root']}: copied from tracked seed (game_files_path not set)")
    else:
        print("  !! goods catalog SKIPPED: set game_files_path in config_game.toml "
              "(or fill goods_ids.example.csv) — raw_market_goods keeps raw ids")


if __name__ == "__main__":
    main()
