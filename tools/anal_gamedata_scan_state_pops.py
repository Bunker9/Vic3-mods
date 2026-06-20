#!/usr/bin/env python3
"""
anal_gamedata_scan_state_pops.py — per-STATE population for the 40 EcoBoost mod tags,
parsed from Victoria 3 common/history/pops. Needed for EcoBoost Track-B starter-building
seeding, where wood goes to the top 80% and iron to the top 40% of a tag's states BY POP.

(parse_country_stats.py only sums pop to the TAG level; this keeps the per-state breakdown.)
Reuses the Paradox tokenizer/parser from parse_country_stats.py (import = no main run).

Output: state_pops.csv  (tag, country, state, pop)  one row per (owning tag, populated state),
        sorted by tag then pop desc.
Usage: python anal_gamedata_scan_state_pops.py
"""
import os, csv, glob
from collections import defaultdict

from _refpaths import game_path
from parse_country_stats import parse_file, kv, kv_all, iter_states, to_int, collect_names

HERE = os.path.dirname(os.path.abspath(__file__))


def collect_state_pops(game):
    """(tag, state) -> summed create_pop.size, from history/pops region_state blocks."""
    sp = defaultdict(int)
    for fp in glob.glob(os.path.join(game, "common", "history", "pops", "*.txt")):
        for skey, st in iter_states(kv(parse_file(fp), "POPS") or []):
            state = skey.split(":", 1)[1] if ":" in skey else skey
            for it in st:
                if isinstance(it, tuple) and isinstance(it[0], str) and it[0].startswith("region_state:"):
                    tag = it[0].split(":", 1)[1]
                    for cp in kv_all(it[1], "create_pop"):
                        sp[(tag, state)] += to_int(kv(cp, "size"))
    return sp


def main():
    game = game_path()
    if not os.path.isdir(game):
        raise SystemExit(f"Game dir not found: {game}")

    nat = {}
    with open(os.path.join(HERE, "mod-nations.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            nat[r["tag"]] = r["country"]

    names = collect_names(game)
    sp = collect_state_pops(game)

    rows = [{"tag": tag, "country": nat.get(tag, names.get(tag, tag)), "state": state, "pop": pop}
            for (tag, state), pop in sp.items() if tag in nat]
    rows.sort(key=lambda r: (r["tag"], -r["pop"]))

    out = os.path.join(HERE, "state_pops.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tag", "country", "state", "pop"])
        w.writeheader()
        w.writerows(rows)

    per_tag = defaultdict(int)
    for r in rows:
        per_tag[r["tag"]] += 1
    print(f"wrote state_pops.csv: {len(rows)} states across {len(per_tag)}/40 mod tags")
    for t in ("CHI", "JAP", "BRZ", "ARG", "PAN", "SOK", "SAF"):
        sts = [r for r in rows if r["tag"] == t]
        if sts:
            print(f"  {t}: {len(sts):>2} states | top {sts[0]['state']}={sts[0]['pop']:,} "
                  f"| bottom {sts[-1]['state']}={sts[-1]['pop']:,}")


if __name__ == "__main__":
    main()
