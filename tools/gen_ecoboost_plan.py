#!/usr/bin/env python3
r"""
gen_ecoboost_plan.py — Top40EcoBoost analysis, STAGE 2 (polish).

Reads the barebones SELECT_ECOBOOST_WIP.csv (stage 1) and applies the champ-scoring rules
tuned by pattern-matching against known-good picks (CHI=tea/silk, USA=cotton, JAP=silk,
PRU=steel, PAN=cotton). Emits SELECT_ECOBOOST_PLAN.csv (+ .xlsx) to FINALIZE a champion
(and 1-2 support) per nation.

This pass FOCUSES on the champion. Support is a loose first-cut ("best to build x of in the
first ~4-5 yrs", incl. empty-but-wanted goods routed here); a dedicated support pass and a
flavour pass follow later. Whale/gold are not here (Track-B history seeding handles them).

Scoring (all weights are knobs - tweak freely; that's the point of stage 2):
  pool = goods that are NOT generic-manufacturing / NOT champ-excluded.
  score = scale(=building levels a; staples x STAPLE_DEWEIGHT)
        + IDENTITY_BONUS      if identity crop (incl. fabric = cotton textile)
        + INDUSTRY_BONUS      if distinctive industry (steel/tools/arms/...)
        + PRESTIGE_BONUS      if a game-flagged prestige good
        + COMPANY_W * (#flavored companies targeting it)
        + STANDOUT_BONUS      if the tag is a relatively big producer (a >= 2x median)
        + base-industry nudge (steel/engines) when the tag self-supplies iron+coal / steel
        + opportunity bonus   if buildable-but-unbuilt (^) AND in shortage AND high demand
  An empty good WANTED but NOT buildable (potential=0) gets no opportunity credit -> it
  falls to SUPPORT instead of champ (per user rule).

Inputs (hk-config/tools/): SELECT_ECOBOOST_WIP.csv, mod-nations.csv,
  future_needs_by_nation.csv (company goods, hardwood rendered wood*), champ_candidates.csv (old picks).
Usage: python gen_ecoboost_plan.py
"""
import os, csv
from collections import defaultdict
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- scoring knobs ----
IDENTITY_BONUS  = 25
INDUSTRY_BONUS  = 18
PRESTIGE_BONUS  = 20
COMPANY_W       = 8
STANDOUT_BONUS  = 12
STANDOUT_MULT   = 2.0      # standout if a >= STANDOUT_MULT * median(positive a for the good)
STAPLE_DEWEIGHT = 0.35
STEEL_NUDGE     = 25       # steel when iron & coal are locally present
ENGINE_NUDGE    = 18       # engines when steel is locally present
OPP_BONUS       = 30       # opportunity: buildable-but-unbuilt + shortage + high demand
OPP_STARTER     = 5        # extra if that opportunity good is an eco-starter (e.g. cotton/fabric)
OPP_DEMAND_HI   = 100      # min absolute demand to count as an opportunity champ
SUPPORT_N       = 5
ECO_STARTERS    = {"iron", "wood", "grain", "fish", "fabric", "tools"}
# finished military goods are a SEPARATE lever (roadmap 2.7), never the eco champion
MILITARY        = {"artillery", "small_arms", "ammunition"}

# editorial one-liner per tag (curated; kept here, not derivable)
IDENTITY = {
    "CHI": "silk, tea & porcelain export titan", "RUS": "grain & timber resource giant",
    "BIC": "tea & textile subcontinent", "USA": "cotton, grain & nascent industry",
    "FRA": "wine, arms & luxury prestige", "GBR": "steel & tools, workshop of world",
    "TUR": "agrarian crossroads, military revival", "JAP": "silk, washi paper & soy sauce",
    "PRU": "Krupp artillery & heavy steel", "SPA": "agrarian colonial remnant",
    "AUS": "diversified industrial heartland", "MEX": "silver, coffee & dye",
    "KOR": "isolated agrarian hermit kingdom", "BRZ": "coffee plantation giant",
    "PER": "opium, carpets & dye", "EGY": "cotton (fabric) & grain",
    "PAN": "cotton, arms & Sikh artillery", "DEI": "coffee, dye & spice islands",
    "HUN": "grain breadbasket", "POR": "wine, fish & colonial trade",
    "SIC": "Sicilian sulfur monopoly", "NET": "trade, textiles & colonial goods",
    "SOK": "cotton & tropical cash crops", "SAR": "steel & early industry",
    "SWE": "bar iron & engineering", "HYD": "cotton & princely agriculture",
    "GRE": "wine, tobacco & maritime", "DAI": "rice, coffee & silk",
    "NEP": "Himalayan opium & timber", "CLM": "coffee & tobacco",
    "ARG": "cattle (meat) & grain pampas", "SIA": "rice & tropical exports",
    "MOR": "agrarian livestock & coast", "OMA": "coffee, dates & ocean trade",
    "SHW": "Ethiopian coffee highlands", "SAF": "wine, wool & frontier mining",
    "PHI": "sugar & tropical plantations", "BEL": "coal, steel & tools industry",
    "BAV": "beer (wine), grain & timber", "BUR": "rice, teak & opium",
}


