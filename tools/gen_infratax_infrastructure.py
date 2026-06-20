#!/usr/bin/env python3
r"""
gen_infratax_infrastructure.py — InfraTaxMod GAME-WIDE infrastructure floor.

RULE (user, 2026-06-19): every STATE:TAG DIVISION (a country's slice of a state region) with
population > 350,000 MUST have at least one trade center and a bureaucracy building, and if it
is coastal must also have a port. This seeds those buildings at 1836 via a history file (no
runtime event => cheap) wherever the division currently has ZERO of them.

  building_trade_center            -> every qualifying division (market access)
  building_government_administration (bureaucracy) -> every qualifying division
  building_port                    -> only divisions that own the state's coastal `port` province

CORRECTNESS GATES (so we never seed a build the division can't support):
  * pop>350K is the DIVISION pop (sum of create_pop under region_state:TAG), not the whole state.
  * Owner NOT decentralized: incorporated AND unincorporated divisions are seeded (a populous colony
    or unrecognized homeland gets infrastructure too); only decentralized owners are skipped, since
    they have no construction sector and no starting techs, so their create_building always errors.
    The build-enabling techs for backwards-but-centralized owners come from the tier-6 starting-tech
    override (InfraTaxMod/common/scripted_effects/00_starting_inventions.txt).
  * PORT requires the tag to OWN the state's designated `port` province (coastal share), same
    province-ownership rigor as the whale/gold seeder. A landlocked or non-port-owning division
    gets no port.
  * JAP (sakoku) and CHI (canton system) block trade centers in ALL their states, so they get
    NO trade centers at all (they still get bureaucracy + ports). Seeding them there spammed the
    state_trade_center_max_limit_add Building-context + canton/sakoku tooltip errors (~620).
  * Only seeds a building where the division has 0 of it today (vanilla history/buildings baseline).

NOTE (load-time, T85): game-wide seeding adds a lot of history. Review the printed counts; the
report final_infratax_infrastructure_seed.csv lists every seed. Final gate = first error.log run;
add curated EXCLUDE entries for any residual "support 0".

Inputs : vanilla common/history/{pops,states,buildings} + map_data/state_regions (via _refpaths).
Outputs: mod1/InfraTaxMod/common/history/buildings/zz_infratax_infrastructure.txt  (UTF-8 BOM)
         hk-config/tools/final_infratax_infrastructure_seed.csv                     (review report)
Usage: python gen_infratax_infrastructure.py
"""
import os, csv, re, glob
from collections import defaultdict
from _refpaths import game_path
from parse_country_stats import parse_file, kv, kv_all, iter_states, to_int
from anal_gamedata_scan_state_pops import collect_state_pops

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_HISTORY = os.path.join(HERE, "..", "..", "mod1", "InfraTaxMod",
                           "common", "history", "buildings", "zz_infratax_infrastructure.txt")
REPORT_CSV = os.path.join(HERE, "final_infratax_infrastructure_seed.csv")

POP_MIN = 350_000
B_TRADE = "building_trade_center"
B_BUREAU = "building_government_administration"
B_PORT = "building_port"

# JAP (sakoku) and CHI (canton system) trade-policy laws block trade-center construction in ALL
# their states. Seeding trade centers there spammed ~620 errors in the 2026-06-19 run
# (state_trade_center_max_limit_add Building-context + canton/sakoku tooltip loc errors, both of
# which come ONLY from those two laws), so they are skipped for trade centers entirely (they still
# get bureaucracy + ports).
NO_TRADE_CENTER_TAGS = {"CHI", "JAP"}
EXCLUDE = set()   # curated (tag, STATE_x, building_token) after an error.log run

STATE_RE = re.compile(r"^\s*(STATE_[A-Z0-9_]+)\s*=\s*\{")
PORT_RE = re.compile(r'^\s*port\s*=\s*"(x[0-9A-Fa-f]{6})"')
HEX_RE = re.compile(r"x[0-9A-Fa-f]{6}")


def norm_state(s):
    return s if s.startswith("STATE_") else f"STATE_{s}"


def parse_port_provinces(game):
    """STATE_x -> designated coastal `port` province hex (UPPER), or None."""
    out = {}
    for path in sorted(glob.glob(os.path.join(game, "map_data", "state_regions", "*.txt"))):
        cur = None
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                m = STATE_RE.match(line)
                if m:
                    cur = m.group(1)
                    continue
                if cur is None:
                    continue
                mp = PORT_RE.match(line)
                if mp:
                    out[cur] = mp.group(1).upper()
    return out


def parse_states(game):
    """Return (incorporated[(tag,state)]->bool, prov_owner[hex]->tag)."""
    incorp, prov_owner = {}, {}
    for fp in glob.glob(os.path.join(game, "common", "history", "states", "*.txt")):
        for skey, st in iter_states(kv(parse_file(fp), "STATES") or []):
            state = skey.split(":", 1)[1] if ":" in skey else skey
            for cs in kv_all(st, "create_state"):
                ctag = kv(cs, "country")
                if not ctag or ":" not in str(ctag):
                    continue
                tag = str(ctag).split(":", 1)[1]
                incorp[(tag, state)] = (kv(cs, "state_type") != "unincorporated")
                for hx in HEX_RE.findall(str(kv(cs, "owned_provinces"))):
                    prov_owner[hx.upper()] = tag
    return incorp, prov_owner


