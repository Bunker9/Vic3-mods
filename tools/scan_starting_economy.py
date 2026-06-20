#!/usr/bin/env python3
"""
scan_starting_economy.py -- per-country 1836 goods production & consumption, using the
ACTUAL active production methods each starting building runs (not just the default PM).

WHY THE REWRITE (2026-06-14): the first version only read the *first* PM of each
production_method_group, which (a) ignored secondary/automation/harvesting PMs that are
actually switched on at 1836, and (b) never surfaced cross-use -- e.g. a furniture
manufactory's base PM consumes wood+fabric, a tooling secondary PM consumes tools/iron.
It also bucketed consumption to "industrial-category" goods only, so wood (a *staple*
good that is a major industrial input) showed zero consumption anywhere. Both are fixed
here: we resolve each building's real active PM per group and track produced AND consumed
for EVERY good regardless of vanilla category.

Method
------
For every building TYPE:
  building -> production_method_groups (common/buildings/*.txt)
  pmg      -> [production_methods]      (common/production_method_groups/*.txt; [0]=default)
  pm       -> goods_output_X_add / goods_input_X_add   (common/production_methods/*.txt)

For every starting building INSTANCE (common/history/buildings/*.txt):
  read `levels` (summed over all ownership shares) and `activate_production_methods`.
  Resolve the active PM *per group*: for each of the building's pmgs, pick the active PM
  that belongs to that group if the history lists one, else the group's default PM[0].
  (Per-building matching, so shared PM names like pm_tools_disabled resolve correctly.)
  Sum each resolved PM's goods I/O, multiply by levels, accumulate per tag.

These are still flat per-level base values -- NO throughput / SoL / market / building-
efficiency multipliers (per the user's "simple add, don't chase accuracy" instruction).
It is a relative yardstick across the 40 nations, not a calibrated in-game rate.

NOTE: subsistence buildings are NOT in history/buildings create_building lists (they're
auto-generated from each state's `subsistence_building`), so subsistence output is not
counted -- this is intentional (we care about market-facing production).

Output (hk-config/tools/):
  starting_economy_prod_cons.csv  -- one row per (tag, good):
      tag | country | good | category | produced | consumed | net
    where consumed = building-input demand (NOT pop needs; pop needs are added in the
    SoL-9 pass, scan_starting_economy_1836.py). net = produced - consumed.

Usage: python scan_starting_economy.py [GAME_DIR]
"""
import os, re, sys, csv, glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
from _refpaths import game_path
DEFAULT_GAME = game_path()


# --- brace helpers (regex-based, for the flat building/pmg/pm definition files) -----
def match_brace(text, i):
    d = 0
    for k in range(i, len(text)):
        if text[k] == "{":
            d += 1
        elif text[k] == "}":
            d -= 1
            if d == 0:
                return k
    return len(text) - 1


def block_for(text, name):
    m = re.search(re.escape(name) + r"\s*=\s*\{", text)
    if not m:
        return None
    i = m.end() - 1
    return text[i + 1:match_brace(text, i)]


def flat_idents(body):
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*", body) if body else []


# --- tokenizer/parser (for the nested history/buildings files) ----------------------
_T = re.compile(r"""\s+|\#[^\n]*|(?P<op>\?=|<=|>=|==|=|<|>)|(?P<lb>\{)|(?P<rb>\})|(?P<qs>"[^"]*")|(?P<w>[^\s{}=<>#"]+)""", re.VERBOSE)
def tok(t): return [m.group() for m in _T.finditer(t) if m.lastgroup in ("op", "lb", "rb", "qs", "w")]
def parse_block(ts, i):
    items, n = [], len(ts)
    while i < n:
        t = ts[i]
        if t == "}":
            return items, i + 1
        nx = ts[i + 1] if i + 1 < n else None
        if nx in ("=", "?=", "==", "<", ">", "<=", ">="):
            k, j = t, i + 2
            if j < n and ts[j] == "{":
                v, k2 = parse_block(ts, j + 1)
            else:
                v, k2 = (ts[j] if j < n else None), j + 1
            items.append((k, v)); i = k2
        elif t == "{":
            v, k2 = parse_block(ts, i + 1); items.append((None, v)); i = k2
        else:
            items.append(t); i += 1
    return items, i
def parse_file(p):
    with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
        return parse_block(tok(f.read()), 0)[0]
def unq(v): return v.strip('"') if isinstance(v, str) else v
def kv(items, key):
    for it in items:
        if isinstance(it, tuple) and it[0] == key:
            return it[1]
    return None
def kv_all(items, key):
    return [it[1] for it in items if isinstance(it, tuple) and it[0] == key]
def sum_levels(block):
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
def active_pms(block):
    """Flatten the activate_production_methods string list of a create_building block."""
    v = kv(block, "activate_production_methods")
    return [unq(x) for x in v if isinstance(x, str)] if isinstance(v, list) else []


# --- goods categories ---------------------------------------------------------------
def load_goods_categories(game):
    text = open(os.path.join(game, "common", "goods", "00_goods.txt"), encoding="utf-8-sig").read()
    cats = {}
    for m in re.finditer(r"^(\w+)\s*=\s*\{", text, re.MULTILINE):
        body = text[m.end() - 1:match_brace(text, m.end() - 1) + 1]
        cm = re.search(r"category\s*=\s*(\w+)", body)
        if cm:
            cats[m.group(1)] = cm.group(1)
    return cats


