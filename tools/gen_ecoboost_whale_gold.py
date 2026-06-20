#!/usr/bin/env python3
r"""
gen_ecoboost_whale_gold.py — seed WHALE (whaling_station) + GOLD (gold_mine, NOT gold_field)
at 1836 via a BUILDING HISTORY file, for the 40 EcoBoost mod tags.

WHY a separate generator (not gen_ecoboost_starters):
  gen_ecoboost_starters dropped whale+gold on 2026-06-15 because it sourced capacity from
  `unused_rgo_by_state.csv`, which (a) conflates DISCOVERED with UNDISCOVERED resources and
  (b) reports the WHOLE-STATE cap against every part-owner of a divided state. Per the
  no-rerun / prefer-new-file rules, that generator and zz_eco_starters.txt are LEFT UNTOUCHED;
  this is a NEW generator + NEW history file.

TWO-LEVEL CORRECTNESS GATE (the fix):
  1. DISCOVERED capacity only — read map_data `capped_resources = { building_whaling_station=N
     building_gold_mine=N }`. (Undiscovered deposits live in `resource = { ... undiscovered_amount }`
     blocks and are IGNORED — that was the gold_field over-seed trap.)
  2. THE NATION ACTUALLY OWNS THE RESOURCE PROVINCE — a state region designates one `mine`
     province (hosts gold/iron) and one `port` province (hosts whaling/coastal). In a DIVIDED
     state the cap is shared, so a tag that owns only a sliver (BIC's Bombay, a French colonial
     coast still growing) has NO buildable slot. We seed gold for tag T in state S only if T
     owns S's `mine` province, and whale only if T owns S's `port` province (ownership from
     common/history/states owned_provinces). Example caught: Bombay's port province x51F0A0 is
     Portugal's (Goa), so BIC gets no whaling there even though the state has whaling capacity.

SEED RULE: for the 40 tags, where (1)+(2) hold and the tag currently builds ZERO of that
  building (state_buildings.csv), create 1 level, country-owned, default PM.

Inputs : hk-config/tools/{mod-nations.csv, state_buildings.csv}
         + vanilla map_data/state_regions/*.txt + common/history/states/*.txt (via _refpaths).
Outputs: mod1/Top40EcoBoostMod/common/history/buildings/zz_eco_whale_gold.txt  (UTF-8 BOM)
         hk-config/tools/final_whale_gold_seed.csv                              (review report)

Final gate is always the first in-game error.log run; add curated EXCLUDE entries if any
(tag,state,building) still logs "can only support 0".
Usage: python gen_ecoboost_whale_gold.py
"""
import os, csv, re, glob
from collections import defaultdict
from _refpaths import game_path

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_HISTORY = os.path.join(HERE, "..", "..", "mod1", "Top40EcoBoostMod",
                           "common", "history", "buildings", "zz_eco_whale_gold.txt")
REPORT_CSV = os.path.join(HERE, "final_whale_gold_seed.csv")

# building token -> (short label, which designated province hosts it)
TARGETS = [
    ("building_whaling_station", "whale", "port"),
    ("building_gold_mine",       "gold",  "mine"),
]
EXCLUDE = set()   # curated (tag, STATE_x, building_token) after an error.log run

STATE_RE = re.compile(r"^\s*(STATE_[A-Z0-9_]+)\s*=\s*\{")
PROV_RE = re.compile(r"(x[0-9A-Fa-f]{6})")
DESIG_RE = {
    "port": re.compile(r'^\s*port\s*=\s*"(x[0-9A-Fa-f]{6})"'),
    "mine": re.compile(r'^\s*mine\s*=\s*"(x[0-9A-Fa-f]{6})"'),
}
CAP_RE = {
    "building_whaling_station": re.compile(r"^\s*building_whaling_station\s*=\s*(\d+)"),
    "building_gold_mine":       re.compile(r"^\s*building_gold_mine\s*=\s*(\d+)"),
}