def load_csv(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v, typ=float, default=0):
    try:
        return typ(v)
    except (TypeError, ValueError):
        return default


def main():
    order = [r["tag"] for r in load_csv("mod-nations.csv")]

    # WIP signals: data[tag][good] = row(dict of parsed signals)
    data = defaultdict(dict)
    a_by_good = defaultdict(list)
    meta = {}
    for r in load_csv("SELECT_ECOBOOST_WIP.csv"):
        t, g = r["tag"], r["good"]
        row = {
            "a": num(r["a"], int), "produced": num(r["produced"]),
            "demand": num(r["demand"]), "ratio": num(r["ratio"], float, None),
            "b": num(r["b"], int), "shortage": r["shortage"] == "1",
            "potential": r["potential"] == "1", "prestige": r["prestige"] == "1",
            "identity_crop": r["identity_crop"] == "1",
            "distinctive_ind": r["distinctive_ind"] == "1",
            "staple_food": r["staple_food"] == "1", "generic_mfg": r["generic_mfg"] == "1",
            "eco_starter": r["eco_starter"] == "1", "excl_champ": r["excl_champ"] == "1",
            "company": num(r["company"], int),
        }
        data[t][g] = row
        meta[t] = {"country": r["country"], "X": num(r["X"], int), "mkt": r["mkt"]}
        if row["a"] > 0:
            a_by_good[g].append(row["a"])

    standout = {g: max(3, STANDOUT_MULT * median(v)) for g, v in a_by_good.items()}

    # company goods (preserve hardwood -> render wood*), incl. post-1836 "aim-for" goods
    company_str = {}
    for r in load_csv("future_needs_by_nation.csv"):
        cnt = defaultdict(int)
        for tok in r["prestige_goods"].split():
            if "(" in tok:
                g = tok.split("(")[1].rstrip(")")
                cnt["wood*" if g == "hardwood" else g] += 1
        company_str[r["tag"]] = " ".join(f"{g}[{n}]" for g, n in
                                          sorted(cnt.items(), key=lambda x: -x[1]))

    # old hand picks (champion + support wishlist) for reference
    old = {}
    for r in load_csv("champ_candidates.csv"):
        def clean(x):
            return (x or "").split("(")[0].strip()
        goods = [g for g in (clean(r.get("pick")),
                             clean(r.get("support /what I kindof wanted") or r.get("support")))
                 if g and g != "-"]
        old[r["tag"]] = " ".join(dict.fromkeys(goods))

    def champ_score(t, g, row):
        """Established producers (a>0) score on scale+identity+industry+prestige+nudge.
        An unbuilt good (a==0) qualifies ONLY as a buildable opportunity (potential +
        shortage + real demand); otherwise it is not a champ (falls to support). This is
        the 'empty-but-wanted -> support' rule, applied to prestige-backed empties too."""
        a = row["a"]
        if a > 0:
            s = a * (STAPLE_DEWEIGHT if row["staple_food"] else 1.0)
            if row["identity_crop"]:
                s += IDENTITY_BONUS
            if row["distinctive_ind"]:
                s += INDUSTRY_BONUS
            if row["prestige"]:
                s += PRESTIGE_BONUS
            s += COMPANY_W * row["company"]
            if a >= standout.get(g, 1e9):
                s += STANDOUT_BONUS
            # base-industry nudge: heavy industry the tag can self-feed
            if g == "steel" and data[t].get("iron", {}).get("a", 0) > 0 and data[t].get("coal", {}).get("a", 0) > 0:
                s += STEEL_NUDGE
            if g == "engines" and data[t].get("steel", {}).get("a", 0) > 0:
                s += ENGINE_NUDGE
            return s
        # a == 0: champ only as a buildable opportunity, else None (-> support)
        if row["potential"] and row["shortage"] and row["demand"] >= OPP_DEMAND_HI:
            s = OPP_BONUS + (OPP_STARTER if row["eco_starter"] else 0)
            if row["identity_crop"]:
                s += IDENTITY_BONUS * 0.4
            return s
        return None

    def champ_disp(g, row):
        return f"{g}({row['a']})" if row["a"] > 0 else f"{g}^"

    def need_disp(g, row):
        mark = f"{g}({row['a']})" if row["a"] > 0 else (f"{g}^" if row["potential"] else f"{g}(0)")
        return f"{mark}<{row['b']}>"

    rows = []
    for t in order:
        if t not in data:
            continue
        m = meta[t]
        goods = data[t]

        # ---- CHAMPION (3 ranked) ----
        pool = []
        for g, r in goods.items():
            if r["generic_mfg"] or r["excl_champ"] or g in MILITARY:
                continue
            sc = champ_score(t, g, r)
            if sc is not None:
                pool.append((sc, g, r))
        pool.sort(key=lambda x: (-x[0], -x[2]["produced"]))
        champ3 = pool[:3]
        champ_pick = champ3[0][1] if champ3 else ""
        champ_candidates = " ".join(champ_disp(g, r) for _, g, r in champ3)

        # ---- SUPPORT (loose; shortage goods incl. empty-but-wanted, excl. the #1 champ) ----
        sup = [(r["demand"] - r["produced"], g, r) for g, r in goods.items()
               if r["shortage"] and g != champ_pick]
        sup.sort(key=lambda x: -x[0])
        support = " ".join(need_disp(g, r) for _, g, r in sup[:SUPPORT_N])

        # ---- MUST-HAVE eco-starters in shortage (self-sufficiency flags) ----
        must = " ".join(need_disp(g, goods[g]) for g in
                        sorted(ECO_STARTERS, key=lambda g: -(goods.get(g, {}).get("demand", 0)))
                        if g in goods and goods[g]["shortage"])

        notes = []
        if not support:
            notes.append("no input shortages")
        if m["mkt"] == "no":
            notes.append("isolated market")

        rows.append({
            "tag": t, "country": m["country"], "X": m["X"], "mkt": m["mkt"],
            "identity": IDENTITY.get(t, ""), "champ_candidates": champ_candidates,
            "support_candidates": support, "must_have_starters": must,
            "company_goods": company_str.get(t, ""), "old_picks": old.get(t, ""),
            "notes": "; ".join(notes),
        })

    cols = ["tag", "country", "X", "mkt", "identity", "champ_candidates",
            "support_candidates", "must_have_starters", "company_goods", "old_picks", "notes"]
    out = os.path.join(HERE, "SELECT_ECOBOOST_PLAN.csv")
    LEGEND = [
        "Top40EcoBoost CHAMP-selection pass (stage 2). Regenerate: gen_ecoboost_plan.py (reads SELECT_ECOBOOST_WIP.csv).",
        "good(a)   = a building levels of that good today.   good^ = can build it but 0 today (potential).",
        "good(a)<b>= SUPPORT/must-have: in shortage (produced/demand < 0.5); seed about b levels (b kept near a).",
        "CHAMP = 3 ranked candidates, pick 1 (this pass finalizes champ + maybe 1-2 support).",
        "SUPPORT = loose first-cut (best to build x of in ~4-5 yrs; incl. empty-but-wanted). Final support = a later pass.",
        "MUST-HAVE = the 6 eco-starters (iron/wood/grain/fish/fabric/tools) a tag can't self-supply >=0.5. wood/iron also seeded by Track-B.",
        "company[n] = good targeted by n flavored companies (wood* = hardwood). old_picks = your earlier hand picks.",
    ]
    with open(out, "w", newline="", encoding="utf-8") as f:
        for ln in LEGEND:
            f.write("# " + ln + "\n")
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote SELECT_ECOBOOST_PLAN.csv ({len(rows)} nations)")
    for t in ("CHI", "USA", "JAP", "PRU", "PAN"):
        r = next((x for x in rows if x["tag"] == t), None)
        if r:
            print(f"  {t}: CHAMP[{r['champ_candidates']}]  SUP[{r['support_candidates']}]")


if __name__ == "__main__":
    main()
