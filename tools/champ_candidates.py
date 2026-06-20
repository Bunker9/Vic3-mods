#!/usr/bin/env python3
r"""
champ_candidates.py — rank champ-good candidates per mod nation.

Inputs (all under hk-config/tools/, already extracted from game files — see
[[future-needs-reference]], do not re-scan):
  mod-nations.csv          -- 40 nations + X tier (champ cap = 2*X)
  arable_rgo_by_nation.csv  -- buildable plantations/staples/rgo per nation
  future_needs_by_nation.csv -- prestige goods (explicit good names) per nation
  state_buildings.csv      -- existing (1836) building levels per nation -> "has"

Output: champ_candidates.csv -- tag, country, X, market_access, champ_1..5 (score), pick

Building->good map derived from common/production_methods + production_method_groups
(verified 2026-06-14, see conversation). market_access = nation has building_trade_center
in state_buildings.csv at 1836 (per ExpMktAccessMod's definition of "no global market
access" for the 10 nations it seeds: KOR PER PAN SOK HYD NEP SIA SHW SAF BUR).

Scoring (encodes champ-support-picks.md directive 1 + 2026-06-14 user guidance):
  +5  prestige good (distinctive national champ, future_needs_by_nation.csv)
  +3  plantation/staple/ranch good (low-input -> best champ per directive 1)
  +2 + min(has,5)  already in production (self-supplied inputs, proven viable)
  no market access only:
    -4  classic export-luxury crop (opium/dye/silk/tea/coffee/sugar/tobacco/wine/fruit/rubber)
        -- hard to monetize without world market access
    +2  staple food good (grain/meat/fish) -- always locally consumable
"""
import csv

BUILDING_GOOD = {
    # plantations
    "cotton_plantation": "fabric", "dye_plantation": "dye", "opium_plantation": "opium",
    "silk_plantation": "silk", "tea_plantation": "tea", "tobacco_plantation": "tobacco",
    "coffee_plantation": "coffee", "sugar_plantation": "sugar", "banana_plantation": "fruit",
    "rubber_plantation": "rubber", "vineyard": "wine",
    # staples / ranching / fishing
    "rye_farm": "grain", "wheat_farm": "grain", "maize_farm": "grain", "millet_farm": "grain",
    "rice_farm": "grain", "livestock_ranch": "meat", "fishing_wharf": "fish",
    "whaling_station": "meat",
    # mining / drilling
    "coal_mine": "coal", "iron_mine": "iron", "lead_mine": "lead", "sulfur_mine": "sulfur",
    "gold_mine": "gold", "oil_rig": "oil",
    # existing industry (has>0 only)
    "steel_mill": "steel", "arms_industry": "small_arms", "artillery_foundry": "artillery",
    "chemical_plant": "fertilizer", "tooling_workshop": "tools", "textile_mill": "clothes",
    "glassworks": "glass", "paper_mill": "paper", "furniture_manufactory": "furniture",
    "food_industry": "groceries", "motor_industry": "engines", "automotive_industry": "automobiles",
    "munition_plant": "ammunition", "explosives_factory": "explosives",
    "electrics_industry": "electronics", "synthetics_plant": "plastics",
}
PLANTATION_STAPLE_GOODS = {
    "fabric", "dye", "opium", "silk", "tea", "tobacco", "coffee", "sugar", "fruit", "rubber",
    "wine", "grain", "meat", "fish",
}
EXPORT_LUXURY = {"opium", "dye", "silk", "tea", "coffee", "sugar", "tobacco", "wine", "fruit", "rubber"}
STAPLE_FOOD = {"grain", "meat", "fish"}

HERE = "."

def load_nations():
    out = {}
    with open(f"{HERE}/mod-nations.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["tag"]] = {"country": row["country"], "X": int(row["X"])}
    return out

def load_market_access():
    tc = set()
    with open(f"{HERE}/state_buildings.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["building"] == "trade_center":
                tc.add(row["tag"])
    return tc

def load_has():
    """tag -> {good: total existing levels}"""
    has = {}
    with open(f"{HERE}/state_buildings.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            good = BUILDING_GOOD.get(row["building"])
            if not good:
                continue
            d = has.setdefault(row["tag"], {})
            d[good] = d.get(good, 0) + int(row["levels"])
    return has

def load_arable_goods():
    """tag -> set of plantation/staple/ranch/mining goods buildable"""
    out = {}
    with open(f"{HERE}/arable_rgo_by_nation.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            goods = set()
            for col in ("plantations", "staples"):
                for b in row[col].split():
                    g = BUILDING_GOOD.get(b)
                    if g: goods.add(g)
            for col in ("rgo_capped", "rgo_discoverable"):
                for tok in row[col].split():
                    b = tok.split(":")[0]
                    g = BUILDING_GOOD.get(b)
                    if g: goods.add(g)
            out[row["tag"]] = goods
    return out

def load_prestige_goods():
    """tag -> set of prestige goods (good names from parentheses)"""
    out = {}
    with open(f"{HERE}/future_needs_by_nation.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            goods = set()
            for tok in row["prestige_goods"].split():
                if "(" in tok:
                    g = tok.split("(")[1].rstrip(")")
                    goods.add(g)
            out[row["tag"]] = goods
    return out

def main():
    nations = load_nations()
    tc_tags = load_market_access()
    has = load_has()
    arable = load_arable_goods()
    prestige = load_prestige_goods()

    rows = []
    for tag, info in nations.items():
        market_access = "yes" if tag in tc_tags else "no"
        nation_has = has.get(tag, {})
        nation_prestige = prestige.get(tag, set())
        nation_arable = arable.get(tag, set())

        # candidate pool = arable goods + prestige goods + existing-production goods
        pool = set(nation_arable) | set(nation_prestige) | set(nation_has.keys())

        scored = []
        for g in pool:
            score = 0
            if g in nation_prestige:
                score += 5
            if g in PLANTATION_STAPLE_GOODS and g in nation_arable:
                score += 3
            existing = nation_has.get(g, 0)
            if existing > 0:
                score += 2 + min(existing, 5)
            if market_access == "no":
                if g in EXPORT_LUXURY:
                    score -= 4
                if g in STAPLE_FOOD:
                    score += 2
            scored.append((score, g))

        scored.sort(key=lambda x: (-x[0], x[1]))
        top5 = scored[:5]
        rows.append({
            "tag": tag, "country": info["country"], "X": info["X"],
            "market_access": market_access,
            "champ_1": f"{top5[0][1]}({top5[0][0]})" if len(top5) > 0 else "",
            "champ_2": f"{top5[1][1]}({top5[1][0]})" if len(top5) > 1 else "",
            "champ_3": f"{top5[2][1]}({top5[2][0]})" if len(top5) > 2 else "",
            "champ_4": f"{top5[3][1]}({top5[3][0]})" if len(top5) > 3 else "",
            "champ_5": f"{top5[4][1]}({top5[4][0]})" if len(top5) > 4 else "",
            "pick": "",
        })

    # order by X descending (tier order), matching mod-nations.csv input order
    with open(f"{HERE}/champ_candidates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tag","country","X","market_access",
                                           "champ_1","champ_2","champ_3","champ_4","champ_5","pick"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote champ_candidates.csv ({len(rows)} nations)")

if __name__ == "__main__":
    main()
