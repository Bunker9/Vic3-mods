#!/usr/bin/env python3
"""anal_state_region_pop.py — per-STATE-REGION total starting population across ALL tags,
from Victoria 3 common/history/pops. Sums create_pop sizes over every owning tag of a
state-region (so split states get their combined pop). Feeds PvtCapCtrlMod's static
per-state industry level cap (pop<1M -> flat 100; else floor(pop/12000)).

Reuses collect_state_pops() from anal_gamedata_scan_state_pops.py (no re-parsing logic);
that helper already reads the full history/pops set unfiltered, the 40-tag filter only
applied on its OWN write step.

Output: data_state_region_pop.csv (state_region, total_pop, n_owners, owner_tags)
Usage:  python anal_state_region_pop.py
"""
import os, csv
from collections import defaultdict

from _refpaths import game_path
from anal_gamedata_scan_state_pops import collect_state_pops

HERE = os.path.dirname(os.path.abspath(__file__))


def cap_for(pop):
    return 100 if pop < 1_000_000 else pop // 12000


def main():
    game = game_path()
    if not os.path.isdir(game):
        raise SystemExit(f"Game dir not found: {game}")

    sp = collect_state_pops(game)  # (tag, state) -> summed pop, ALL tags
    reg = defaultdict(int)
    owners = defaultdict(set)
    for (tag, state), pop in sp.items():
        reg[state] += pop
        owners[state].add(tag)

    rows = [{"state_region": s, "total_pop": reg[s], "n_owners": len(owners[s]),
             "owner_tags": "|".join(sorted(owners[s]))} for s in reg]
    rows.sort(key=lambda r: -r["total_pop"])

    out = os.path.join(HERE, "data_state_region_pop.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["state_region", "total_pop", "n_owners", "owner_tags"])
        w.writeheader()
        w.writerows(rows)

    flat = sum(1 for r in rows if r["total_pop"] < 1_000_000)
    print(f"wrote data_state_region_pop.csv: {len(rows)} state-regions")
    print(f"  flat-100 (<1M): {flat}  |  pop-scaled (>=1M): {len(rows) - flat}")
    print("  top 15 by total pop -> cap:")
    for r in rows[:15]:
        print(f"    {r['state_region']:<26} pop={r['total_pop']:>9} cap={cap_for(r['total_pop']):>5} owners={r['owner_tags']}")
    # spot the >1M states owned ONLY by non-mod tags (the coverage-gap risk)
    print("  (n_owners>1 split-state sample, top 8):")
    for r in [x for x in rows if x["n_owners"] > 1][:8]:
        print(f"    {r['state_region']:<26} pop={r['total_pop']:>9} cap={cap_for(r['total_pop']):>5} owners={r['owner_tags']}")


if __name__ == "__main__":
    main()
