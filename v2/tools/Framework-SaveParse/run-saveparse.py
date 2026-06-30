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


def main():
    args = lib_args.parse_args("SaveParse master: save + data-<Mod> -> save-CURR/<Mod>/.", save=True)
    save = lib_paths.resolve_save(lib_paths.game_config(), args.save)   # resolve ONCE so all stages agree
    print(f"== SaveParse {args.mod_name}  save={os.path.basename(save)} "
          f"-> {lib_paths.run_dir('save-CURR', args.mod_name)} ==")
    base = [args.mod_name, "--save", save]              # pass the RESOLVED path to every stage
    if args.prefix:
        base += ["--prefix", args.prefix]
    if args.rerun:
        base += ["--rerun"]
    for stage in STAGES:
        subprocess.run([sys.executable, os.path.join(HERE, stage)] + base, check=True)
    print("== SaveParse done ==")


if __name__ == "__main__":
    main()
