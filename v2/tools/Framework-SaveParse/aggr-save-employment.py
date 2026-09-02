#!/usr/bin/env python3
"""aggr-save-employment.py - SaveParse Set-1 COMMON aggregator (MOD-AGNOSTIC): joins the raw pool into a
per-STATE employment/vacancy census -> save-CURR/aggr_employment.csv + aggr_employment_pops.csv.

PURPOSE (actinfo): answers "which states have UNEMPLOYMENT sitting next to EMPTY BUILDINGS, and are the
vacancies in the SAME professions as the idle pops?" - the pairing a human needs to judge a stranded-pop
state. Vacancy is measured from the building block's own `staffing` (occupancy in level-equivalents) vs
`levels`; destitution is measured from the pop block's `wealth`. Both are RAW save fields - nothing here
models Vic3 rules, it only SORTS + PAIRS what the save states (SORT-not-FILTER: no state is dropped).

Mod-agnostic by construction: no tags, no probe literals, no mod tokens (T101). Standalone; run-save-parse
invokes it after the ext-* stages have written the raw pool.

Inputs  (save-CURR/ ROOT): raw_buildings.csv, raw_pops.csv, raw_state_census.csv
Outputs (save-CURR/ ROOT): aggr_employment.csv      one row per state  (vacancy + idle-pop pairing)
                           aggr_employment_pops.csv one row per state x pop profession (wealth split)
"""
import os
import sys
import argparse
import collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")
# A pop at or below this wealth is counted DESTITUTE (idle-or-starving). Externalized, not a magic number.
DESTITUTE_WEALTH_MAX = CFG.get("employment", {}).get("destitute_wealth_max", 2)
# A building staffed at or below this fraction of its levels is counted EMPTY.
EMPTY_OCCUPANCY_MAX = CFG.get("employment", {}).get("empty_occupancy_max", 0.5)


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _read(name):
    path = os.path.join(ROOT, name)
    if not os.path.exists(path):
        sys.exit(f"  aggr-employment: MISSING {path} - run the ext-* stages first (run-save-parse).")
    return lib_io.read_csv_dicts(path)


def main():
    argparse.ArgumentParser(description="SaveParse Set1: per-state employment/vacancy census (common).").parse_args()

    # state_id -> (owner_tag, state_region) from the enriched census; owner-agnostic, first row wins.
    owner = {}
    for r in _read("raw_state_census.csv"):
        owner.setdefault(r["state_id"], (r.get("owner_tag", ""), r.get("state_region", "")))

    # ---- buildings: vacancy = levels - staffing (staffing is occupancy in LEVEL-equivalents) ----
    b_lv, b_vac, b_empty, b_worst = (collections.defaultdict(float), collections.defaultdict(float),
                                     collections.defaultdict(int), {})
    for r in _read("raw_buildings.csv"):
        st = r["state"]
        lv, staff = _f(r["levels"]), _f(r["staffing"])
        if lv <= 0:
            continue
        vac = max(lv - staff, 0.0)
        occ = staff / lv
        b_lv[st] += lv
        b_vac[st] += vac
        if occ <= EMPTY_OCCUPANCY_MAX:
            b_empty[st] += 1
            # worst = the emptiest building weighted by size (biggest stranded capacity)
            if st not in b_worst or vac > b_worst[st][1]:
                b_worst[st] = (r["building"], vac, lv, occ, r.get("salary_rate", ""))

    # ---- pops: workforce split by wealth (destitute vs the rest), per state x profession ----
    p_tot, p_dest = collections.defaultdict(float), collections.defaultdict(float)
    pp = collections.defaultdict(lambda: [0.0, 0.0])   # (state, type) -> [workforce, destitute_workforce]
    for r in _read("raw_pops.csv"):
        st, wf = r["location"], _f(r["workforce"])
        if wf <= 0:
            continue
        p_tot[st] += wf
        key = (st, r["type"])
        pp[key][0] += wf
        if _f(r["wealth"], 99) <= DESTITUTE_WEALTH_MAX:
            p_dest[st] += wf
            pp[key][1] += wf

    # ---- emit: one row per state ----
    rows = []
    for st in sorted(set(b_lv) | set(p_tot), key=lambda s: -p_dest.get(s, 0)):
        tag, region = owner.get(st, ("", ""))
        worst = b_worst.get(st)
        rows.append([
            st, tag, region,
            round(b_lv.get(st, 0), 3), round(b_vac.get(st, 0), 3), b_empty.get(st, 0),
            round(p_tot.get(st, 0)), round(p_dest.get(st, 0)),
            round(p_dest.get(st, 0) / p_tot[st], 4) if p_tot.get(st) else "",
            worst[0] if worst else "", round(worst[1], 3) if worst else "",
            round(worst[3], 4) if worst else "", worst[4] if worst else "",
        ])
    lib_io.write_csv(os.path.join(ROOT, "aggr_employment.csv"),
                     ["state_id", "owner_tag", "state_region", "levels_total", "vacancy_levels",
                      "empty_buildings", "workforce", "destitute_workforce", "destitute_frac",
                      "worst_empty_building", "worst_vacancy_levels", "worst_occupancy", "worst_salary_rate"],
                     rows)
    print(f"  [employment] {len(rows)} states -> aggr_employment.csv")

    # ---- emit: one row per state x profession (which professions are idle) ----
    prows = []
    for (st, typ), (wf, dwf) in sorted(pp.items(), key=lambda kv: -kv[1][1]):
        tag, region = owner.get(st, ("", ""))
        prows.append([st, tag, region, typ, round(wf), round(dwf),
                      round(dwf / wf, 4) if wf else ""])
    lib_io.write_csv(os.path.join(ROOT, "aggr_employment_pops.csv"),
                     ["state_id", "owner_tag", "state_region", "pop_type", "workforce",
                      "destitute_workforce", "destitute_frac"], prows)
    print(f"  [employment] {len(prows)} state x profession rows -> aggr_employment_pops.csv")


if __name__ == "__main__":
    main()
