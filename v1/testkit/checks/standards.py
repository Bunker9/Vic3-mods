#!/usr/bin/env python3
"""
Authoring-STANDARDS check for a single Vic3 mod (the "Standards" data source).

Complements structure.py (which does encoding/brace/quote). This one inspects mod *objects*
(modifiers, events) for the authoring mistakes that have actually shipped as bugs, and grades
each object green / yellow:

  green  = meets the standard
  yellow = sub-standard / likely-malformed (shows wrong in-game or spams the error log)

Rules (deliberately ZERO-false-positive; dependency-free — no game files, CI-safe):
  MOD-ICON  every modifier definition has `icon =`        (no icon + shown on a scope => the
                                                            VFSOpen missing-texture flood, cf.
                                                            bug T25/D.1.4 in Top40)
  MOD-LOC   every modifier name has a localization key      (else the name renders as raw key)
  EVT-PIC   a player-facing event (has option {}) has a     (a shown event with no picture reads
            `picture =`                                       as unfinished)

Explicitly OUT OF SCOPE (needs semantics / a token dump, not a static rule — would be
false-positive-prone): "is this the *right* modifier type" (the T24/D.1.3 class) and
unknown-token detection. Those stay a human design-review item; see T12/T29.

  LOC-DASH   no '-' or '—' in player-facing .yml loc strings    (dashes are debug-only — spams
             (option / event title / desc / modifier name keys)   wrong display in-game, cf. rule
                                                                  established 2026-06)
  EFF-REMOVE bare `remove_modifier =` without an `has_modifier`  (fires a script error for every
             guard in a `limit =` block                           country that lacks the modifier,
                                                                  cf. 1084-error incident 2026-06)

Explicitly OUT OF SCOPE (needs semantics / a token dump, not a static rule — would be
false-positive-prone): "is this the *right* modifier type" (the T24/D.1.3 class) and
unknown-token detection. Those stay a human design-review item; see T12/T29.

Refs: https://vic3.paradoxwikis.com/Modding  (rule set to be expanded from the wiki — T12).

Usage:
    python standards.py <path-to-mod-folder> [--json out.json]
"""
import sys, os, re, json, argparse, datetime

IDENT = r"[A-Za-z_][A-Za-z0-9_.]*"


def read_text(p):
    with open(p, "rb") as f:
        return f.read().decode("utf-8-sig", errors="replace")


def iter_top_blocks(text):
    """Yield (name, inner_text, line_no) for every top-level `name = { ... }` block.
    Brace-aware; skips '#'-comments and quoted strings when tracking depth."""
    n = len(text)
    head_re = re.compile(rf"({IDENT})\s*=\s*$")
    out, pending, depth, j = [], None, 0, 0
    while j < n:
        c = text[j]
        if c == "#":                                  # line comment
            nl = text.find("\n", j)
            j = n if nl < 0 else nl
        elif c == '"':                                # quoted string
            k = text.find('"', j + 1)
            j = n if k < 0 else k + 1
        elif c == "{":
            if depth == 0:                            # capture the `ident =` just before it
                mm = head_re.search(text, 0, j)
                if mm:
                    pending = (mm.group(1), j + 1, text.count("\n", 0, mm.start(1)) + 1)
            depth += 1
            j += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and pending:
                name, start, ln = pending
                out.append((name, text[start:j], ln))
                pending = None
            j += 1
        else:
            j += 1
    return out


def load_loc_keys(mod_dir):
    keys = set()
    locdir = os.path.join(mod_dir, "localization")
    for dp, _, fns in os.walk(locdir):
        for fn in fns:
            if fn.endswith(".yml"):
                for ln in read_text(os.path.join(dp, fn)).splitlines():
                    m = re.match(rf"\s*({IDENT})\s*:", ln)
                    if m:
                        keys.add(m.group(1))
    return keys


def glob_txt(mod_dir, *subparts):
    base = os.path.join(mod_dir, *subparts)
    if not os.path.isdir(base):
        return []
    out = []
    for dp, _, fns in os.walk(base):
        out += [os.path.join(dp, fn) for fn in fns if fn.endswith(".txt")]
    return out


