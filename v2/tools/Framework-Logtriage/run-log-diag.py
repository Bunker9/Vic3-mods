#!/usr/bin/env python3
"""run-log-diag.py — Logtriage Set-3 MASTER: the diagnostics engine. STEP 1: seed diag_literals.csv into
log-CURR/ ROOT from the tracked .example (the example -> ROOT config pattern; --literals overrides the rules
file wholesale — swappable per game/version, UAT LT-06). STEP 2: aggr-log-smoke (global smoke metrics +
smoke_detector accrual). STEP 3: for _global + each mod, ext-diag-eval + gen-diag-md -> diagnostics.md.
Requires run-log-aggr (per-mod metrics) for mod targets. Args: one or more MOD_NAMEs, or --all."""
import os
import sys
import shutil
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "log-CURR")


def main():
    p = lib_args.build_master_parser("Logtriage Set3 master: diagnostics engine -> per-mod + global diagnostics.md.")
    p.add_argument("--literals", default=None, help="alternative rules CSV forwarded to ext-diag-eval (swappable data)")
    args = p.parse_args()
    mods = lib_args.selected_mods(args)
    seed = os.path.join(HERE, CFG["diag"]["example"])                     # STEP 1: seed rules -> ROOT
    dest = os.path.join(ROOT, CFG["diag"]["root"])
    if os.path.isfile(seed) and not os.path.isfile(dest):
        shutil.copyfile(seed, dest)
    subprocess.run([sys.executable, os.path.join(HERE, "aggr-log-smoke.py")], check=True)   # STEP 2 (global)
    lit = (["--literals", args.literals] if args.literals else [])
    for target in ["_global"] + mods:                                     # STEP 3
        subprocess.run([sys.executable, os.path.join(HERE, "ext-diag-eval.py"), target] + lit, check=True)
        subprocess.run([sys.executable, os.path.join(HERE, "gen-diag-md.py"), target], check=True)
    print(f"== log-diag done -> {ROOT}/<target>/diagnostics.md ==")


if __name__ == "__main__":
    main()
