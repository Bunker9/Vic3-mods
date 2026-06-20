#!/usr/bin/env python3
r"""
gen_ecoboost_wip.py — Top40EcoBoost analysis, STAGE 1 (barebones WIP).

Emits SELECT_ECOBOOST_WIP.csv: one row per (tag, good) with the RAW signals needed to
choose a CHAMPION (the focus of this pass) and to flag must-have eco-starters. No curated
champ/support/flavour picks here — that judgement happens in stage 2 (a human+Claude
pattern-matching refinement of this WIP), which is then reverse-engineered back into a
reproducible polish script.

Rules baked in (the rest is left raw on purpose):
- hardwood is FOLDED into wood everywhere (logging camp makes both); good "gold" + whaling
  are DROPPED from the analysis (handled by Track-B history seeding gen_ecoboost_starters.py).
- b (seed count) = building levels to lift production to 50% of demand, then CLAMPED to be
  "around a" (a = levels the tag already has): b <= max(B_ZERO_CAP, round(B_CLAMP_MULT*a)).
  Tweak B_CLAMP_MULT / B_ZERO_CAP to taste.
- demand = building-input demand (starting_economy_prod_cons) + pop demand (SELECT_STAPLE_1836).
- flags: ^ potential (can build, 0 built); champ-exclusions and generic-manufacturing marked
  so a champion isn't picked from a byproduct / ubiquitous-processing good.

Inputs (hk-config/tools/): mod-nations.csv, state_buildings.csv,
  starting_economy_prod_cons.csv, SELECT_STAPLE_1836.csv, arable_rgo_by_nation.csv,
  future_needs_by_nation.csv.
Usage: python gen_ecoboost_wip.py
"""
import os, csv, math
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- tuning knobs (the point of stage 1: expose these for tweaking) ----
SHORTAGE_RATIO = 0.5     # produced/demand below this = shortage-penalty zone (Vic3 define)
B_CLAMP_MULT   = 1.0     # b <= round(B_CLAMP_MULT * a)  -> keep seed "around a"
B_ZERO_CAP     = 2       # ...but allow up to this when a == 0

# ---- good classification ----
ECO_STARTERS = {"iron", "wood", "grain", "fish", "fabric", "tools"}   # must self-supply >=0.5
IDENTITY_CROPS = {"silk", "tea", "dye", "coffee", "sugar", "tobacco", "opium", "wine", "fruit"}
DISTINCTIVE_INDUSTRY = {"steel", "artillery", "small_arms", "tools", "engines",
                        "ammunition", "explosives"}
STAPLE_FOOD = {"grain", "meat", "fish"}
GENERIC_MFG = {"groceries", "paper", "clothes", "furniture", "glass", "fertilizer"}
# never a 1836 champion (byproducts / post-1836 / infra). gold + hardwood handled separately.
EXCLUDE_CHAMP = {"oil", "rubber", "clippers", "steamers", "services", "transportation",
                 "electricity", "merchant_marine", "automobiles", "telephones", "radios",
                 "aeroplanes", "tanks", "electronics", "plastics"}
DROP_GOODS = {"gold"}    # whaling produces meat (kept as plain meat); gold dropped outright

BUILDING_GOOD = {
    "cotton_plantation": "fabric", "dye_plantation": "dye", "opium_plantation": "opium",
    "silk_plantation": "silk", "tea_plantation": "tea", "tobacco_plantation": "tobacco",
    "coffee_plantation": "coffee", "sugar_plantation": "sugar", "banana_plantation": "fruit",
    "rubber_plantation": "rubber", "vineyard": "wine",
    "rye_farm": "grain", "wheat_farm": "grain", "maize_farm": "grain", "millet_farm": "grain",
    "rice_farm": "grain", "livestock_ranch": "meat", "fishing_wharf": "fish",
    "whaling_station": "meat",
    "coal_mine": "coal", "iron_mine": "iron", "lead_mine": "lead", "sulfur_mine": "sulfur",
    "logging_camp": "wood",
    "steel_mill": "steel", "arms_industry": "small_arms", "artillery_foundry": "artillery",
    "chemical_plant": "fertilizer", "tooling_workshop": "tools", "textile_mill": "clothes",
    "glassworks": "glass", "paper_mill": "paper", "furniture_manufactory": "furniture",
    "food_industry": "groceries", "motor_industry": "engines",
    "munition_plant": "ammunition", "explosives_factory": "explosives",
}


