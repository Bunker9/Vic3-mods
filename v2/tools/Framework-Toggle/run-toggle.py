#!/usr/bin/env python3
"""run-toggle.py (ss4 MASTER) — comment (--off) / uncomment (--on) debug_log + _fingerprint_ markers across a
TARGET: a single .txt file, a mod/repo FOLDER (walked for the config'd extensions), or a mod NAME resolved via
config_game.toml [mod_locations]. DRY-RUN by default; --commit writes. BOM + line endings preserved.

Each file is toggled through the SAME lib_toggle primitives ss2/ss1/ss3 use (marker toggle + empty-scope
collapse + post-toggle scope check), so the stages are shared via the importable lib rather than a subprocess
per file (DEV-RULES tooling-design: thin subs over one shared lib_*). Promote (Ceremony 3) = `--off --commit`
over each mod, then verify zero active markers per the save-fingerprint / debug-var discipline.
Usage: python run-toggle.py (--on|--off) [--commit] (<path> | --mod NAME | --path DIR)"""
import os
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_toggle, lib_io, lib_paths


def _targets(a, exts):
    """Resolve the target selector to a concrete list of files (honours the config'd extensions for folders)."""
    root = a.path or a.target
    if a.mod:
        root = (lib_paths.game_config().get("mod_locations", {}) or {}).get(a.mod)
        if not root:
            sys.exit(f"run-toggle: --mod {a.mod} not in config_game.toml [mod_locations].")
    if not root:
        sys.exit("run-toggle: give a target — <path>, --path DIR, or --mod NAME.")
    if os.path.isfile(root):
        return [root]
    if os.path.isdir(root):
        return [ap for _rel, ap, _fn in lib_io.walk_files(root, exts)]
    sys.exit(f"run-toggle: target not found: {root}")


def main():
    p = argparse.ArgumentParser(description="Toggle debug/fingerprint markers across a file / folder / mod.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--on", action="store_true", help="UNCOMMENT (enable) the markers")
    g.add_argument("--off", action="store_true", help="COMMENT (disable) the markers")
    p.add_argument("--commit", action="store_true", help="write files (default = dry-run)")
    p.add_argument("--mod", default=None, help="mod NAME (key in config_game.toml [mod_locations])")
    p.add_argument("--path", default=None, help="explicit folder/file (overrides the positional target)")
    p.add_argument("target", nargs="?", default=None, help="file OR folder to toggle")
    a = p.parse_args()
    cfg = lib_toggle.config(HERE)
    files = _targets(a, cfg["exts"])
    total, edited, flagged = 0, 0, 0
    for ap in files:
        n, marker_n, scope_n, text = lib_toggle.toggle_file(ap, a.on, cfg)
        if not n:
            continue
        edited += 1; total += n
        print(f"  {'EDIT' if a.commit else 'would edit'} {n:3d} ({marker_n} marker + {scope_n} scope)  {ap}")
        if a.commit:
            lib_toggle.write_file(ap, text)
            check_lines = lib_toggle.read_lines(ap)
        else:
            check_lines = text.splitlines(keepends=True)
        for prob in lib_toggle.check_scopes(check_lines, cfg):
            print(f"    !! scope-check {prob}"); flagged += 1
    state = "ON" if a.on else "OFF"
    print(f"toggle {state} {'(COMMIT)' if a.commit else '(dry-run)'}: {total} line(s) in {edited} file(s) "
          f"({len(files)} scanned; {flagged} scope-flag(s))" + ("" if a.commit else "  — pass --commit to apply"))


if __name__ == "__main__":
    main()
