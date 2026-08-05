#!/usr/bin/env python3
"""lib_toggle.py — shared core for the Framework-Toggle split (imported BY NAME by ss1-ss4, so it keeps the
underscore form per the DEV-RULES importable-module exception). Ported verbatim-in-spirit from the retired
Framework-common/testbook-toggle-markers.py (the proven _collapse_scopes), now parameterised by config and with
the empty-scope logic GATED to a configured scope-keyword set (config_toggle.toml [toggle].scope_keywords).

Primitives (all comment-agnostic so a commented block still round-trips):
  config(here)                  -> dict: marker, pats(compiled), exts(set), scopes(set)
  find_markers(lines, cfg)      -> [(lineno, text)]   (ss1: ext-toggle-markers)
  toggle_file(path, on, cfg)    -> (n, marker_n, scope_n, new_text)  BOM + line endings preserved (ss2/ss4)
  check_scopes(lines, cfg)      -> [problem str]       (ss3: chk-toggle-scopes)
The IO (read/write with utf-8-sig + newline='') lives in toggle_file so ss2 and ss4 stay thin."""
import os
import re
import lib_config   # Framework-common (callers add it to sys.path)

_OPENER = re.compile(r"^([A-Za-z_][\w:.]*)\s*=\s*\{")


def config(here):
    c = lib_config.load_framework_config(here, "config_toggle.toml")["toggle"]
    return {
        "marker": c["comment_marker"],
        "pats": [re.compile(p) for p in c["patterns"]],
        "exts": set(c["extensions"]),
        "scopes": set(c.get("scope_keywords", [])),
    }


# --- line-level primitives -----------------------------------------------------------------------------------
def _logical(line, marker):
    """The line's underlying CODE regardless of comment depth: strip leading comment markers + a trailing
    line-comment. Used for brace/structure + marker detection so a commented block is still seen structurally."""
    s = line.strip()
    while s.startswith(marker):
        s = s[len(marker):].lstrip()
    return s.split(marker, 1)[0]


def _has_marker(line, cfg):
    code = _logical(line, cfg["marker"])
    return any(p.search(code) for p in cfg["pats"])


def _is_active(line, marker):
    """True if the line is uncommented AND carries real code (not blank / not a pure comment)."""
    s = line.lstrip()
    if s.startswith(marker):
        return False
    return s.split(marker, 1)[0].strip() != ""


_MARKER_STMT = re.compile(r'\bdebug_log(_scopes)?\s*=\s*("[^"]*"|\S+)')
_FP_STMT = re.compile(r'\b\w+\s*=\s*\{[^{}]*_fingerprint_[^{}]*\}')
_BARE_FP = re.compile(r'\b\w*_fingerprint_\w*\b')


def _line_is_marker_only(code, cfg):
    """True if every statement on this ONE line is a marker or a wrapper around one, so commenting the
    whole line cannot delete real gameplay code. Guards the unanchored patterns (T125)."""
    rest = re.sub(r'"[^"]*"', '""', code)
    rest = _MARKER_STMT.sub(" ", rest)
    rest = _FP_STMT.sub(" ", rest)
    rest = re.sub(r'\blimit\s*=\s*\{[^{}]*\}', " ", rest)
    for kw in sorted(cfg["scopes"], key=len, reverse=True):        # `else = {`, `if = {`, ...
        rest = re.sub(r'\b' + re.escape(kw) + r'\s*=\s*\{', " ", rest)
        rest = re.sub(r'\b' + re.escape(kw) + r'\s*=\s*yes\b', " ", rest)
    rest = _BARE_FP.sub(" ", rest)
    return re.sub(r'[{}\s="]', "", rest) == ""


def _toggle_line(line, on, cfg):
    """Return (new_line, changed). Operates on the leading part only, so the trailing newline is preserved.
    A line whose marker shares space with real effects is left untouched (chk-toggle-scopes reports it)."""
    marker = cfg["marker"]
    lead = re.match(r"^(\s*)", line).group(1)
    stripped = line.lstrip()
    commented = stripped.startswith(marker)
    code = stripped[len(marker):].lstrip() if commented else stripped
    if not any(p.search(code) for p in cfg["pats"]):
        return line, False
    # _logical drops the trailing line-comment, so an end-of-line note (or a BDD tag) is not residue.
    if not _line_is_marker_only(_logical(line, marker), cfg):
        return line, False
    if on and commented:
        return re.sub(r"^(\s*)" + re.escape(marker) + r"\s?", r"\1", line, count=1), True
    if (not on) and (not commented):
        return lead + marker + " " + line[len(lead):], True
    return line, False


def _force_comment(line, marker):
    return line if line.lstrip().startswith(marker) else \
        re.match(r"^(\s*)", line).group(1) + marker + " " + line[len(re.match(r"^(\s*)", line).group(1)):]