def load_csv(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fold(good):
    """hardwood -> wood (logging camp makes both)."""
    return "wood" if good == "hardwood" else good


def main():
    nations = {r["tag"]: {"country": r["country"], "X": int(r["X"])}
               for r in load_csv("mod-nations.csv")}

    # a = building levels per (tag, good); also trade-center => market access
    has = defaultdict(lambda: defaultdict(int))
    tc = set()
    for r in load_csv("state_buildings.csv"):
        if r["building"] == "trade_center":
            tc.add(r["tag"])
        g = BUILDING_GOOD.get(r["building"])
        if g:
            has[r["tag"]][g] += int(r["levels"])

    # produced / building-consumed per (tag, good), hardwood folded into wood
    produced = defaultdict(lambda: defaultdict(float))
    bld_demand = defaultdict(lambda: defaultdict(float))
    for r in load_csv("starting_economy_prod_cons.csv"):
        g = fold(r["good"])
        if g in DROP_GOODS:
            continue
        produced[r["tag"]][g] += float(r["produced"])
        bld_demand[r["tag"]][g] += float(r["consumed"])

    # pop demand per (tag, good) from the staple welfare sheet (cols <good>_pop_need)
    pop_demand = defaultdict(lambda: defaultdict(float))
    staple = load_csv("SELECT_STAPLE_1836.csv")
    need_cols = [c for c in (staple[0].keys() if staple else []) if c.endswith("_pop_need")]
    for r in staple:
        for c in need_cols:
            g = fold(c[:-len("_pop_need")])
            try:
                pop_demand[r["tag"]][g] += float(r[c] or 0)
            except ValueError:
                pass

    # arable / buildable potential per tag (for the ^ flag)
    arable = defaultdict(set)
    for r in load_csv("arable_rgo_by_nation.csv"):
        for col in ("plantations", "staples"):
            for b in r[col].split():
                g = BUILDING_GOOD.get(b)
                if g:
                    arable[r["tag"]].add(g)
        for col in ("rgo_capped", "rgo_discoverable"):
            for tok in r[col].split():
                g = BUILDING_GOOD.get(tok.split(":")[0])
                if g:
                    arable[r["tag"]].add(g)

    # prestige goods + flavored-company target goods per tag (hardwood->wood)
    prestige = defaultdict(set)
    company = defaultdict(lambda: defaultdict(int))
    for r in load_csv("future_needs_by_nation.csv"):
        for tok in r["prestige_goods"].split():
            if "(" in tok:
                g = fold(tok.split("(")[1].rstrip(")"))
                if g not in DROP_GOODS:
                    prestige[r["tag"]].add(g)
                    company[r["tag"]][g] += 1

    # global per-level output per good (to convert a goods deficit -> building levels)
    lvl_tot, out_tot = defaultdict(float), defaultdict(float)
    for t in nations:
        for g, lv in has[t].items():
            lvl_tot[g] += lv
        for g, p in produced[t].items():
            out_tot[g] += p
    per_level = {g: out_tot[g] / lvl_tot[g] for g in lvl_tot if lvl_tot[g] > 0 and out_tot[g] > 0}
    DEFAULT_PER_LEVEL = 30.0

    def seed_b(good, a, deficit_goods):
        if deficit_goods <= 0:
            return 0
        raw = max(1, math.ceil(deficit_goods / (per_level.get(good) or DEFAULT_PER_LEVEL)))
        cap = max(B_ZERO_CAP, round(B_CLAMP_MULT * a))
        return min(raw, cap)

    cols = ["tag", "country", "X", "mkt", "good", "a", "produced", "bld_demand",
            "pop_demand", "demand", "ratio", "b", "shortage", "potential", "prestige",
            "identity_crop", "distinctive_ind", "staple_food", "generic_mfg",
            "eco_starter", "excl_champ", "company"]
    rows = []
    for tag, info in nations.items():
        mkt = "yes" if tag in tc else "no"
        goods = (set(produced[tag]) | set(bld_demand[tag]) | set(pop_demand[tag])
                 | set(has[tag]) | arable[tag] | prestige[tag] | ECO_STARTERS) - DROP_GOODS
        for g in goods:
            a = has[tag].get(g, 0)
            p = produced[tag].get(g, 0.0)
            bd = bld_demand[tag].get(g, 0.0)
            pd = pop_demand[tag].get(g, 0.0)
            dem = bd + pd
            ratio = (p / dem) if dem > 0 else ""
            short = 1 if (dem > 0 and p / dem < SHORTAGE_RATIO) else 0
            b = seed_b(g, a, (SHORTAGE_RATIO * dem - p)) if short else 0
            rows.append({
                "tag": tag, "country": info["country"], "X": info["X"], "mkt": mkt, "good": g,
                "a": a, "produced": round(p, 1), "bld_demand": round(bd, 1),
                "pop_demand": round(pd, 1), "demand": round(dem, 1),
                "ratio": (round(ratio, 2) if ratio != "" else ""), "b": b, "shortage": short,
                "potential": 1 if (a == 0 and g in arable[tag]) else 0,
                "prestige": 1 if g in prestige[tag] else 0,
                "identity_crop": 1 if g in IDENTITY_CROPS else 0,
                "distinctive_ind": 1 if g in DISTINCTIVE_INDUSTRY else 0,
                "staple_food": 1 if g in STAPLE_FOOD else 0,
                "generic_mfg": 1 if g in GENERIC_MFG else 0,
                "eco_starter": 1 if g in ECO_STARTERS else 0,
                "excl_champ": 1 if g in EXCLUDE_CHAMP else 0,
                "company": company[tag].get(g, 0),
            })

    # sort: tag (by X desc, country), then produced desc -> champ candidates float to top
    rows.sort(key=lambda r: (-r["X"], r["country"], -r["produced"]))
    out = os.path.join(HERE, "SELECT_ECOBOOST_WIP.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote SELECT_ECOBOOST_WIP.csv ({len(rows)} tag-good rows, {len(nations)} tags)")

    # sanity: champ-eligible top-by-production for the tags whose champ was previously WRONG
    def champ_elig(r):
        return not r["excl_champ"] and not r["generic_mfg"] and r["good"] not in DROP_GOODS
    for t in ("CHI", "USA", "PAN", "JAP", "PRU"):
        cand = sorted([r for r in rows if r["tag"] == t and champ_elig(r)],
                      key=lambda r: -r["produced"])[:4]
        disp = " ".join(f"{r['good']}({r['produced']:g}{'^' if r['potential'] else ''})" for r in cand)
        print(f"  {t} top-produced champ-eligible: {disp}")


if __name__ == "__main__":
    main()