def run(mod_dir):
    mod = os.path.basename(os.path.normpath(mod_dir))
    loc_keys = load_loc_keys(mod_dir)
    findings = []

    def add(obj, rule, sev, msg, rel, line):
        findings.append({"object": obj, "rule": rule, "severity": sev,
                         "msg": msg, "file": rel.replace("\\", "/"), "line": line})

    # --- modifiers: icon + loc -------------------------------------------------
    mod_files = glob_txt(mod_dir, "common", "static_modifiers") + \
        glob_txt(mod_dir, "common", "modifiers")
    for path in mod_files:
        rel = os.path.relpath(path, mod_dir)
        text = read_text(path)
        for name, inner, ln in iter_top_blocks(text):
            if not re.search(r"\bicon\s*=", inner):
                add(name, "MOD-ICON", "yellow",
                    "modifier has no icon= (if shown on a scope this floods VFSOpen "
                    "missing-texture errors)", rel, ln)
            if name not in loc_keys:
                add(name, "MOD-LOC", "yellow",
                    "no localization key (name will render as the raw token)", rel, ln)

    # --- events: player-facing event should have a picture ---------------------
    for path in glob_txt(mod_dir, "events"):
        rel = os.path.relpath(path, mod_dir)
        text = read_text(path)
        for name, inner, ln in iter_top_blocks(text):
            if "." not in name:           # event ids look like ns.NN; skip stray blocks
                continue
            has_option = re.search(r"\boption\s*=\s*{", inner)
            hidden = re.search(r"\bhidden\s*=\s*yes", inner)
            imaged = re.search(r"\b(picture|gfx|event_image)\s*=", inner)
            if has_option and not hidden and not imaged:
                add(name, "EVT-PIC", "yellow",
                    "player-facing event (has option) with no picture/event_image=", rel, ln)

    # --- localization: no dash in player-facing strings -------------------------
    # Dashes render wrong in Vic3 UI and were a repeated session bug (2026-06).
    # Checked keys: event title (.t), desc (.d), option names, modifier names.
    # Excludes debug/internal keys (those explicitly labelled for debug use are OK).
    _DASH_PLAYER_KEY = re.compile(
        r"^\s+(\w+(?:\.t|\.d|\.desc|\.\d+[a-z]*|_desc|_name|_desc_short)?)\s*:\s*\d+\s*\"([^\"]*[-—][^\"]*)\""
    )
    locdir = os.path.join(mod_dir, "localization")
    for dp, _, fns in os.walk(locdir):
        for fn in fns:
            if not fn.endswith(".yml"):
                continue
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, mod_dir)
            for lno, raw in enumerate(read_text(path).splitlines(), 1):
                m = _DASH_PLAYER_KEY.match(raw)
                if m:
                    key, val = m.group(1), m.group(2)
                    # Skip debug-prefix keys or FORTESTLOG values (intentional debug dashes)
                    if key.startswith("debug_") or val.startswith("FORTESTLOG"):
                        continue
                    add(key, "LOC-DASH", "yellow",
                        f"dash in player-facing loc string: {val[:60]!r}", rel, lno)

    # --- scripted effects: bare remove_modifier without has_modifier guard ------
    # Bare remove_modifier on an absent modifier fires a script error per-country.
    # Pattern: find `remove_modifier = X` lines NOT inside a `limit = { has_modifier` block.
    # Heuristic: flag any remove_modifier whose preceding non-blank line is NOT a has_modifier.
    _REMOVE_RX = re.compile(r"^\s+remove_modifier\s*=\s*\S")
    _HASMODI_RX = re.compile(r"has_modifier\s*=")
    for path in glob_txt(mod_dir, "common", "scripted_effects"):
        rel = os.path.relpath(path, mod_dir)
        lines = read_text(path).splitlines()
        for lno, ln in enumerate(lines, 1):
            if not _REMOVE_RX.match(ln):
                continue
            # Check the preceding 4 lines for a has_modifier guard
            window = "\n".join(lines[max(0, lno - 5):lno])
            if not _HASMODI_RX.search(window):
                add(f"line {lno}", "EFF-REMOVE", "yellow",
                    f"bare remove_modifier without has_modifier guard: {ln.strip()!r}", rel, lno)

    objects_checked = len({f["object"] for f in findings}) if findings else 0
    yellow = sum(1 for f in findings if f["severity"] == "yellow")
    red = sum(1 for f in findings if f["severity"] == "red")
    return {
        "mod": mod,
        "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "findings": findings,
        "summary": {"yellow": yellow, "red": red, "flagged_objects": objects_checked},
    }


def print_summary(res):
    print(f"\n=== STANDARDS: {res['mod']} ===")
    if not res["findings"]:
        print("  all clear (green)")
    for f in res["findings"]:
        tag = "YEL" if f["severity"] == "yellow" else "RED"
        print(f"  [{tag}] {f['rule']:8} {f['object']:24} {f['file']}:{f['line']}  {f['msg']}")
    s = res["summary"]
    print(f"  ---- {s['yellow']} yellow, {s['red']} red over {s['flagged_objects']} object(s) ----")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mod_dir")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = run(a.mod_dir)
    print_summary(res)
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)) or ".", exist_ok=True)
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        print(f"  json -> {a.json}")
    sys.exit(0)   # advisory: never fails the build (green/yellow only)
