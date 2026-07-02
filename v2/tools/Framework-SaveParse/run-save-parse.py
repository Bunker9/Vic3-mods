#!/usr/bin/env python3
"""run-save-parse.py — SaveParse Set-1 MASTER (parse-once): build the COMMON save-CURR/ ROOT pool. STEP 1:
archive every prior save-CURR* ONCE (the SOLE archive point of the save flow) — SKIPPED entirely when the
pool already exists and no --rerun (reuse: a 147 MB save is parsed at most once per run). STEP 2: resolve the
save ONCE, then ext-save-blocks + ext-save-flags + ext-save-goods (all given the SAME --save) +
ext-goods-catalog + aggr-save-census. Mod-agnostic; NO MOD_NAME. Standalone or chained by run-saveparse."""
import os
import sys
import argparse
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_paths

ARCHIVE = os.path.join(os.path.dirname(HERE), "Framework-common", "run-archive-curr.py")
ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")
STAGES = ["ext-save-blocks.py", "ext-save-flags.py", "ext-save-goods.py"]


def main():
    p = argparse.ArgumentParser(description="SaveParse Set1 master: parse the save ONCE -> common raws.")
    p.add_argument("--save", default=None, help="save file (.v3); else resolved from config_game.toml")
    p.add_argument("--rerun", action="store_true", help="force re-parse (else reuse an existing pool)")
    a = p.parse_args()
    if os.path.isfile(os.path.join(ROOT, "raw_countries.csv")) and not a.rerun:
        print(f"== save-parse: pool already at {ROOT} — reusing (pass --rerun to re-parse) ==")
        return
    subprocess.run([sys.executable, ARCHIVE, "save-CURR"], check=True)            # STEP 1 (once)
    save = lib_paths.resolve_save(lib_paths.game_config(), a.save)                # resolve ONCE
    for stage in STAGES:
        subprocess.run([sys.executable, os.path.join(HERE, stage), "--save", save], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "ext-goods-catalog.py")], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "aggr-save-census.py")], check=True)
    print(f"== save-parse done -> {ROOT} ==")


if __name__ == "__main__":
    main()
