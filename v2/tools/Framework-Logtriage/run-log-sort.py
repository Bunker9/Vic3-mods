#!/usr/bin/env python3
"""run-log-sort.py — Logtriage Set-1 MASTER (SORT-not-FILTER). STEP 1: archive prior log-CURR (once). STEP 2: load
the tracked smoke_detector seed into log-CURR/ ROOT (the .example -> ROOT config pattern). STEP 3: run ext-log-lines
+ aggr-log-errorpatterns (subprocesses) -> COMMON raws + _global/error_patterns.csv. Mod-agnostic, runs ONCE per
run. Flag: --logs DIR. Standalone or chained by run-logtriage."""
import os
import sys
import shutil
import argparse
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")
ARCHIVE = os.path.join(os.path.dirname(HERE), "Framework-common", "run-archive-curr.py")
ROOT = os.path.join(lib_paths.GAME_ROOT, "log-CURR")


def main():
    p = argparse.ArgumentParser(description="Logtriage Set1 master: sort all *.log into common raws (once).")
    p.add_argument("--logs", default=None, help="override the Vic3 logs dir")
    a = p.parse_args()
    subprocess.run([sys.executable, ARCHIVE, "log-CURR"], check=True)          # STEP 1 (once)
    os.makedirs(ROOT, exist_ok=True)
    seed = os.path.join(HERE, CFG["smoke"]["example"])                         # STEP 2: seed smoke -> ROOT
    dest = os.path.join(ROOT, CFG["smoke"]["root"])
    if os.path.isfile(seed) and not os.path.isfile(dest):
        shutil.copyfile(seed, dest)
    extra = (["--logs", a.logs] if a.logs else [])
    subprocess.run([sys.executable, os.path.join(HERE, "ext-log-lines.py")] + extra, check=True)   # STEP 3
    subprocess.run([sys.executable, os.path.join(HERE, "aggr-log-errorpatterns.py")], check=True)
    print(f"== log-sort done -> {ROOT} ==")


if __name__ == "__main__":
    main()
