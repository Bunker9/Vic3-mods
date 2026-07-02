#!/usr/bin/env python3
"""run-log-aggr.py — Logtriage Set-2 MASTER: per mod, join the COMMON log-CURR raws (built once by
run-log-sort) against data-<Mod> -> log-CURR/<Mod>/ aggr_log_matches.csv + aggr_markers_status.csv +
metrics.csv. Runs aggr-log-matches then aggr-log-markers as subprocesses per mod. Requires Framework-ModParse
(data-<Mod>) and run-log-sort (common raws) to have run. Args: one or more MOD_NAMEs, or --all."""
import os
import sys
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_paths

STAGES = ["aggr-log-matches.py", "aggr-log-markers.py"]


def main():
    args = lib_args.parse_master_args("Logtriage Set2 master: common raws x data-<Mod> -> per-mod aggr + metrics.")
    for mod in lib_args.selected_mods(args):
        print(f"== log-aggr {mod} -> {lib_paths.run_dir('log-CURR', mod)} ==")
        for stage in STAGES:
            subprocess.run([sys.executable, os.path.join(HERE, stage), mod], check=True)
    print("== log-aggr done ==")


if __name__ == "__main__":
    main()
