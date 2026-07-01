#!/usr/bin/env python3
"""lib_args — the ONE standardized CLI arg contract for every framework script.

  arg1  MOD_NAME  (always, required) -> output namespace under Game-<game>/
  arg2  MOD_PATH  (opt; enable with mod_path=True) -> mod source folder
  --save / --logs (opt; enable per framework)
  --prefix        -> override the auto-derived mod prefix/abbr
  --rerun         -> force rebuild/re-scan (else reuse if present)
Each framework enables only the optional args it needs, so the same arg means the same thing everywhere."""
import argparse


def build_parser(desc, *, mod_path=False, save=False, logs=False):
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("mod_name", metavar="MOD_NAME",
                   help="mod basename; output namespace under Game-<game>/")
    if mod_path:
        p.add_argument("mod_path", metavar="MOD_PATH", nargs="?", default=None,
                       help="mod source folder (else resolved from config_game.toml mod_locations)")
    if save:
        p.add_argument("--save", default=None,
                       help="save file (.v3); else newest in the save-games dir")
    if logs:
        p.add_argument("--logs", default=None, help="override the Vic3 logs dir")
    p.add_argument("--prefix", default=None, help="override the auto-derived mod prefix/abbr")
    p.add_argument("--rerun", action="store_true",
                   help="force rebuild/re-scan (else reuse-if-present)")
    return p


def parse_args(desc, **kw):
    return build_parser(desc, **kw).parse_args()


# --- MASTER (multi-mod) front-end ------------------------------------------------------------------
# The MASTER orchestrators accept one-or-more MOD_NAMEs (or --all = every mod in config_game.toml
# [mod_locations]); they resolve the list, then invoke the single-mod SUB-scripts (above) once per mod.
# So the sub contract (arg1=MOD_NAME, arg2=MOD_PATH) is unchanged; only the masters take a mod LIST.

def build_master_parser(desc, *, mod_path=False, save=False, logs=False):
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("mod_names", metavar="MOD_NAME", nargs="*",
                   help="one or more mod basenames; omit and pass --all for every configured mod")
    p.add_argument("--all", action="store_true",
                   help="run for ALL mods in config_game.toml [mod_locations]")
    if mod_path:
        p.add_argument("--path", default=None,
                       help="explicit mod source folder (single MOD_NAME only; else from config_game.toml [mod_locations])")
    if save:
        p.add_argument("--save", default=None, help="save file (.v3); else newest in the save-games dir")
    if logs:
        p.add_argument("--logs", default=None, help="override the Vic3 logs dir")
    p.add_argument("--prefix", default=None, help="override the auto-derived mod prefix/abbr")
    p.add_argument("--rerun", action="store_true", help="force rebuild/re-scan (else reuse-if-present)")
    return p


def parse_master_args(desc, **kw):
    return build_master_parser(desc, **kw).parse_args()


def selected_mods(args):
    """The MOD_NAMEs a master will process: --all -> every config_game.toml [mod_locations] key; else the
    positional MOD_NAME list. Errors if neither yields a mod."""
    if getattr(args, "all", False):
        import lib_paths   # lazy: only masters need config
        mods = list((lib_paths.game_config().get("mod_locations", {}) or {}).keys())
        if not mods:
            raise SystemExit("--all: config_game.toml [mod_locations] is empty (add mods, or name them explicitly).")
        return mods
    if not args.mod_names:
        raise SystemExit("give one or more MOD_NAME, or --all (uses config_game.toml [mod_locations]).")
    return list(args.mod_names)