def _force_uncomment(line, marker):
    return re.sub(r"^(\s*)" + re.escape(marker) + r"\s?", r"\1", line, count=1) \
        if line.lstrip().startswith(marker) else line


# --- brace tree + empty-scope collapse -----------------------------------------------------------------------
def _parse_blocks(lines, marker):
    """Comment-agnostic brace tree -> [{open, close, key, parent}]. The first '{' on a line takes that line's
    '<key> = {' name; extra braces on the same line get key=None."""
    stack, blocks = [], []
    for i, ln in enumerate(lines):
        logical = _logical(ln, marker)
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


def _collapse_scopes(lines, on, cfg):
    """Comment (--off) / uncomment (--on) the wrapper lines of marker-only nested scopes whose key is in the
    configured scope set. Iterates to a fixpoint so a parent emptied by its child is handled too. The `limit`
    sub-block is not counted as body. Returns (lines, wrapper_lines_changed)."""
    marker, scopes = cfg["marker"], cfg["scopes"]
    out, changed = list(lines), 0
    for _ in range(25):
        blocks = _parse_blocks(out, marker)
        did = False
        for b in sorted(blocks, key=lambda x: -x["open"]):        # innermost-first
            if b["close"] is None or b["parent"] is None or b["key"] not in scopes:
                continue                                          # unbalanced / top-level / not a wrapper we own
            limit_lines = set()
            for c in blocks:
                if c["parent"] is b and c["key"] == "limit" and c["close"] is not None:
                    limit_lines.update(range(c["open"], c["close"] + 1))
            if not any(_has_marker(out[i], cfg) for i in range(b["open"], b["close"] + 1)):
                continue                                          # only touch scopes that carry marker content
            body_active = any(_is_active(out[i], marker) for i in range(b["open"] + 1, b["close"])
                              if i not in limit_lines)
            wrapper = [b["open"], b["close"], *sorted(limit_lines)]
            if not on and not body_active and _is_active(out[b["open"]], marker):
                for i in wrapper:
                    if _is_active(out[i], marker):
                        out[i] = _force_comment(out[i], marker); changed += 1
                did = True
            elif on and body_active and not _is_active(out[b["open"]], marker):
                for i in wrapper:
                    if not _is_active(out[i], marker):
                        out[i] = _force_uncomment(out[i], marker); changed += 1
                did = True
        if not did:
            break
    return out, changed


# --- public API used by ss1-ss4 ------------------------------------------------------------------------------
def find_markers(lines, cfg):
    """ss1: (lineno[1-based], stripped text) for every marker line, commented or not."""
    return [(i + 1, ln.strip()) for i, ln in enumerate(lines) if _has_marker(ln, cfg)]


def check_scopes(lines, cfg):
    """ss3: structural problems after a toggle — brace imbalance, or an ACTIVE configured-scope opener whose
    body (excluding its `limit`) has no active line (an empty scope the collapse should have handled)."""
    marker = cfg["marker"]
    depth = 0
    for i, ln in enumerate(lines):
        for ch in _logical(ln, marker):
            depth += 1 if ch == "{" else -1 if ch == "}" else 0
            if depth < 0:
                return [f"line {i+1}: unbalanced '}}' (brace depth < 0)"]
    if depth != 0:
        return [f"brace imbalance: net depth {depth:+d} at EOF"]
    problems, blocks = [], _parse_blocks(lines, marker)
    for b in blocks:
        if b["close"] is None or b["key"] not in cfg["scopes"]:
            continue
        if b["close"] == b["open"]:
            continue                                              # single-line block: body shares the line (T126)
        if not _is_active(lines[b["open"]], marker):
            continue                                              # a commented-out scope is fine
        limit_lines = set()
        for c in blocks:
            if c["parent"] is b and c["key"] == "limit" and c["close"] is not None:
                limit_lines.update(range(c["open"], c["close"] + 1))
        if not any(_is_active(lines[i], marker) for i in range(b["open"] + 1, b["close"])
                   if i not in limit_lines):
            problems.append(f"line {b['open']+1}: active '{b['key']}' scope left empty (only a limit / comments)")
    return problems


def toggle_file(path, on, cfg):
    """ss2/ss4 worker: read PATH, toggle marker lines then collapse/restore marker-only scope wrappers, BOM +
    line endings preserved. Returns (total_changed, marker_changed, scope_changed, new_text)."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        lines = f.read().splitlines(keepends=True)
    toggled = [_toggle_line(ln, on, cfg)[0] for ln in lines]
    final, scope_n = _collapse_scopes(toggled, on, cfg)
    marker_n = sum(1 for o, t in zip(lines, toggled) if o != t)
    n = sum(1 for o, fnl in zip(lines, final) if o != fnl)
    return n, marker_n, scope_n, "".join(final)


def read_lines(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return f.read().splitlines(keepends=True)


def write_file(path, text):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)
