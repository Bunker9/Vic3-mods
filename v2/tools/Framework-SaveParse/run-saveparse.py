#!/usr/bin/env python3
"""run-saveparse.py — Framework-SaveParse TOP master (REWORKED 2026-07-02, parse-once). The whole save flow:
Set 1 run-save-parse (archive prior save-CURR* ONCE + parse the save ONCE into the COMMON pool — raws, ALL
persisted flags/modifiers, market goods prices, goods catalog, census; REUSED if already built, --rerun to
force) -> Set 2 run-save-aggr (per-mod joins + metrics over the pool; the 147 MB save is NEVER re-read per
mod) -> Set 3 run-save-diag (shared diagnostics engine -> per-mod diagnostics.md). Run Framework-ModParse
first (data-<Mod>). The save must be TEXT/melted (binary ironman -> 0 rows). Args: MOD_NAME..., --all,
--save FILE, --prefix, --rerun."""
import os
import sys
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_paths


def main():
    args = lib_args.parse_master_args("SaveParse top master: Set1 parse-once -> Set2 per-mod aggr -> Set3 diagnostics.",
                                      save=True)
    mods = lib_args.selected_mods(args)
    print(f"== SaveParse: {', '.join(mods)} ==")
    s1 = [sys.executable, os.path.join(HERE, "run-save-parse.py")]
    s1 += (["--save", args.save] if args.save else []) + (["--rerun"] if args.rerun else [])
    subprocess.run(s1, check=True)                                                   # Set 1 (once)
    s2 = [sys.executable, os.path.join(HERE, "run-save-aggr.py")] + mods
    s2 += (["--prefix", args.prefix] if args.prefix else [])
    subprocess.run(s2, check=True)                                                   # Set 2
    subprocess.run([sys.executable, os.path.join(HERE, "run-save-diag.py")] + mods, check=True)   # Set 3
    root = os.path.join(lib_paths.GAME_ROOT, "save-CURR")
    print(f"== SaveParse done -> {root}/<MOD>/diagnostics.md ==")


if __name__ == "__main__":
    main()
