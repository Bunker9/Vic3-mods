#!/usr/bin/env python3
"""
parse_errors.py — group the game engine's cpp error.log into signatures for the v2 "Errors" view.

These are the in-game C++ data/script errors (the cpp files flag them). They are GAME-GLOBAL: they
reference the VANILLA file that threw them, not a mod marker, so they cannot be attributed per-mod
the way debug_log markers are. parse_log.py handles mod-marker attribution; THIS handles the raw
engine error stream.

Output: { "total": N, "groups": [ {signature, count, snippet[], ref_file, kind, note}, ... ] }
  kind: mod-data   — a mod's seeded DATA tripped a vanilla evaluation (e.g. trade centers under the
                     canton/sakoku law, or a seeded building over a state's capacity)
        mod-script — the snippet references a path under one of our mod folders
        vanilla?   — a vanilla file, but plausibly MOD-AMPLIFIED (more wars/fleets) or mod-triggered;
                     surfaced for human judgement, NOT auto-dismissed (a vanilla script_value div/0
                     can be caused by mod code that violates a game rule)
        vanilla    — engine/UI noise with no realistic mod link
        uncertain  — unclassified
Usage: python parse_errors.py [logs_dir]
"""
import os, re, sys, glob, collections

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from lib_paths import resolve_logs_dir
import lib_components as fb

# classification rules: (compiled regex on the snippet text) -> (kind, note)
RULES = [
    (re.compile(r"trade_center_trigger_tt|state_trade_center_max_limit_add", re.I),
     ("mod-data", "Trade-center evaluation under the canton/sakoku trade-policy law. Triggered by "
                  "InfraTax trade-center seeding in JAP/CHI states (fixed: those tags now get no "
                  "trade centers).")),
    (re.compile(r"can only support|its level will be reduced", re.I),
     ("mod-data", "A seeded building exceeds the state division's capacity (ownership share or "
                  "missing tech). Add a curated EXCLUDE or rely on the tier-6 tech grant.")),
    (re.compile(r"treaty_articles|_ship_transfer", re.I),
     ("vanilla?", "Vanilla peace-deal/ship-transfer article. Amplified by mod-added wars (more "
                  "peace negotiations) but the bug is vanilla's.")),
    (re.compile(r"NAVAL_BATTLE|BATTLE_SHIPS_BREAKDOWN|naval_battle", re.I),
     ("vanilla?", "Vanilla naval-combat UI. Amplified by mod-added fleets (troop ships) — worth a "
                  "look if it spikes.")),
    (re.compile(r"script_values/|jomini_scriptvalue|Div/0", re.I),
     ("vanilla?", "Vanilla script_value. A div/0 or wrong-type CAN be caused by a mod-created 0/edge "
                  "state — review the line before ruling out mod code.")),
    (re.compile(r"FindChild|TriggerAnimation|pdx_gui", re.I),
     ("vanilla", "Engine GUI animation noise. Not mod-related.")),
]


def _classify(snippet, mod_dirs):
    text = " ".join(snippet)
    for d in mod_dirs:
        if d and d.lower() in text.lower():
            return "mod-script", f"References a file under a mod folder ({d})."
    for rgx, (kind, note) in RULES:
        if rgx.search(text):
            return kind, note
    return "uncertain", ""


def _sig(line):
    s = re.sub(r"\d+", "#", line)
    s = re.sub(r'"[^"]*"', '"X"', s)
    s = re.sub(r"x[0-9A-Fa-f]{4,}", "xID", s)
    # drop the leading [HH:MM:SS][cpp:#] timestamp/loc prefix for grouping
    s = re.sub(r"^\[#:#:#\]\[[a-z_]+\.cpp:#\]:\s*", "", s)
    return s.strip()


def _ref_file(snippet):
    for l in snippet:
        m = re.search(r"((?:common|events|gfx|gui|map_data)/[\w./\- ]+\.\w+)", l)
        if m:
            return m.group(1)
    return ""


def run(logs_dir=None):
    logs_dir = logs_dir or resolve_logs_dir()
    path = os.path.join(logs_dir, "error.log") if logs_dir else None
    if not path or not os.path.isfile(path):
        return {"total": 0, "groups": [], "logs_dir": logs_dir}

    lines = open(path, encoding="utf-8-sig", errors="replace").read().splitlines()
    # mod folder names (for mod-script detection)
    mod_dirs = [d for d in os.listdir(fb.MOD1)
                if os.path.isdir(os.path.join(fb.MOD1, d))] if os.path.isdir(fb.MOD1) else []

    groups = collections.OrderedDict()   # sig -> {count, first_idx}
    for i, l in enumerate(lines):
        if not l.strip():
            continue
        k = _sig(l)
        g = groups.setdefault(k, {"count": 0, "first": i})
        g["count"] += 1

    out = []
    total = 0
    for sig, g in groups.items():
        total += g["count"]
        first = g["first"]
        # snippet = the error line + only its CONTINUATION lines (Error:/Script location:/indented),
        # i.e. following lines that do NOT begin a new timestamped entry. Avoids grabbing an
        # unrelated interleaved error's lines (which mis-classified the group).
        snip = [lines[first].rstrip()]
        j = first + 1
        while j < len(lines) and len(snip) < 5:
            nxt = lines[j]
            if nxt.strip() and not nxt.lstrip().startswith("["):
                snip.append(nxt.rstrip())
                j += 1
            else:
                break
        kind, note = _classify(snip, mod_dirs)
        out.append({
            "signature": sig[:200],
            "count": g["count"],
            "snippet": snip,
            "ref_file": _ref_file(snip),
            "kind": kind,
            "note": note,
        })
    out.sort(key=lambda x: -x["count"])
    return {"total": total, "groups": out, "logs_dir": logs_dir}


if __name__ == "__main__":
    d = run(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"total cpp errors: {d['total']}  ({len(d['groups'])} groups)")
    for g in d["groups"][:15]:
        print(f"  [{g['count']:>4}] {g['kind']:<10} {g['signature'][:80]}")
