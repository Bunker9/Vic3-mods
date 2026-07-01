#!/usr/bin/env python3
"""ext-mod-tokens.py — ModParse UNFILTERED token dump: every identifier used in the mod's `.txt` script
(incl. `if`/`else_if`/`limit`/`trigger`/`title`/effects/…), EXCLUDING commented-out code, with its occurrence
count → data-<Mod>/raw_tokens.csv (`keyword, occurrence`). No prefix/kind filter — the raw census of what the mod
writes, for the per-mod aggr stages to join against save/log. Standalone-runnable; the master invokes it as a
subprocess. Args: arg1=MOD_NAME, arg2=MOD_PATH (or config_game.toml [mod_locations])."""
import os
import sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config, lib_parse

CFG = lib_config.load_framework_config(HERE, "config_modparse.toml")


def _code(line):
    """The CODE portion of a line — a PDX `#` comment to end-of-line is stripped, so commented-out tokens are
    excluded from the dump."""
    return line.split("#", 1)[0]


def main(args):
    mod_path = lib_paths.resolve_mod_path(lib_paths.game_config(), args.mod_name, args.mod_path)
    if not mod_path:
        sys.exit("ext-mod-tokens: no MOD_PATH (arg2 or config_game.toml [mod_locations]).")
    counts = Counter()
    for _rel, ap, _fn in lib_io.walk_files(mod_path, {".txt"}):
        for line in lib_io.read_text_lines(ap):
            for tok in lib_parse.iter_identifiers([_code(line)]):
                counts[tok] += 1
    rows = [[kw, n] for kw, n in sorted(counts.items())]          # sorted -> idempotent output
    out = os.path.join(lib_paths.data_dir(args.mod_name), CFG["outputs"]["tokens"])
    lib_io.write_csv(out, ["keyword", "occurrence"], rows)
    print(f"  [tokens] {len(rows)} distinct ({sum(counts.values())} total) -> {out}")
    return out


if __name__ == "__main__":
    main(lib_args.parse_args("ModParse: unfiltered token dump.", mod_path=True))
