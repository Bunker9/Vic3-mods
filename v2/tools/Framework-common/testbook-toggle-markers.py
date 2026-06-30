#!/usr/bin/env python3
"""testbook-toggle-markers.py — mod-agnostic debug/fingerprint TOGGLE. Comments (--off) or uncomments (--on),
across all configured mods (or --mod M / --path P), every line matching the config patterns (debug_log /
debug_log_scopes + any _fingerprint_ line). DRY-RUN by default; --commit rewrites files (BOM + line endings
preserved). Supersedes hk-config/scripts/testbook_toggle_debuglog.py. Patterns + extensions from
config_toggle.toml. Promote (Ceremony 3) = `--off --commit`; then verify zero active per the DEV-RULES
save-fingerprint / debug-var-standardization discipline. Cohesive utility (exceeds the 50-line glue target)."""
import os
import re
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_toggle.toml")["toggle"]
MARK = CFG["comment_marker"]
PATS = [re.compile(p) for p in CFG["patterns"]]
EXTS = set(CFG["extensions"])
_LEAD = re.compile(r"^(\s*)")
_UNCOMMENT = re.compile(r"^(\s*)" + re.escape(MARK) + r"\s?")


def _toggle_line(line, on):
    """Return (new_line, changed). Operates only on the leading part, so trailing newline is preserved."""
    stripped = line.lstrip()
    commented = stripped.startswith(MARK)
    code = stripped[len(MARK):].lstrip() if commented else stripped
    if not any(p.search(code) for p in PATS):
        return line, False
    if on and commented:
        return _UNCOMMENT.sub(r"\1", line, count=1), True
    if (not on) and (not commented):
        return _LEAD.sub(r"\1" + MARK + " ", line, count=1), True
    return line, False


def _mod_paths(args):
    if args.path:
        return [args.path]
    cfg = lib_paths.game_config().get("mod_locations", {}) or {}
    if args.mod:
        return [cfg[args.mod]] if args.mod in cfg else []
    return list(cfg.values())


def main():
    p = argparse.ArgumentParser(description="Toggle debug/fingerprint lines ON/OFF across mod source.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--on", action="store_true", help="UNCOMMENT (enable) the markers")
    g.add_argument("--off", action="store_true", help="COMMENT (disable) the markers")
    p.add_argument("--mod", default=None, help="one mod (key in config_game.toml mod_locations)")
    p.add_argument("--path", default=None, help="explicit mod source folder (overrides --mod)")
    p.add_argument("--commit", action="store_true", help="rewrite files (default = dry-run)")
    a = p.parse_args()
    paths = _mod_paths(a)
    if not paths:
        sys.exit("toggle: no mod paths (set config_game.toml [mod_locations], or pass --path/--mod).")
    total = 0
    for mp in paths:
        for _rel, ap, _fn in lib_io.walk_files(mp, EXTS):
            with open(ap, "r", encoding="utf-8-sig", newline="") as f:
                lines = f.read().splitlines(keepends=True)
            new = [_toggle_line(ln, a.on) for ln in lines]
            n = sum(1 for _l, c in new if c)
            if n:
                total += n
                print(f"  {'EDIT' if a.commit else 'would edit'} {n:3d} line(s)  {ap}")
                if a.commit:
                    with open(ap, "w", encoding="utf-8-sig", newline="") as f:
                        f.write("".join(l for l, _c in new))
    state = "ON" if a.on else "OFF"
    print(f"toggle {state} {'(COMMIT)' if a.commit else '(dry-run)'}: {total} line(s) across {len(paths)} mod(s)"
          + ("" if a.commit else "  — pass --commit to apply"))


if __name__ == "__main__":
    main()
