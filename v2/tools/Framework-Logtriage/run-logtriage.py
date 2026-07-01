#!/usr/bin/env python3
"""run-logtriage.py — Framework-Logtriage MASTER. Runs aggr-log-matches then anal-log-triage (as subprocesses)
over Game-<game>/data-<Mod>/ + the game LOGS -> log-CURR/<Mod>/. Run Framework-ModParse (run-modparse) FIRST so
data-<Mod>/ exists. Args: arg1=MOD_NAME, --logs DIR, --prefix, --rerun. Run BEFORE any manual log deep-dive."""
import os
import sys
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_paths

STAGES = ["aggr-log-matches.py", "anal-log-triage.py"]
ARCHIVE = os.path.join(os.path.dirname(HERE), "Framework-common", "run-archive-curr.py")


def main():
    args = lib_args.parse_master_args("Logtriage master: logs + data-<Mod> -> log-CURR/<Mod>/ (one or more mods; --all).",
                                      logs=True)
    mods = lib_args.selected_mods(args)
    # STEP 1: demote every prior log-CURR* ONCE per run (BEFORE any run_dir creates the fresh one), so ALL mods in
    # THIS run share the single new log-CURR and the prior run's outputs PERSIST as log-<label> for fallback.
    subprocess.run([sys.executable, ARCHIVE, "log-CURR"], check=True)
    for mod in mods:
        print(f"== Logtriage {mod} -> {lib_paths.run_dir('log-CURR', mod)} ==")
        sub = [mod]
        if args.logs:
            sub += ["--logs", args.logs]
        if args.prefix:
            sub += ["--prefix", args.prefix]
        if args.rerun:
            sub += ["--rerun"]
        for stage in STAGES:
            subprocess.run([sys.executable, os.path.join(HERE, stage)] + sub, check=True)
    print("== Logtriage done ==")


if __name__ == "__main__":
    main()
