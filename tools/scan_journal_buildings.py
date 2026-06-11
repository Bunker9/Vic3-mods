#!/usr/bin/env python3
"""
scan_journal_buildings.py — first-pass scan of journal entries + decisions for the
building requirements that matter to the Mod 1 nations.

Goal: a scaffold to help decide what to nudge the AI to build (beyond champ/support/
flavour) so the 40 nations can actually progress their journals/decisions. Buildings
here are ANY type (infrastructure, admin, military, monuments, industry, ...), not just
economic goods.

Reads (read-only): common/journal_entries/*.txt and common/decisions/*.txt
Outputs:
  tools/journal_building_refs.csv   one row per (source, entry) that references a building
  tools/journal-building-notes.md   the same, grouped by Mod 1 nation, for perusal

⚠️ FIRST-PASS / APPROXIMATE. Country gating is inferred from c:TAG / can_form_nation
tokens in the entry; "count_hint" is any nearby numeric threshold and may be noise.
Treat as a starting map to refine by hand against the wiki, not ground truth.

Usage: python scan_journal_buildings.py [GAME_DIR]
"""
import os, re, sys, csv, glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
from _refpaths import game_path
DEFAULT_GAME = game_path()

# tokenizer / parser (shared shape with the other tools) ---------------------
_TOKEN_RE = re.compile(r"""\s+|\#[^\n]*|(?P<op>\?=|<=|>=|==|=|<|>)|(?P<lb>\{)|(?P<rb>\})|(?P<qs>"[^"]*")|(?P<w>[^\s{}=<>#"]+)""", re.VERBOSE)
def tokenize(t):
    return [m.group() for m in _TOKEN_RE.finditer(t) if m.lastgroup in ("op","lb","rb","qs","w")]
def parse_block(toks, i):
    items, n = [], len(toks)
    while i < n:
        t = toks[i]
        if t == "}": return items, i+1
        nxt = toks[i+1] if i+1 < n else None
        if nxt in ("=","?=","==","<",">","<=",">="):
            key, j = t, i+2
            if j < n and toks[j] == "{": val, k = parse_block(toks, j+1)
            else: val, k = (toks[j] if j < n else None), j+1
            items.append((key, val)); i = k
        elif t == "{":
            val, k = parse_block(toks, i+1); items.append((None, val)); i = k
        else:
            items.append(t); i += 1
    return items, i
