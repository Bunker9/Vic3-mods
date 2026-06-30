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
                       help="mod source folder (else resolved from config-game.toml mod_locations)")
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
