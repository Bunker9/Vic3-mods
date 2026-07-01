#!/usr/bin/env python3
"""testbook-toggle-markers.py — mod-agnostic debug/fingerprint TOGGLE. Comments (--off) or uncomments (--on),
across all configured mods (or --mod M / --path P), every line matching the config patterns (debug_log /
debug_log_scopes + any _fingerprint_ line). DRY-RUN by default; --commit rewrites files (BOM + line endings
preserved). Supersedes hk-config/scripts/testbook_toggle_debuglog.py. Patterns + extensions from
config_toggle.toml. Promote (Ceremony 3) = `--off --commit`; then verify zero active per the DEV-RULES
save-fingerprint / debug-var-standardization discipline. Cohesive utility (exceeds the 50-line glue target).

Also runs an EMPTY-SCOPE collapse (`_collapse_scopes`): after commenting fp/debug lines, a nested scope whose only
body was fingerprints (e.g. `if = { limit = {..} <fp> }`) is left dead, so its wrapper lines (opener, the `limit`
sub-block, and the matching `}`) are commented too (`--on` restores them). The `limit` is NOT counted as body;
scopes with any real code are untouched. Fixes the eco_effects.txt:257 case the marker-only toggle missed."""
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


# --- empty-scope collapse -------------------------------------------------------------------------------------
# Toggling fp/debug lines OFF can leave a scope whose ONLY body was fingerprints — e.g. `if = { limit = {..} <fp> }`
# becomes an `if` with just a limit and no effect (the eco_effects.txt:257 TODO). This pass comments the WRAPPER
# lines (the scope opener, its `limit` sub-block, and the matching `}`) of any nested scope whose body — counting
# everything EXCEPT a `limit` sub-block — is left with no active code; `--on` reverses it. Structure is parsed
# comment-agnostically (a commented `# if = {` still counts its brace) so it round-trips.
_OPENER = re.compile(r"^([A-Za-z_][\w:.]*)\s*=\s*\{")


def _logical(line):
    """The line's underlying CODE regardless of comment depth: strip any leading comment markers + a trailing
    line-comment. Used for brace/structure + fp detection (so a commented-out block is still seen structurally)."""
    s = line.strip()
    while s.startswith(MARK):
        s = s[len(MARK):].lstrip()
    return s.split(MARK, 1)[0]


def _is_active(line):
    """True if the line is uncommented AND carries real code (not blank / not a comment)."""
    s = line.lstrip()
    if s.startswith(MARK):
        return False
    return s.split(MARK, 1)[0].strip() != ""


def _has_fp(line):
    return any(p.search(_logical(line)) for p in PATS)


def _force_comment(line):
    return line if line.lstrip().startswith(MARK) else _LEAD.sub(r"\1" + MARK + " ", line, count=1)


def _force_uncomment(line):
    return _UNCOMMENT.sub(r"\1", line, count=1) if line.lstrip().startswith(MARK) else line


def _parse_blocks(lines):
    """Comment-agnostic brace tree -> list of blocks {open, close, key, parent}. The first `{` on a line takes
    that line's `<key> = {` name; extra braces on the same line (rare here) get key=None."""
    stack, blocks = [], []
    for i, ln in enumerate(lines):
        logical = _logical(ln)
        m = _OPENER.match(logical)
        key, first = (m.group(1) if m else None), True
        for ch in logical:
            if ch == "{":
                b = {"open": i, "close": None, "key": key if first else None,
                     "parent": stack[-1] if stack else None}
                first = False
                stack.append(b); blocks.append(b)
            elif ch == "}" and stack:
                stack.pop()["close"] = i
    return blocks


def _collapse_scopes(lines, on):
    """Comment (--off) / uncomment (--on) the wrapper lines of fp-only nested scopes. Iterates to a fixpoint so a
    parent that becomes empty after its child collapses is handled too. Returns (lines, wrapper_lines_changed)."""
    out, changed = list(lines), 0
    for _ in range(25):
        blocks = _parse_blocks(out)
        did = False
        for b in sorted(blocks, key=lambda x: -x["open"]):        # innermost-first
            if b["close"] is None or b["parent"] is None or b["key"] == "limit":
                continue                                          # unbalanced / top-level def / a limit itself
            limit_lines = set()
            for c in blocks:
                if c["parent"] is b and c["key"] == "limit" and c["close"] is not None:
                    limit_lines.update(range(c["open"], c["close"] + 1))
            if not any(_has_fp(out[i]) for i in range(b["open"], b["close"] + 1)):
                continue                                          # only touch scopes that carry fp/debug content
            body_active = any(_is_active(out[i]) for i in range(b["open"] + 1, b["close"])
                              if i not in limit_lines)
            wrapper = [b["open"], b["close"], *sorted(limit_lines)]
            if not on and not body_active and _is_active(out[b["open"]]):
                for i in wrapper:
                    if _is_active(out[i]):
                        out[i] = _force_comment(out[i]); changed += 1
                did = True
            elif on and body_active and not _is_active(out[b["open"]]):
                for i in wrapper:
                    if not _is_active(out[i]):
                        out[i] = _force_uncomment(out[i]); changed += 1
                did = True
        if not did:
            break
    return out, changed


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
            toggled = [_toggle_line(ln, a.on)[0] for ln in lines]     # 1) marker lines (debug_log / _fingerprint_)
            final, scope_n = _collapse_scopes(toggled, a.on)          # 2) collapse/restore fp-only scope wrappers
            marker_n = sum(1 for o, t in zip(lines, toggled) if o != t)
            n = sum(1 for o, fnl in zip(lines, final) if o != fnl)
            if n:
                total += n
                print(f"  {'EDIT' if a.commit else 'would edit'} {n:3d} line(s) "
                      f"({marker_n} marker + {scope_n} scope)  {ap}")
                if a.commit:
                    with open(ap, "w", encoding="utf-8-sig", newline="") as f:
                        f.write("".join(final))
    state = "ON" if a.on else "OFF"
    print(f"toggle {state} {'(COMMIT)' if a.commit else '(dry-run)'}: {total} line(s) across {len(paths)} mod(s)"
          + ("" if a.commit else "  — pass --commit to apply"))


if __name__ == "__main__":
    main()
