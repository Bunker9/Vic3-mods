#!/usr/bin/env python3
"""run-saveparse.py — Framework-SaveParse MASTER. Resolves the save ONCE and runs (as subprocesses, all given
the SAME --save) ext-save-blocks -> aggr-save-matches + aggr-state-census -> anal-save-report over data-<Mod>/
-> save-CURR/<Mod>/. Run Framework-ModParse (run-modparse) first. Args: arg1=MOD_NAME, --save <file.v3>,
--prefix, --rerun."""
import os
import sys
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_paths

STAGES = ["ext-save-blocks.py", "aggr-save-matches.py", "aggr-state-census.py", "anal-save-report.py"]
ARCHIVE = os.path.join(os.path.dirname(HERE), "Framework-common", "run-archive-curr.py")


def main():
    args = lib_args.parse_master_args("SaveParse master: save + data-<Mod> -> save-CURR/<Mod>/ (one or more mods; --all).",
                                      save=True)
    mods = lib_args.selected_mods(args)
    save = lib_paths.resolve_save(lib_paths.game_config(), args.save)   # resolve ONCE so all mods/stages agree
    # STEP 1: demote every prior save-CURR* ONCE per run (BEFORE any run_dir creates the fresh one), so ALL mods in
    # THIS run share the single new save-CURR and the prior run's outputs PERSIST as save-<label> for fallback.
    subprocess.run([sys.executable, ARCHIVE, "save-CURR"], check=True)
    for mod in mods:
        print(f"== SaveParse {mod}  save={os.path.basename(save)} -> {lib_paths.run_dir('save-CURR', mod)} ==")
        sub = [mod, "--save", save]                    # pass the RESOLVED path to every stage
        if args.prefix:
            sub += ["--prefix", args.prefix]
        if args.rerun:
            sub += ["--rerun"]
        for stage in STAGES:
            subprocess.run([sys.executable, os.path.join(HERE, stage)] + sub, check=True)
    print("== SaveParse done ==")


if __name__ == "__main__":
    main()
