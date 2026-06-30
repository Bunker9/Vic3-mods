#!/usr/bin/env python3
"""ext-mod-files.py — ModParse extractor: the mod's source filenames -> data-<Mod>/raw_files.csv
(file_id, rel_path, basename). basename is the join key against the game logs. Standalone-runnable; the
master (run-modparse.py) invokes it as a subprocess. Args: arg1=MOD_NAME, arg2=MOD_PATH (or
config_game.toml [mod_locations])."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_modparse.toml")


def main(args):
    mod_path = lib_paths.resolve_mod_path(lib_paths.game_config(), args.mod_name, args.mod_path)
    if not mod_path:
        sys.exit("ext-mod-files: no MOD_PATH (arg2 or config_game.toml [mod_locations]).")
    files = lib_io.walk_files(mod_path, set(CFG["scan"]["extensions"]))
    rows = [[i, rel, base] for i, (rel, _ap, base) in enumerate(files, 1)]
    out = os.path.join(lib_paths.data_dir(args.mod_name), CFG["outputs"]["files"])
    lib_io.write_csv(out, ["file_id", "rel_path", "basename"], rows)
    print(f"  [files] {len(rows)} -> {out}")
    return out


if __name__ == "__main__":
    main(lib_args.parse_args("ModParse: extract mod source filenames.", mod_path=True))