def parse_file(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return parse_block(tokenize(f.read()), 0)[0]
def unq(v): return v.strip('"') if isinstance(v, str) else v

# building tokens we DON'T want to treat as a real building type
META = {"building_type", "building_group", "building_levels", "building_owner",
        "building_employment", "building_types", "building_size"}
BKEYS = {"building", "is_building_type", "building_type", "default_building",
         "has_building", "type", "target_building"}
NUMKEYS = {"value", "count", "level", "levels", "amount", "add", "min", "max"}
# confident formable-tag -> Mod 1 source tag (so e.g. a GER journal maps to Prussia)
FORMABLE = {"GER": "PRU", "ITA": "SAR", "SCA": "SWE", "ETH": "SHW", "GCO": "CLM",
            "GBR": "GBR"}
# filename substring -> Mod 1 tag. Most country gating lives in the file name / scoped
# triggers, not a literal c:TAG, so this is where the real signal is. Inclusive but
# hand-picked; ambiguous files (canals, player_objectives, art) stay generic.
FILE_HINTS = {
    "russia": "RUS", "hokkaido": "JAP", "meiji": "JAP", "japan": "JAP",
    "sick_man": "TUR", "amazonas": "BRZ", "coffee_and_milk": "BRZ",
    "cristo_redentor": "BRZ", "brazil": "BRZ", "philippines": "PHI", "manila": "PHI",
    "iberian": "SPA", "spanish": "SPA", "atocha": "SPA", "sagrada": "SPA", "spain": "SPA",
    "portugal": "POR", "pena": "POR", "national_awakening_monument": "PRU",
    "kaiserforum": "PRU", "grunderzeit": "PRU", "germany": "PRU", "greece": "GRE",
    "austria": "AUS", "egypt": "EGY", "punjab": "PAN", "sikh": "PAN", "persia": "PER",
    "mexico": "MEX", "korea": "KOR", "sokoto": "SOK", "ethiopia": "SHW",
    "morocco": "MOR", "siam": "SIA", "nepal": "NEP", "burma": "BUR", "colombia": "CLM",
    "argentina": "ARG", "sweden": "SWE", "scandinav": "SWE", "netherlands": "NET",
    "east_indies": "DEI", "east_india": "BIC", "british_dictates": "BIC",
    "victoria_terminus": "BIC", "india_railway": "BIC", "raj": "BIC", "india": "BIC",
    "hyderabad": "HYD", "belgium": "BEL", "bavaria": "BAV", "oman": "OMA",
}

def walk(node, tags, builds, hints, _in_building_ctx=False):
    """Recursively collect tags, building tokens, and nearby numeric hints."""
    if isinstance(node, str):
        s = unq(node)
        if s.startswith("c:"):
            tags.add(s.split(":", 1)[1])
        elif s.startswith("building_") and s not in META:
            builds.add(s)
        return
    if not isinstance(node, list):
        return
    block_has_building = any(
        isinstance(it, tuple) and (
            (it[0] in BKEYS and isinstance(it[1], str) and unq(it[1]).startswith("building_")
             and unq(it[1]) not in META)
        ) for it in node)
    for it in node:
        if isinstance(it, tuple):
            k, v = it
            if k == "can_form_nation" and isinstance(v, str):
                tags.add(unq(v))
            if k in BKEYS and isinstance(v, str):
                s = unq(v)
                if s.startswith("building_") and s not in META:
                    builds.add(s)
            if k in NUMKEYS and isinstance(v, str) and block_has_building:
                try: hints.add(str(int(float(unq(v)))))
                except Exception: pass
            walk(v, tags, builds, hints)
        else:
            walk(it, tags, builds, hints)

def main():
    game = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GAME
    if not os.path.isdir(game):
        sys.exit(f"Game dir not found: {game}")

    want = {}  # tag -> country
    with open(os.path.join(HERE, "mod-nations.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            want[r["tag"]] = r["country"]

    rows = []  # (source, file, key, tags, builds, hints)
    for src, sub in (("journal", "journal_entries"), ("decision", "decisions")):
        for fp in glob.glob(os.path.join(game, "common", sub, "*.txt")):
            fname = os.path.basename(fp)
            for it in parse_file(fp):
                if not (isinstance(it, tuple) and isinstance(it[1], list)):
                    continue
                key = it[0]
                tags, builds, hints = set(), set(), set()
                walk(it[1], tags, builds, hints)
                if not builds:
                    continue
                rows.append((src, fname, key, sorted(tags),
                             sorted(b.replace("building_", "") for b in builds),
                             sorted(hints, key=lambda x: int(x))))

    # CSV (full raw extraction)
    out_csv = os.path.join(HERE, "journal_building_refs.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "file", "entry_key", "scope_tags", "buildings", "count_hints"])
        for src, fname, key, tags, builds, hints in rows:
            w.writerow([src, fname, key, " ".join(tags), " ".join(builds), " ".join(hints)])

    # map each entry to Mod 1 nations (by tag token, formable, or filename hint)
    def nations_for(tags):
        hit = set()
        for t in tags:
            if t in want: hit.add(t)
            elif t in FORMABLE and FORMABLE[t] in want: hit.add(FORMABLE[t])
        return hit

    def file_nation(fname):
        low = fname.lower()
        for sub, tag in FILE_HINTS.items():
            if sub in low and tag in want:
                return tag
        return None

    per_nation = defaultdict(list)   # tag -> [(src,file,key,builds,hints,inferred)]
    generic = []                     # entries with no Mod 1 attribution at all
    for src, fname, key, tags, builds, hints in rows:
        nats = nations_for(tags)
        fn = file_nation(fname)
        if fn and fn not in nats:
            per_nation[fn].append((src, fname, key, builds, hints, True))
        if nats:
            for t in nats:
                per_nation[t].append((src, fname, key, builds, hints, False))
        if not nats and not fn:
            generic.append((src, fname, key, builds, hints))

    # Markdown notes
    out_md = os.path.join(HERE, "journal-building-notes.md")
    order = list(want.keys())
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# Journal / decision building requirements — Mod 1 nations (first-pass scan)\n\n")
        f.write("> ⚠️ Auto-generated by `tools/scan_journal_buildings.py`. Country gating is "
                "inferred from `c:TAG` / `can_form_nation`; `count` hints are approximate "
                "(any nearby threshold). Buildings span ALL types (infra/admin/mil/monument/"
                "industry). **Refine by hand vs the wiki before acting.**\n\n")
        f.write("Backing data: `journal_building_refs.csv`.\n\n")
        f.write("## Nation-specific entries\n\n")
        for t in order:
            entries = per_nation.get(t)
            if not entries:
                continue
            f.write(f"### {want[t]} ({t})\n\n")
            for src, fname, key, builds, hints, inferred in sorted(entries):
                h = f"  _(counts≈ {', '.join(hints)})_" if hints else ""
                mark = " _[via filename]_" if inferred else ""
                f.write(f"- **{key}** ({src}/{fname}): {', '.join(builds)}{h}{mark}\n")
            f.write("\n")
        f.write("## Generic entries (no specific country gating — apply broadly)\n\n")
        for src, fname, key, builds, hints in sorted(generic):
            h = f"  _(counts≈ {', '.join(hints)})_" if hints else ""
            f.write(f"- **{key}** ({src}/{fname}): {', '.join(builds)}{h}\n")

    print(f"{len(rows)} entries reference buildings.")
    print(f"  nation-specific: {sum(len(v) for v in per_nation.values())} mappings "
          f"across {len(per_nation)} of {len(want)} nations")
    print(f"  generic (broad): {len(generic)}")
    print(f"-> {out_csv}\n-> {out_md}")

if __name__ == "__main__":
    main()
