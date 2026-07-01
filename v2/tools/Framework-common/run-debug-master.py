#!/usr/bin/env python3
"""run-debug-master.py — MASTER orchestrator: the whole debug flow for one mod —
Framework-ModParse -> Framework-Logtriage -> Framework-SaveParse (each as a subprocess) — then print the three
output locations. The single in-place entry point the v2 report build + CI invoke. Args: arg1=MOD_NAME,
arg2=MOD_PATH (or config_game.toml [mod_locations]), --save <f>, --logs <d>, --prefix, --rerun."""
import os
import sys
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lib_args, lib_paths


def _run(framework, script, extra):
    subprocess.run([sys.executable, os.path.join(TOOLS, framework, script), *extra], check=True)


def main():
    a = lib_args.parse_master_args("Debug master: ModParse -> Logtriage -> SaveParse (one or more mods; --all).",
                                   mod_path=True, save=True, logs=True)
    mods = lib_args.selected_mods(a)                         # validate + for the summary
    sel = (["--all"] if a.all else list(a.mod_names))        # forward the SAME selection to each sub-master
    common = sel + (["--prefix", a.prefix] if a.prefix else []) + (["--rerun"] if a.rerun else [])
    print(f"==== DEBUG MASTER: {', '.join(mods)} ====")
    _run("Framework-ModParse", "run-modparse.py", common + (["--path", a.path] if a.path else []))
    _run("Framework-Logtriage", "run-logtriage.py", common + (["--logs", a.logs] if a.logs else []))
    _run("Framework-SaveParse", "run-saveparse.py", common + (["--save", a.save] if a.save else []))
    print("==== outputs (per mod) ====")
    for mod in mods:
        print(f"  [{mod}] data={lib_paths.data_dir(mod, create=False)}")
    print(f"  logtriage: {lib_paths.GAME_DIR}/log-CURR/<MOD>/diagnostics.md")
    print(f"  saveparse: {lib_paths.GAME_DIR}/save-CURR/<MOD>/diagnostics.md")


if __name__ == "__main__":
    main()
