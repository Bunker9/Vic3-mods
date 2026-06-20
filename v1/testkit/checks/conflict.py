#!/usr/bin/env python3
"""
Mod-conflict check (SCAFFOLD, 2026-06-15) — for the new "Conflict" tab.

Vic3 loads mods in sequence; when two mods ship a file at the SAME relative path, the
later-loaded one OVERRIDES the earlier (silent). And a shared script-object NAME (event id,
scripted_effect, on_action, modifier) defined in different mods can clash too. This is a basic
first pass per the user's ask: assert file names / folder structure don't collide across mods.

Levels:
  HARD  - same RELATIVE PATH in 2+ mods  -> real file override (load-order dependent).
  SOFT  - same BASENAME in 2+ mods at different paths -> advisory (copy-paste / namespace risk).

TODO (deeper, later): parse same database-object NAMES across mods (event namespaces,
scripted_effects/_triggers, on_action sub-lists, modifier keys).

Usage: python conflict.py --mods <mod_dir> [<mod_dir> ...] [--json out.json]
"""
import os, json, argparse
from collections import defaultdict

# per-mod boilerplate that is SUPPOSED to exist in every mod (not a real collision)
IGNORE_BASENAMES = {"metadata.json", ".gitignore", "descriptor.mod", "thumbnail.png",
                    "CHANGELOG.md", "README.md"}
SCAN_EXT = (".txt", ".yml", ".json", ".gui", ".gfx")


def scan(mod_dirs):
    by_relpath = defaultdict(list)   # relpath -> [mod, ...]
    by_basename = defaultdict(list)  # basename -> [(mod, relpath), ...]
    mods = []
    for md in mod_dirs:
        mod = os.path.basename(os.path.normpath(md))
        mods.append(mod)
        for dp, dn, fns in os.walk(md):
            dn[:] = [d for d in dn if d not in (".git", ".vscode", ".claude", "__pycache__", ".metadata")]
            for fn in fns:
                if os.path.splitext(fn)[1].lower() not in SCAN_EXT:
                    continue
                if fn in IGNORE_BASENAMES:
                    continue
                rel = os.path.relpath(os.path.join(dp, fn), md).replace("\\", "/")
                by_relpath[rel].append(mod)
                by_basename[fn].append((mod, rel))
    return mods, by_relpath, by_basename


def run(mod_dirs):
    mods, by_relpath, by_basename = scan(mod_dirs)
    hard = [{"relpath": rp, "mods": sorted(set(ms))}
            for rp, ms in sorted(by_relpath.items()) if len(set(ms)) > 1]
    soft = []
    for bn, entries in sorted(by_basename.items()):
        modset = {m for m, _ in entries}
        if len(modset) > 1:
            # skip ones already flagged HARD (same relpath)
            rels = {r for _, r in entries}
            if any(len({m for m, r in entries if r == rr}) > 1 for rr in rels):
                continue
            soft.append({"basename": bn, "occurrences": [f"{m}:{r}" for m, r in entries]})
    return {
        "mods": mods,
        "hard": hard,   # same relative path across mods = real override
        "soft": soft,   # same basename, different paths = advisory
        "summary": {"hard": len(hard), "soft": len(soft),
                    "ok": len(hard) == 0},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mods", nargs="+", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    res = run(a.mods)
    print(f"Conflict check: {res['summary']['hard']} HARD, {res['summary']['soft']} SOFT "
          f"across {len(res['mods'])} mods")
    for h in res["hard"]:
        print(f"  HARD  {h['relpath']}  <- {', '.join(h['mods'])}")
    for s in res["soft"]:
        print(f"  soft  {s['basename']}  ({', '.join(s['occurrences'])})")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
