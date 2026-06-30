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


def main():
    args = lib_args.parse_args("Logtriage master: logs + data-<Mod> -> log-CURR/<Mod>/.", logs=True)
    print(f"== Logtriage {args.mod_name} -> {lib_paths.run_dir('log-CURR', args.mod_name)} ==")
    passthrough = sys.argv[1:]
    for stage in STAGES:
        subprocess.run([sys.executable, os.path.join(HERE, stage)] + passthrough, check=True)
    print("== Logtriage done ==")


if __name__ == "__main__":
    main()