# --- building / pmg / pm maps -------------------------------------------------------
def load_building_pmgs(game):
    out = {}
    for fp in glob.glob(os.path.join(game, "common", "buildings", "*.txt")):
        text = open(fp, encoding="utf-8-sig").read()
        for m in re.finditer(r"^(building_\w+)\s*=\s*\{", text, re.MULTILINE):
            i = m.end() - 1
            body = text[i + 1:match_brace(text, i)]
            out[m.group(1)] = flat_idents(block_for(body, "production_method_groups"))
    return out

def load_pmg_members(game):
    out = {}
    for fp in glob.glob(os.path.join(game, "common", "production_method_groups", "*.txt")):
        text = open(fp, encoding="utf-8-sig").read()
        for m in re.finditer(r"^(pmg_\w+)\s*=\s*\{", text, re.MULTILINE):
            i = m.end() - 1
            body = text[i + 1:match_brace(text, i)]
            out[m.group(1)] = flat_idents(block_for(body, "production_methods"))
    return out

def load_pm_goods(game):
    out = {}
    for fp in glob.glob(os.path.join(game, "common", "production_methods", "*.txt")):
        text = open(fp, encoding="utf-8-sig").read()
        # PMs are named either pm_* OR default_building_* (the 15 plantation/farm base PMs).
        # Matching only pm_* silently dropped ALL plantation output (fabric/silk/tobacco/...).
        for m in re.finditer(r"^((?:pm_|default_building_)\w+)\s*=\s*\{", text, re.MULTILINE):
            i = m.end() - 1
            body = text[i + 1:match_brace(text, i)]
            o, n = defaultdict(float), defaultdict(float)
            for gm in re.finditer(r"goods_(output|input)_(\w+?)_add\s*=\s*([\d.]+)", body):
                (o if gm.group(1) == "output" else n)[gm.group(2)] += float(gm.group(3))
            out[m.group(1)] = (dict(o), dict(n))
    return out


def resolve_active(building, history_actives, building_pmgs, pmg_members):
    """Return the list of active PMs for one building instance (one per group)."""
    pmgs = building_pmgs.get(building, [])
    resolved = []
    for pmg in pmgs:
        members = pmg_members.get(pmg, [])
        chosen = members[0] if members else None        # default
        for ap in history_actives:
            if ap in members:
                chosen = ap                              # history override for this group
                break
        if chosen:
            resolved.append(chosen)
    return resolved


def main():
    game = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GAME
    if not os.path.isdir(game):
        sys.exit(f"Game dir not found: {game}")

    want = {}
    with open(os.path.join(HERE, "mod-nations.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            want[r["tag"]] = r["country"]

    print("Loading goods categories + PM maps ...")
    goods_cat = load_goods_categories(game)
    building_pmgs = load_building_pmgs(game)
    pmg_members = load_pmg_members(game)
    pm_goods = load_pm_goods(game)

    print("Parsing starting buildings (with active PMs) ...")
    produced = defaultdict(lambda: defaultdict(float))
    consumed = defaultdict(lambda: defaultdict(float))
    unresolved = defaultdict(int)
    for fp in glob.glob(os.path.join(game, "common", "history", "buildings", "*.txt")):
        for it in kv(parse_file(fp), "BUILDINGS") or []:
            if not (isinstance(it, tuple) and isinstance(it[0], str) and it[0].startswith("s:")):
                continue
            for sub in it[1] or []:
                if not (isinstance(sub, tuple) and isinstance(sub[0], str)):
                    continue
                if not sub[0].startswith("region_state:"):
                    continue
                tag = sub[0].split(":", 1)[1]
                if tag not in want:
                    continue
                for cb in kv_all(sub[1], "create_building"):
                    b = unq(kv(cb, "building"))
                    if not b:
                        continue
                    levels = sum_levels(cb)
                    if levels <= 0:
                        continue
                    actives = resolve_active(b, active_pms(cb), building_pmgs, pmg_members)
                    if not actives and building_pmgs.get(b):
                        unresolved[b] += 1
                    for pm in actives:
                        o, n = pm_goods.get(pm, ({}, {}))
                        for g, q in o.items():
                            produced[tag][g] += q * levels
                        for g, q in n.items():
                            consumed[tag][g] += q * levels

    # --- emit long-format prod/cons table --------------------------------------------
    all_goods = sorted(set(g for t in produced for g in produced[t])
                        | set(g for t in consumed for g in consumed[t]))
    out = os.path.join(HERE, "starting_economy_prod_cons.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tag", "country", "good", "category", "produced", "consumed", "net"])
        for tag in sorted(want, key=lambda t: want[t]):
            for g in all_goods:
                p = round(produced[tag].get(g, 0.0), 1)
                c = round(consumed[tag].get(g, 0.0), 1)
                if p == 0 and c == 0:
                    continue
                w.writerow([tag, want[tag], g, goods_cat.get(g, "?"), p, c, round(p - c, 1)])
    print(f"Wrote {os.path.basename(out)} ({len(all_goods)} distinct goods across {len(want)} nations)")
    if unresolved:
        print("  WARNING: buildings with pmgs but no resolved active PM:",
              dict(sorted(unresolved.items(), key=lambda x: -x[1])[:8]))


if __name__ == "__main__":
    main()
