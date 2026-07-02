#!/usr/bin/env python3
"""run-save-aggr.py — SaveParse Set-2 MASTER: per mod, join the COMMON save-CURR pool (built once by
run-save-parse) against data-<Mod> -> save-CURR/<Mod>/ aggr_save_matches.csv + aggr_census_overbuild.csv +
metrics.csv. Runs aggr-save-matches then aggr-save-overbuild as subprocesses per mod. Requires
Framework-ModParse (data-<Mod>) and run-save-parse (common pool). Args: one or more MOD_NAMEs, or --all."""
import os
import sys
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_paths

STAGES = ["aggr-save-matches.py", "aggr-save-overbuild.py"]


def main():
    args = lib_args.parse_master_args("SaveParse Set2 master: common pool x data-<Mod> -> per-mod aggr + metrics.")
    for mod in lib_args.selected_mods(args):
        print(f"== save-aggr {mod} -> {lib_paths.run_dir('save-CURR', mod)} ==")
        sub = [mod] + (["--prefix", args.prefix] if args.prefix else [])
        for stage in STAGES:
            subprocess.run([sys.executable, os.path.join(HERE, stage)] + sub, check=True)
    print("== save-aggr done ==")


if __name__ == "__main__":
    main()
