#!/usr/bin/env python3
"""
parse_country_stats.py — compile starting country stats from Victoria 3 history files.

Reads (read-only) from the game install:
  common/history/pops/*.txt        -> population (sum of create_pop.size per tag)
  common/history/states/*.txt      -> total/homeland state count + province count per tag
  common/history/buildings/*.txt   -> starting building levels per tag  (GDP PROXY)
  common/country_definitions/*.txt -> each country's primary cultures
  localization/english/countries_l_english.yml -> display names

Output columns: tag | country | rank | gdp_proxy | pop | homeland_states | total_states | provinces
  - pop / total_states / provinces are REAL (parsed straight from files).
  - homeland_states = owned states whose add_homeland culture(s) intersect the country's
    primary cultures (excludes colonial/foreign-culture states) -> the "core" economy.
  - gdp_proxy = total starting building levels owned (no stored GDP exists in files).
  - rank = ordinal by POPULATION (1 = largest), per the pop-first prioritisation.

Usage: python parse_country_stats.py [GAME_DIR] [--out country_stats.csv] [--top 40]
"""
import os, re, sys, csv, glob, argparse
from collections import defaultdict

DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game"

# --- minimal Paradox-script tokenizer / parser ------------------------------
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

# --- helpers ----------------------------------------------------------------
def kv(items, key):
    for it in items:
        if isinstance(it, tuple) and it[0] == key:
            return it[1]
    return None

def kv_all(items, key):
    return [it[1] for it in items if isinstance(it, tuple) and it[0] == key]

def clean_tag(v):
    if not isinstance(v, str): return None
    v = v.strip('"')
    return v.split(":", 1)[1] if v.startswith("c:") else (v or None)

def to_int(v):
    try: return int(float(str(v).strip('"')))
    except Exception: return 0

def iter_states(block, prefix="s:"):
    for it in block or []:
        if isinstance(it, tuple) and isinstance(it[0], str) and it[0].startswith(prefix):
            yield it[0], it[1]

def as_scalar_list(v):
    return [x for x in v if isinstance(x, str)] if isinstance(v, list) else []

# --- extractors -------------------------------------------------------------
def collect_cultures(game):
    cult = {}
    for fp in glob.glob(os.path.join(game, "common", "country_definitions", "*.txt")):
        for it in parse_file(fp):
            if isinstance(it, tuple) and isinstance(it[1], list):
                tag = it[0]
                cs = kv(it[1], "cultures")
                cult[tag] = set(as_scalar_list(cs))
    return cult

def collect_names(game):
    names = {}
    fp = os.path.join(game, "localization", "english", "countries_l_english.yml")
    rx = re.compile(r'^\s*([A-Za-z0-9_]+)\s*:\s*\d+\s+"(.*)"\s*$')
    with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            m = rx.match(line)
            if m: names[m.group(1)] = m.group(2)
    return names

def collect_pops(game):
    pops = defaultdict(int)
    for fp in glob.glob(os.path.join(game, "common", "history", "pops", "*.txt")):
        for _, st in iter_states(kv(parse_file(fp), "POPS") or []):
            for it in st:
                if isinstance(it, tuple) and isinstance(it[0], str) and it[0].startswith("region_state:"):
                    tag = it[0].split(":", 1)[1]
                    for cp in kv_all(it[1], "create_pop"):
                        pops[tag] += to_int(kv(cp, "size"))
    return pops

def collect_states(game, cultures):
    total, homeland, provs = defaultdict(int), defaultdict(int), defaultdict(int)
    for fp in glob.glob(os.path.join(game, "common", "history", "states", "*.txt")):
        for _, st in iter_states(kv(parse_file(fp), "STATES") or []):
            homelands = set()
            for hv in kv_all(st, "add_homeland"):
                if isinstance(hv, str):
                    homelands.add(hv.split(":", 1)[1] if ":" in hv else hv)
            for cs in kv_all(st, "create_state"):
                tag = clean_tag(kv(cs, "country"))
                if not tag: continue
                total[tag] += 1
                provs[tag] += len(as_scalar_list(kv(cs, "owned_provinces")))
                if cultures.get(tag, set()) & homelands:
                    homeland[tag] += 1
    return total, homeland, provs

def collect_building_levels(game):
    levels = defaultdict(int)
    def add_levels(cb, fallback):
        own = kv(cb, "add_ownership")
        if isinstance(own, list):
            for sub in own:
                if isinstance(sub, tuple) and isinstance(sub[1], list):
                    tag = clean_tag(kv(sub[1], "country")) or fallback
                    if tag: levels[tag] += to_int(kv(sub[1], "levels"))
    for fp in glob.glob(os.path.join(game, "common", "history", "buildings", "*.txt")):
        for _, st in iter_states(kv(parse_file(fp), "BUILDINGS") or []):
            for it in st:
                if not isinstance(it, tuple): continue
                key, val = it
                if isinstance(key, str) and key.startswith("region_state:"):
                    tag = key.split(":", 1)[1]
                    for cb in kv_all(val, "create_building"):
                        add_levels(cb, tag)
                elif key == "create_building":
                    add_levels(val, None)
    return levels

# --- main -------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("game", nargs="?", default=DEFAULT_GAME)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "country_stats.csv"))
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()
    if not os.path.isdir(args.game):
        sys.exit(f"Game dir not found: {args.game}")

    print("Parsing cultures, names, pops, states, buildings ...")
    cultures = collect_cultures(args.game)
    names = collect_names(args.game)
    pops = collect_pops(args.game)
    total, homeland, provs = collect_states(args.game, cultures)
    gdp = collect_building_levels(args.game)

    tags = set(total) | set(pops)
    rows = [{
        "tag": t,
        "country": names.get(t, t),
        "gdp_proxy": gdp.get(t, 0),
        "pop": pops.get(t, 0),
        "homeland_states": homeland.get(t, 0),
        "total_states": total.get(t, 0),
        "provinces": provs.get(t, 0),
    } for t in tags]
    rows.sort(key=lambda r: (r["pop"], r["gdp_proxy"]), reverse=True)   # rank by pop
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    cols = ["tag", "country", "rank", "gdp_proxy", "pop", "homeland_states", "total_states", "provinces"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c: r[c] for c in cols})

    print(f"\n{len(rows)} countries -> {args.out}\n")
    print(f"{'#':>3} {'tag':<4} {'country':<20} {'pop':>12} {'home':>4} {'tot':>4} {'gdp_x':>5}")
    print("-" * 56)
    for r in rows[:args.top]:
        print(f"{r['rank']:>3} {r['tag']:<4} {r['country'][:20]:<20} {r['pop']:>12,} "
              f"{r['homeland_states']:>4} {r['total_states']:>4} {r['gdp_proxy']:>5}")

if __name__ == "__main__":
    main()
