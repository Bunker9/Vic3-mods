#!/usr/bin/env python3
"""
parse_country_stats.py — compile starting country stats from Victoria 3 history files.

Reads (read-only) from the game install:
  common/history/pops/*.txt       -> population (sum of create_pop.size per tag)
  common/history/states/*.txt     -> state count + province count per tag
  common/history/buildings/*.txt  -> starting building levels per tag  (GDP PROXY)

Outputs: country | rank | gdp_proxy | pop | states | provinces
  - pop / states / provinces are REAL (parsed straight from files).
  - gdp_proxy = total starting building levels owned by the country. Vic3 has NO
    stored starting GDP (it is computed at runtime), so this is a stand-in that
    correlates with economic size. Treat as relative, not absolute.
  - rank = ordinal (1 = largest) by gdp_proxy. True Vic3 ranks (Great/Major/Minor/
    Unrecognized) are runtime prestige calculations and are NOT in the files.

Usage:
  python parse_country_stats.py [GAME_DIR] [--out country_stats.csv] [--top 40]
Default GAME_DIR = the local Steam install path.
"""
import os, re, sys, csv, glob, argparse
from collections import defaultdict

DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game"

# --- minimal Paradox-script tokenizer / parser -----------------------------
_TOKEN_RE = re.compile(r"""
    \s+                # whitespace
  | \#[^\n]*           # comment
  | (?P<op>\?=|<=|>=|==|=|<|>)   # operators (treat all like '=')
  | (?P<lb>\{) | (?P<rb>\})
  | (?P<qs>"[^"]*")    # quoted string
  | (?P<w>[^\s{}=<>#"]+)         # bare word / number / tag / province id
""", re.VERBOSE)

def tokenize(text):
    toks = []
    for m in _TOKEN_RE.finditer(text):
        g = m.lastgroup
        if g in ("op", "lb", "rb", "qs", "w"):
            toks.append(m.group())
    return toks

def parse_block(toks, i):
    """Parse '{'-less block contents until a '}' or end. Returns (items, next_i).
       items: list of either scalar str, or (key, value) where value is scalar or list."""
    items = []
    n = len(toks)
    while i < n:
        t = toks[i]
        if t == "}":
            return items, i + 1
        nxt = toks[i + 1] if i + 1 < n else None
        if nxt in ("=", "?=", "==", "<", ">", "<=", ">="):
            key = t
            j = i + 2
            if j < n and toks[j] == "{":
                val, k = parse_block(toks, j + 1)
            else:
                val, k = (toks[j] if j < n else None), j + 1
            items.append((key, val))
            i = k
        elif t == "{":
            val, k = parse_block(toks, i + 1)
            items.append((None, val))
            i = k
        else:
            items.append(t)
            i += 1
    return items, i

def parse_file(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        toks = tokenize(f.read())
    items, _ = parse_block(toks, 0)
    return items

# --- helpers ----------------------------------------------------------------
def kv(items, key):
    for it in items:
        if isinstance(it, tuple) and it[0] == key:
            return it[1]
    return None

def kv_all(items, key):
    return [it[1] for it in items if isinstance(it, tuple) and it[0] == key]

def clean_tag(v):
    if not isinstance(v, str):
        return None
    v = v.strip('"')
    return v.split(":", 1)[1] if v.startswith("c:") else (v if v else None)

def to_int(v):
    try:
        return int(float(str(v).strip('"')))
    except Exception:
        return 0

def iter_states(block, prefix="s:"):
    """yield (state_name, state_items) for entries keyed s:STATE_*"""
    for it in block or []:
        if isinstance(it, tuple) and isinstance(it[0], str) and it[0].startswith(prefix):
            yield it[0], it[1]

# --- extractors -------------------------------------------------------------
def collect_pops(game):
    pops = defaultdict(int)
    for fp in glob.glob(os.path.join(game, "common", "history", "pops", "*.txt")):
        root = kv(parse_file(fp), "POPS") or []
        for _, st in iter_states(root):
            for it in st:
                if isinstance(it, tuple) and isinstance(it[0], str) and it[0].startswith("region_state:"):
                    tag = it[0].split(":", 1)[1]
                    for cp in kv_all(it[1], "create_pop"):
                        pops[tag] += to_int(kv(cp, "size"))
    return pops

def collect_states(game):
    states = defaultdict(int)
    provs = defaultdict(int)
    for fp in glob.glob(os.path.join(game, "common", "history", "states", "*.txt")):
        root = kv(parse_file(fp), "STATES") or []
        for _, st in iter_states(root):
            for cs in kv_all(st, "create_state"):
                tag = clean_tag(kv(cs, "country"))
                if not tag:
                    continue
                states[tag] += 1
                op = kv(cs, "owned_provinces")
                provs[tag] += sum(1 for x in op if isinstance(x, str)) if isinstance(op, list) else 0
    return states, provs

def collect_building_levels(game):
    """GDP proxy: sum building levels per owning country tag."""
    levels = defaultdict(int)
    def add_ownership_levels(cb, fallback_tag):
        own = kv(cb, "add_ownership")
        if not isinstance(own, list):
            if fallback_tag:
                levels[fallback_tag] += 0
            return
        for sub in own:  # country={...} building={...} company={...}
            if isinstance(sub, tuple) and isinstance(sub[1], list):
                tag = clean_tag(kv(sub[1], "country")) or fallback_tag
                if tag:
                    levels[tag] += to_int(kv(sub[1], "levels"))
    for fp in glob.glob(os.path.join(game, "common", "history", "buildings", "*.txt")):
        root = kv(parse_file(fp), "BUILDINGS") or []
        for _, st in iter_states(root):
            for it in st:
                if not isinstance(it, tuple):
                    continue
                key, val = it
                if isinstance(key, str) and key.startswith("region_state:"):
                    tag = key.split(":", 1)[1]
                    for cb in kv_all(val, "create_building"):
                        add_ownership_levels(cb, tag)
                elif key == "create_building":
                    add_ownership_levels(val, None)
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

    print("Parsing pops, states, buildings ...")
    pops = collect_pops(args.game)
    states, provs = collect_states(args.game)
    gdp = collect_building_levels(args.game)

    tags = set(states) | set(pops)            # countries that own land or have pops at start
    rows = []
    for t in tags:
        rows.append({
            "country": t,
            "gdp_proxy": gdp.get(t, 0),
            "pop": pops.get(t, 0),
            "states": states.get(t, 0),
            "provinces": provs.get(t, 0),
        })
    rows.sort(key=lambda r: (r["gdp_proxy"], r["pop"]), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    cols = ["country", "rank", "gdp_proxy", "pop", "states", "provinces"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})

    print(f"\n{len(rows)} countries written to {args.out}\n")
    print(f"{'rank':>4}  {'tag':<5} {'gdp_proxy':>9} {'pop':>12} {'states':>6} {'prov':>5}")
    print("-" * 50)
    for r in rows[:args.top]:
        print(f"{r['rank']:>4}  {r['country']:<5} {r['gdp_proxy']:>9} {r['pop']:>12,} {r['states']:>6} {r['provinces']:>5}")

if __name__ == "__main__":
    main()
