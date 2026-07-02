#!/usr/bin/env python3
"""run-save-diag.py — SaveParse Set-3 MASTER: save-side diagnostics via the SHARED engine
(Framework-Logtriage's ext-diag-eval + gen-diag-md over Framework-common's lib_diag, called with
--kind save-CURR). STEP 1: seed diag_literals.csv into save-CURR/ ROOT from the tracked .example (the
example -> ROOT pattern; --literals overrides the rules file wholesale — swappable per game/version, UAT
LT-06). STEP 2: per mod, evaluate + render save-CURR/<Mod>/diagnostics.md. Requires run-save-aggr (per-mod
metrics). Args: one or more MOD_NAMEs, or --all."""
import os
import sys
import shutil
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")
ENGINE = os.path.join(os.path.dirname(HERE), "Framework-Logtriage")


def main():
    p = lib_args.build_master_parser("SaveParse Set3 master: shared diagnostics engine -> per-mod diagnostics.md.")
    p.add_argument("--literals", default=None, help="alternative rules CSV forwarded to the engine (swappable data)")
    args = p.parse_args()
    mods = lib_args.selected_mods(args)
    seed = os.path.join(HERE, CFG["diag"]["example"])                     # STEP 1: seed rules -> ROOT
    dest = os.path.join(ROOT, CFG["diag"]["root"])
    if os.path.isfile(seed) and not os.path.isfile(dest):
        shutil.copyfile(seed, dest)
    lit = ["--literals", args.literals or dest]
    for mod in mods:                                                      # STEP 2
        subprocess.run([sys.executable, os.path.join(ENGINE, "ext-diag-eval.py"),
                        mod, "--kind", "save-CURR"] + lit, check=True)
        subprocess.run([sys.executable, os.path.join(ENGINE, "gen-diag-md.py"),
                        mod, "--kind", "save-CURR"], check=True)
    print(f"== save-diag done -> {ROOT}/<MOD>/diagnostics.md ==")


if __name__ == "__main__":
    main()
