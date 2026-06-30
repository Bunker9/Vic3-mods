#!/usr/bin/env python3
"""run-modparse.py — Framework-ModParse MASTER. Builds the idempotent data-<Mod>/ token files by running the
ext-* extractors as SUBPROCESSES (their hyphenated code filenames are not importable). ext-mod-files MUST run
first (the others FK its raw_files.csv). Args: arg1=MOD_NAME, arg2=MOD_PATH (or config_game.toml
[mod_locations]), --prefix. Output namespace: Game-<game>/data-<MOD_NAME>/."""
import os
import sys
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_paths

STAGES = ["ext-mod-files.py", "ext-mod-keywords.py", "ext-mod-debuglines.py",
          "ext-mod-loc.py", "ext-mod-fingerprints.py"]


def main():
    args = lib_args.parse_args("ModParse master: mod source -> data-<Mod>/.", mod_path=True)
    print(f"== ModParse {args.mod_name} -> {lib_paths.data_dir(args.mod_name)} ==")
    passthrough = sys.argv[1:]
    for stage in STAGES:
        subprocess.run([sys.executable, os.path.join(HERE, stage)] + passthrough, check=True)
    print("== ModParse done ==")


if __name__ == "__main__":
    main()
