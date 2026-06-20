#!/usr/bin/env python3
r"""
anal_flavour_built.py — cross-ref planned flavour (SELECT_ECOBOOST_FINAL_v2.csv) vs what
ACTUALLY built in-game (testbook/timeline.json, from the ECO_PLACED flavour markers) per tag.

Outputs:
  eco_flavour_built.csv    (tag, good)  — confirmed buildable day-1 -> candidates to move to history
  eco_flavour_unbuilt.csv  (tag, good)  — did NOT build -> kept in eco configs for manual review

NOTE: the log captures (country, building) but NOT the state, so this tells us WHICH flavour
goods build, not WHERE. Writing history needs the state -> enhanced logging + a follow-up run
(or generator-computed placement, T48/T52).

Usage: python anal_flavour_built.py
"""
import os, csv, json

HERE = os.path.dirname(os.path.abspath(__file__))
TIMELINE = os.path.join(HERE, "..", "..", "testbook", "timeline.json")

# in-game localized country name -> tag (the ones that differ from mod-nations.csv)
COUNTRY2TAG = {
    "Argentina": "ARG", "Bavaria": "BAV", "Brazil": "BRZ", "Burma": "BUR", "Dai Nam": "DAI",
    "East India Company": "BIC", "Egypt": "EGY", "Great Qing": "CHI", "Greece": "GRE",
    "Hungary": "HUN", "Hyderabad": "HYD", "Joseon": "KOR", "Khalsa Raj": "PAN", "Mexico": "MEX",
    "Morocco": "MOR", "Nepal": "NEP", "New Granada": "CLM", "Oman": "OMA", "Ottoman Empire": "TUR",
    "Persia": "PER", "Philippines": "PHI", "Sardinia-Piedmont": "SAR", "Siam": "SIA",
    "Two Sicilies": "SIC", "Russia": "RUS", "United States": "USA", "France": "FRA",
    "Great Britain": "GBR", "Japan": "JAP", "Prussia": "PRU", "Spain": "SPA", "Austria": "AUS",
    "Dutch East Indies": "DEI", "Portugal": "POR", "Netherlands": "NET", "Sokoto": "SOK",
    "Sweden": "SWE", "South Africa": "SAF", "Belgium": "BEL",
}
# localized building display name -> good
BUILDING2GOOD = {
    "Banana Plantations": "fruit", "Coffee Plantations": "coffee", "Dye Plantations": "dye",
    "Lead Mines": "lead", "Sugar Plantations": "sugar", "Vineyards": "wine", "Coal Mines": "coal",
    "Cotton Plantations": "fabric", "Tea Plantations": "tea", "Tobacco Plantations": "tobacco",
    "Opium Plantations": "opium", "Silk Plantations": "silk", "Sulfur Mines": "sulfur",
    "Fishing Wharves": "fish", "Iron Mines": "iron", "Logging Camps": "wood",
}


def planned_flavour():
    out = {}
    with open(os.path.join(HERE, "SELECT_ECOBOOST_FINAL_v2.csv"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.startswith("tag,"):
                continue
            p = [x.strip() for x in line.rstrip("\n").split(",")]
            if len(p) >= 6 and p[0]:
                out[p[0]] = p[5].split()
    return out


def built_flavour():
    d = json.load(open(TIMELINE, encoding="utf-8"))
    out = {}
    for r in d["eco"]:
        if r["type"] != "flavour":
            continue
        tag = COUNTRY2TAG.get(r["country"])
        good = BUILDING2GOOD.get(r["building"])
        if tag and good:
            out.setdefault(tag, set()).add(good)
    return out


def main():
    planned = planned_flavour()
    built = built_flavour()
    built_rows, unbuilt_rows = [], []
    seen_tags = set()
    nb = nu = 0
    for tag, goods in planned.items():
        b = built.get(tag, set())
        if tag in built:
            seen_tags.add(tag)
        for g in goods:
            if g in b:
                built_rows.append((tag, g)); nb += 1
            else:
                unbuilt_rows.append((tag, g)); nu += 1
    for name, rows in (("eco_flavour_built.csv", built_rows), ("eco_flavour_unbuilt.csv", unbuilt_rows)):
        with open(os.path.join(HERE, name), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["tag", "good"]); w.writerows(rows)
    missing = sorted(set(planned) - seen_tags)
    print(f"planned flavour entries: {nb+nu} | BUILT: {nb} | UNBUILT: {nu}")
    print(f"tags with ANY flavour build: {len(seen_tags)}/{len(planned)}")
    print(f"tags with ZERO flavour builds (no eco markers in log - investigate): {' '.join(missing)}")
    print("wrote eco_flavour_built.csv + eco_flavour_unbuilt.csv")


if __name__ == "__main__":
    main()
