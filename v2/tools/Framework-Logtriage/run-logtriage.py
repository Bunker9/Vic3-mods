#!/usr/bin/env python3
"""run-logtriage.py — Framework-Logtriage TOP master (REWORKED 2026-07-02, SORT-not-FILTER). The whole log
flow: Set 1 run-log-sort (archives every prior log-CURR* ONCE, seeds smoke_detector, sorts ALL *.log into the
COMMON raws — the ONLY place the CURR archive runs, killing the old double-archive trap) -> Set 2 run-log-aggr
(per-mod joins + metrics over the common pool) -> Set 3 run-log-diag (diagnostics engine -> per-mod + _global
diagnostics.md). Run Framework-ModParse first (data-<Mod>). Run BEFORE any manual log deep-dive.
Mods: positional MOD_NAME list, --all, or NEITHER -> the config_logmods.toml list."""
import os
import sys
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_paths, lib_config


def _mods(args):
    if not args.mod_names and not args.all:                    # fallback: the tracked convenience list
        cfg = lib_config.load_framework_config(HERE, "config_logmods.toml")
        if cfg.get("mods"):
            return list(cfg["mods"])
    return lib_args.selected_mods(args)


def main():
    args = lib_args.parse_master_args("Logtriage top master: Set1 sort -> Set2 per-mod aggr -> Set3 diagnostics.",
                                      logs=True)
    mods = _mods(args)
    print(f"== Logtriage: {', '.join(mods)} ==")
    sort_cmd = [sys.executable, os.path.join(HERE, "run-log-sort.py")] + (["--logs", args.logs] if args.logs else [])
    subprocess.run(sort_cmd, check=True)                                            # Set 1 (archives ONCE)
    subprocess.run([sys.executable, os.path.join(HERE, "run-log-aggr.py")] + mods, check=True)   # Set 2
    subprocess.run([sys.executable, os.path.join(HERE, "run-log-diag.py")] + mods, check=True)   # Set 3
    root = os.path.join(lib_paths.GAME_ROOT, "log-CURR")
    print(f"== Logtriage done -> {root}/<MOD>/diagnostics.md + {root}/_global/diagnostics.md ==")


if __name__ == "__main__":
    main()
