#!/usr/bin/env python3
"""
parse_state_buildings.py — per-state starting building counts for the Mod 1 nations.

Reads (read-only) from the Victoria 3 install:
  common/history/buildings/*.txt   -> create_building blocks per state (levels)
  common/buildings/*.txt           -> building -> building_group
  common/building_groups/*.txt     -> group hierarchy (-> lens/category label)
  localization/english/*states*.yml + countries_l_english.yml -> display names

Output: tools/state_buildings.csv with one row per (tag, state, building):
  tag | country | state | building | building_group | category | levels

`levels` = sum of every levels= inside the create_building (all ownership shares),
i.e. the physical level of that building in that state at 1836 start. Foreign-owned
shares are included (it's still a building sitting in that state).

Only the curated Mod 1 nations (tools/mod-nations.csv) are emitted, so you can pivot
country -> state -> building to pick champ / support / flavour goods.

Usage: python parse_state_buildings.py [GAME_DIR]
"""
import os, re, sys, csv, glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game"

# --- minimal Paradox-script tokenizer / parser (same as parse_country_stats) ---
_TOKEN_RE = re.compile(r"""
    \s+ | \#[^\n]*
  | (?P<op>\?=|<=|>=|==|=|<|>)
  | (?P<lb>\{) | (?P<rb>\})
  | (?P<qs>"[^"]*")
  | (?P<w>[^\s{}=<>#"]+)
""", re.VERBOSE)

def tokenize(text):
    return [m.group() for m in _TOKEN_RE.finditer(text)
            if m.lastgroup in ("op", "lb", "rb", "qs", "w")]

def parse_block(toks, i):
    items, n = [], len(toks)
    while i < n:
        t = toks[i]
        if t == "}":
            return items, i + 1
        nxt = toks[i + 1] if i + 1 < n else None
        if nxt in ("=", "?=", "==", "<", ">", "<=", ">="):
            key, j = t, i + 2
            if j < n and toks[j] == "{":
                val, k = parse_block(toks, j + 1)
            else:
                val, k = (toks[j] if j < n else None), j + 1
            items.append((key, val)); i = k
        elif t == "{":
            val, k = parse_block(toks, i + 1); items.append((None, val)); i = k
        else:
            items.append(t); i += 1
    return items, i

def parse_file(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return parse_block(tokenize(f.read()), 0)[0]

def kv(items, key):
    for it in items:
        if isinstance(it, tuple) and it[0] == key:
            return it[1]
    return None

def kv_all(items, key):
    return [it[1] for it in items if isinstance(it, tuple) and it[0] == key]

def unq(v):
    return v.strip('"') if isinstance(v, str) else v

def sum_levels(block):
    """Sum every levels= anywhere inside a create_building block."""
    total = 0
    for it in block or []:
        if isinstance(it, tuple):
            k, v = it
            if k == "levels":
                try: total += int(float(unq(v)))
                except Exception: pass
            elif isinstance(v, list):
                total += sum_levels(v)
        elif isinstance(it, list):
            total += sum_levels(it)
    return total

# --- building -> group -> readable category --------------------------------
def collect_building_groups(game):
    """group -> (parent, lens, category)."""
    groups = {}
    for fp in glob.glob(os.path.join(game, "common", "building_groups", "*.txt")):
        for it in parse_file(fp):
            if isinstance(it, tuple) and isinstance(it[1], list):
                g = it[0]
                groups[g] = (unq(kv(it[1], "parent_group")),
                             unq(kv(it[1], "lens")),
                             unq(kv(it[1], "category")))
    return groups

def resolve_category(group, groups, _seen=None):
    """Walk parents; first lens found wins, else first category, else group name."""
    seen = _seen or set()
    g = group
    lens = cat = None
    while g and g in groups and g not in seen:
        seen.add(g)
        parent, glens, gcat = groups[g]
        lens = lens or glens
        cat = cat or gcat
        g = parent
    return lens or cat or (group or "?")

def collect_building_meta(game):
    """building -> (group, category)."""
    groups = collect_building_groups(game)
    meta = {}
    for fp in glob.glob(os.path.join(game, "common", "buildings", "*.txt")):
        for it in parse_file(fp):
            if isinstance(it, tuple) and isinstance(it[1], list):
                b = it[0]
                grp = unq(kv(it[1], "building_group"))
                meta[b] = (grp or "", resolve_category(grp, groups))
    return meta

# --- names ------------------------------------------------------------------
def load_loc(game, *globs):
    names = {}
    rx = re.compile(r'^\s*([A-Za-z0-9_]+)\s*:\s*\d*\s*"(.*)"\s*$')
    for gpat in globs:
        for fp in glob.glob(os.path.join(game, "localization", "english", gpat)):
            with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
                for line in f:
                    m = rx.match(line)
                    if m: names.setdefault(m.group(1), m.group(2))
    return names

def main():
    game = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GAME
    if not os.path.isdir(game):
        sys.exit(f"Game dir not found: {game}")

    # curated Mod 1 tags + display names
    want = {}
    with open(os.path.join(HERE, "mod-nations.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            want[r["tag"]] = r["country"]

    print("Loading building metadata + names ...")
    bmeta = collect_building_meta(game)
    state_names = load_loc(game, "*state_regions*l_english.yml", "*states*l_english.yml")

    rows = []
    for fp in glob.glob(os.path.join(game, "common", "history", "buildings", "*.txt")):
        for it in kv(parse_file(fp), "BUILDINGS") or []:
            if not (isinstance(it, tuple) and isinstance(it[0], str)
                    and it[0].startswith("s:")):
                continue
            state_key = it[0].split(":", 1)[1]
            for sub in it[1] or []:
                if not (isinstance(sub, tuple) and isinstance(sub[0], str)):
                    continue
                # region_state:TAG = { create_building ... }
                if sub[0].startswith("region_state:"):
                    tag = sub[0].split(":", 1)[1]
                    cbs = kv_all(sub[1], "create_building")
                elif sub[0] == "create_building":
                    continue  # no owner tag at this level — skip
                else:
                    continue
                if tag not in want:
                    continue
                for cb in cbs:
                    b = unq(kv(cb, "building"))
                    if not b:
                        continue
                    grp, cat = bmeta.get(b, ("", "?"))
                    rows.append({
                        "tag": tag,
                        "country": want[tag],
                        "state": state_names.get(state_key, state_key.replace("STATE_", "")),
                        "building": b.replace("building_", ""),
                        "building_group": grp.replace("bg_", ""),
                        "category": cat,
                        "levels": sum_levels(cb),
                    })

    rows.sort(key=lambda r: (r["country"], r["state"], -r["levels"], r["building"]))
    out = os.path.join(HERE, "state_buildings.csv")
    cols = ["tag", "country", "state", "building", "building_group", "category", "levels"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

    # quick console summary: total levels per category per country
    by_cat = defaultdict(lambda: defaultdict(int))
    for r in rows:
        by_cat[r["country"]][r["category"]] += r["levels"]
    print(f"\n{len(rows)} (state,building) rows for {len(want)} nations -> {out}")
    print(f"states with buildings: {len(set((r['tag'], r['state']) for r in rows))}\n")

if __name__ == "__main__":
    main()