def parse_existing_buildings(game):
    """(tag, state) -> set(building tokens) from vanilla history/buildings."""
    have = defaultdict(set)
    for fp in glob.glob(os.path.join(game, "common", "history", "buildings", "*.txt")):
        for skey, st in iter_states(kv(parse_file(fp), "BUILDINGS") or []):
            state = skey.split(":", 1)[1] if ":" in skey else skey
            for it in st:
                if isinstance(it, tuple) and isinstance(it[0], str) and it[0].startswith("region_state:"):
                    tag = it[0].split(":", 1)[1]
                    for cb in kv_all(it[1], "create_building"):
                        b = str(kv(cb, "building")).strip('"')
                        have[(tag, state)].add(b)
    return have


def parse_decentralized(game):
    """Set of tags whose country_type = decentralized (no construction sector / no starting tech)."""
    dec = set()
    for fp in glob.glob(os.path.join(game, "common", "country_definitions", "*.txt")):
        txt = open(fp, encoding="utf-8-sig", errors="replace").read()
        for m in re.finditer(r"^([A-Z0-9_]{2,4})\s*=\s*\{(.*?)\n\}", txt, re.S | re.M):
            if re.search(r"country_type\s*=\s*decentralized", m.group(2)):
                dec.add(m.group(1))
    return dec


def main():
    game = game_path()
    if not os.path.isdir(game):
        raise SystemExit(f"Game dir not found: {game}")

    pops = collect_state_pops(game)                 # (tag, state) -> division pop, ALL tags
    incorp, prov_owner = parse_states(game)         # incorp kept only for the report
    port_prov = parse_port_provinces(game)
    have = parse_existing_buildings(game)
    decentralized = parse_decentralized(game)       # cannot build modern infrastructure at all

    seed = defaultdict(lambda: defaultdict(list))   # tag -> state -> [building]
    rows, skipped_dec = [], []
    for (tag, state), pop in pops.items():
        if pop <= POP_MIN:
            continue
        # Seed BOTH incorporated and unincorporated divisions (a populous colony / unrecognized
        # homeland should get infrastructure too). Only DECENTRALIZED owners are skipped: they have
        # no construction sector and no starting techs, so their create_building always errors
        # ("must have invented Bureaucracy/Navigation").
        if tag in decentralized:
            skipped_dec.append((tag, state, pop))
            continue
        ex = have.get((tag, state), set())

        # trade center (skip JAP/CHI entirely — sakoku/canton block it in all their states)
        if tag not in NO_TRADE_CENTER_TAGS and B_TRADE not in ex \
                and (tag, state, B_TRADE) not in EXCLUDE:
            seed[tag][state].append(B_TRADE)
            rows.append((tag, state, pop, "trade_center"))

        # bureaucracy
        if B_BUREAU not in ex and (tag, state, B_BUREAU) not in EXCLUDE:
            seed[tag][state].append(B_BUREAU)
            rows.append((tag, state, pop, "government_administration"))

        # port — only if the division owns the state's coastal port province
        pprov = port_prov.get(state)
        if pprov and prov_owner.get(pprov) == tag and B_PORT not in ex \
                and (tag, state, B_PORT) not in EXCLUDE:
            seed[tag][state].append(B_PORT)
            rows.append((tag, state, pop, "port"))

    # ---- write the history file (UTF-8 BOM, tabs) ----
    os.makedirs(os.path.dirname(MOD_HISTORY), exist_ok=True)
    lines = [
        "# =============================================================================",
        "# InfraTaxMod - infrastructure floor for populous divisions",
        "#   (GENERATED by hk-config/tools/gen_infratax_infrastructure.py - DO NOT HAND-EDIT)",
        "# Every (tag,state) division with pop > 350,000 whose owner is NOT decentralized gets lvl1",
        "# trade_center + government_administration (bureaucracy) where it has 0, plus a port",
        "# where the division owns the state's coastal port province. JAP+CHI get NO trade centers",
        "# (sakoku/canton block them everywhere). Country-owned, default PM. Verify in error.log.",
        "# =============================================================================",
        "BUILDINGS = {",
    ]
    n_states = n_builds = 0
    for tag in sorted(seed):
        for state in sorted(seed[tag]):
            n_states += 1
            lines.append(f"\ts:{state} = {{")
            lines.append(f"\t\tregion_state:{tag} = {{")
            for bt in seed[tag][state]:
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

    # ---- review report ----
    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tag", "state", "division_pop", "building"])
        for row in sorted(rows, key=lambda r: (r[0], r[1], r[3])):
            w.writerow(row)
        w.writerow([])
        w.writerow(["# DECENTRALIZED owners skipped (cannot build; review):", "", "", ""])
        for tag, state, pop in sorted(skipped_dec):
            w.writerow([tag, state, pop, "SKIPPED_decentralized"])

    by_b = defaultdict(int)
    for _, _, _, b in rows:
        by_b[b] += 1
    print(f"wrote zz_infratax_infrastructure.txt: {n_builds} buildings across {n_states} divisions")
    print("  by building: " + ", ".join(f"{b}={by_b[b]}" for b in sorted(by_b)))
    print(f"  decentralized divisions skipped: {len(skipped_dec)}")


if __name__ == "__main__":
    main()
