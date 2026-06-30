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
    a = lib_args.parse_args("Debug master: ModParse -> Logtriage -> SaveParse for one mod.",
                            mod_path=True, save=True, logs=True)
    pfx = (["--prefix", a.prefix] if a.prefix else [])
    rr = (["--rerun"] if a.rerun else [])
    print(f"==== DEBUG MASTER: {a.mod_name} ====")
    _run("Framework-ModParse", "run-modparse.py", [a.mod_name, *([a.mod_path] if a.mod_path else []), *pfx, *rr])
    _run("Framework-Logtriage", "run-logtriage.py", [a.mod_name, *(["--logs", a.logs] if a.logs else []), *pfx, *rr])
    _run("Framework-SaveParse", "run-saveparse.py", [a.mod_name, *(["--save", a.save] if a.save else []), *pfx, *rr])
    print("==== outputs ====")
    print(f"  data:      {lib_paths.data_dir(a.mod_name, create=False)}")
    print(f"  logtriage: {os.path.join(lib_paths.run_dir('log-CURR', a.mod_name, create=False), 'diagnostics.md')}")
    print(f"  saveparse: {os.path.join(lib_paths.run_dir('save-CURR', a.mod_name, create=False), 'diagnostics.md')}")


if __name__ == "__main__":
    main()