def load_csv(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def norm_state(s):
    return s if s.startswith("STATE_") else f"STATE_{s}"


def parse_state_regions():
    """STATE_x -> {whale, gold, port, mine}  (capped/discovered capacity + designated provinces)."""
    out = defaultdict(lambda: {"whale": 0, "gold": 0, "port": None, "mine": None})
    sr_dir = os.path.join(game_path(), "map_data", "state_regions")
    for path in sorted(glob.glob(os.path.join(sr_dir, "*.txt"))):
        cur = None
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                m = STATE_RE.match(line)
                if m:
                    cur = m.group(1)
                    continue
                if cur is None:
                    continue
                for key, rgx in DESIG_RE.items():
                    md = rgx.match(line)
                    if md:
                        out[cur][key] = md.group(1).upper()
                mw = CAP_RE["building_whaling_station"].match(line)
                if mw:
                    out[cur]["whale"] = int(mw.group(1))
                mg = CAP_RE["building_gold_mine"].match(line)
                if mg:
                    out[cur]["gold"] = int(mg.group(1))
    return out


def parse_province_owners():
    """province-hex (UPPER) -> owning tag, from common/history/states create_state blocks."""
    owner = {}
    hs_dir = os.path.join(game_path(), "common", "history", "states")
    for path in sorted(glob.glob(os.path.join(hs_dir, "*.txt"))):
        cur_tag = None
        in_op = False
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                ctag = re.search(r"country\s*=\s*c:(\w+)", line)
                if ctag:
                    cur_tag = ctag.group(1)
                if "owned_provinces" in line:
                    for hx in PROV_RE.findall(line.split("owned_provinces", 1)[1]):
                        if cur_tag:
                            owner[hx.upper()] = cur_tag
                    in_op = "}" not in line.split("owned_provinces", 1)[1]
                    continue
                if in_op:
                    for hx in PROV_RE.findall(line):
                        if cur_tag:
                            owner[hx.upper()] = cur_tag
                    if "}" in line:
                        in_op = False
    return owner


def main():
    tags = {r["tag"]: r["country"] for r in load_csv("mod-nations.csv")}

    # already-present whale/gold: (tag, STATE_x) sets
    have = {"building_whaling_station": set(), "building_gold_mine": set()}
    for r in load_csv("state_buildings.csv"):
        if r["tag"] not in tags:
            continue
        key = (r["tag"], norm_state(r["state"]))
        if r["building"] == "whaling_station":
            have["building_whaling_station"].add(key)
        elif r["building"] == "gold_mine":
            have["building_gold_mine"].add(key)

    regions = parse_state_regions()
    prov_owner = parse_province_owners()

    # decide seeds: tag -> STATE_x -> [building_token]
    seed = defaultdict(lambda: defaultdict(list))
    rows = []
    report = {t: {"whale": 0, "gold": 0} for t in tags}
    for st, info in regions.items():
        for bt, lbl, desig in TARGETS:
            cap = info[lbl]
            prov = info[desig]
            if cap <= 0 or prov is None:
                continue
            owner = prov_owner.get(prov)            # the tag that OWNS the resource province
            if owner not in tags:
                continue
            if (owner, st) in have[bt]:
                continue
            if (owner, st, bt) in EXCLUDE:
                continue
            seed[owner][st].append(bt)
            report[owner][lbl] += 1
            rows.append((owner, tags[owner], st, lbl, cap, prov))

    # ---- write the history file (UTF-8 BOM, tabs) ----
    os.makedirs(os.path.dirname(MOD_HISTORY), exist_ok=True)
    lines = [
        "# =============================================================================",
        "# Top40EcoBoostMod - whale + gold_mine starter RGOs",
        "#   (GENERATED by hk-config/tools/gen_ecoboost_whale_gold.py - DO NOT HAND-EDIT)",
        "# Seeds 1 level of whaling_station / gold_mine at 1836 to states of the 40 mod tags where",
        "# (1) the state has DISCOVERED capacity (map_data capped_resources) and (2) the tag OWNS",
        "# the resource province (port for whaling, mine for gold) so its division can actually",
        "# build it, and it currently builds ZERO. Separate from zz_eco_starters.txt (never touched).",
        "# Country-owned, default PM. Verify in error.log.",
        "# =============================================================================",
        "BUILDINGS = {",
    ]
    n_states = n_builds = 0
    for tag in sorted(seed):
        for st in sorted(seed[tag]):
            n_states += 1
            lines.append(f"\ts:{st} = {{")
            lines.append(f"\t\tregion_state:{tag} = {{")
            for bt in seed[tag][st]:
                n_builds += 1
                lines.append("\t\t\tcreate_building = {")
                lines.append(f'\t\t\t\tbuilding = "{bt}"')
                lines.append("\t\t\t\tadd_ownership = {")
                lines.append("\t\t\t\t\tcountry = {")
                lines.append(f'\t\t\t\t\t\tcountry = "c:{tag}"')
                lines.append("\t\t\t\t\t\tlevels = 1")
                lines.append("\t\t\t\t\t}")
                lines.append("\t\t\t\t}")
                lines.append("\t\t\t\treserves = 1")
                lines.append("\t\t\t}")
            lines.append("\t\t}")
            lines.append("\t}")
    lines.append("}")
    with open(MOD_HISTORY, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")

    # ---- write the review report ----
    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tag", "country", "state", "building", "state_capacity", "owned_resource_province"])
        for row in sorted(rows):
            w.writerow(row)

    print(f"wrote zz_eco_whale_gold.txt: {n_builds} buildings across {n_states} state-blocks")
    whale = sum(report[t]["whale"] for t in tags)
    gold = sum(report[t]["gold"] for t in tags)
    print(f"  totals: whale={whale} gold={gold}")
    for t in sorted(tags, key=lambda t: -(report[t]["whale"] + report[t]["gold"])):
        if report[t]["whale"] or report[t]["gold"]:
            print(f"  {t}: whale={report[t]['whale']} gold={report[t]['gold']}")


if __name__ == "__main__":
    main()
