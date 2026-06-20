#!/usr/bin/env python3
r"""
gen_champ_support_flavour.py — per-nation Champion / Support / Flavour candidates.

NEW schema (user 2026-06-14), written to SELECT_CHAMP_SUPPORT_FLAVOUR.csv (does NOT clobber
the hand-curated champ_candidates.csv):
  tag | country | X | market_access | champ_candidates(3 ranked) |
  support_candidates(5) | flavour(6) | notes

Design rules (fold in a 2nd AI's parallel pass, user-endorsed):
- CHAMPION = the nation's distinctive economic IDENTITY (not generic food). Scored from
  prestige goods (game-flagged distinctive goods), existing distinctive industry, and
  identity export crops. EXCLUDED as champs: hardwood (logging byproduct), oil + rubber
  (post-1836), clippers (shipyard/convoy good), gold (gold_field is post-1836 prospecting),
  steamers, and the infra goods (services/transportation/electricity/merchant_marine).
  Generic staple food (grain/meat/fish) is heavily de-weighted for champ — it's support.
  `^` marks a champ candidate NOT produced at 1836 but with strong unused RGO/arable slots.
- SUPPORT(5) = the supply-chain inputs the economy is most SHORT of (building-input deficits
  from starting_economy_prod_cons.csv) — i.e. what stabilises production / lets the champion
  scale within ~4 years. Champion good itself excluded.
- FLAVOUR(6) = NEW character builds: 1 per unused RGO (plantation / capped mine — NOT
  discoverable oil_rig/gold_field) the tag has, plus a desperately-wanted absent base
  building (iron/coal/tools produced ~0). MUST NOT duplicate any support good. Developed
  GPs with no unused slots & no gaps correctly get `none` (e.g. PRU).
- Market isolation: market_access=no (no trade centre -> can't import) -> x2 weight on
  iron + wood self-sufficiency in support ranking.

Inputs (all in hk-config/tools/): mod-nations.csv, arable_rgo_by_nation.csv,
future_needs_by_nation.csv, state_buildings.csv, starting_economy_prod_cons.csv,
unused_rgo_by_nation.csv.

Usage: python gen_champ_support_flavour.py
"""
import csv, os, math
from collections import defaultdict


def write_xlsx(path, cols, rows, legend):
    """Render the plan as a formatted workbook. Returns path, or None if openpyxl missing."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "EcoBoost Plan"

    head_fill = PatternFill("solid", fgColor="1F4E78")
    head_font = Font(bold=True, color="FFFFFF", size=11)
    legend_font = Font(italic=True, color="444444", size=10)
    title_font = Font(bold=True, size=12, color="1F4E78")
    iso_fill = PatternFill("solid", fgColor="FCE4D6")        # isolated nations
    tier_fill = PatternFill("solid", fgColor="FFF2CC")       # X tier cell
    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(vertical="top", wrap_text=True)
    center = Alignment(horizontal="center", vertical="center")

    r = 1
    for i, ln in enumerate(legend):
        ws.cell(r, 1, ln).font = title_font if i == 0 else legend_font
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(cols))
        r += 1
    r += 1  # blank spacer

    header_row = r
    for c, name in enumerate(cols, 1):
        cell = ws.cell(header_row, c, name)
        cell.fill = head_fill; cell.font = head_font
        cell.alignment = center; cell.border = border
    r += 1

    for row in rows:
        iso = row.get("market_access") == "no"
        for c, name in enumerate(cols, 1):
            cell = ws.cell(r, c, row.get(name, ""))
            cell.alignment = wrap; cell.border = border
            if name == "X":
                cell.fill = tier_fill; cell.alignment = center
            elif iso and name in ("tag", "country", "market_access"):
                cell.fill = iso_fill
        r += 1

    widths = {"tag": 6, "country": 15, "X": 4, "market_access": 7, "identity": 26,
              "champ_candidates": 24, "support_candidates": 30, "flavour": 34,
              "company_goods": 22, "old_picks": 14, "notes": 18}
    for c, name in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(c)].width = widths.get(name, 14)

    ws.freeze_panes = ws.cell(header_row + 1, 3)            # freeze header + tag/country
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(cols))}{header_row}"
    wb.save(path)
    return path

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- building <-> good map (reuse of champ_candidates.py, kept in sync) -------------
BUILDING_GOOD = {
    "cotton_plantation": "fabric", "dye_plantation": "dye", "opium_plantation": "opium",
    "silk_plantation": "silk", "tea_plantation": "tea", "tobacco_plantation": "tobacco",
    "coffee_plantation": "coffee", "sugar_plantation": "sugar", "banana_plantation": "fruit",
    "rubber_plantation": "rubber", "vineyard": "wine",
    "rye_farm": "grain", "wheat_farm": "grain", "maize_farm": "grain", "millet_farm": "grain",
    "rice_farm": "grain", "livestock_ranch": "meat", "fishing_wharf": "fish",
    "whaling_station": "meat",
    "coal_mine": "coal", "iron_mine": "iron", "lead_mine": "lead", "sulfur_mine": "sulfur",
    "gold_mine": "gold", "oil_rig": "oil", "logging_camp": "wood",
    "steel_mill": "steel", "arms_industry": "small_arms", "artillery_foundry": "artillery",
    "chemical_plant": "fertilizer", "tooling_workshop": "tools", "textile_mill": "clothes",
    "glassworks": "glass", "paper_mill": "paper", "furniture_manufactory": "furniture",
    "food_industry": "groceries", "motor_industry": "engines",
    "munition_plant": "ammunition", "explosives_factory": "explosives",
}
GOOD_BUILDING = {  # for flavour "build this" suggestions (canonical producer)
    "iron": "iron_mine", "coal": "coal_mine", "tools": "tooling_workshop",
    "lead": "lead_mine", "sulfur": "sulfur_mine", "wood": "logging_camp",
}

# champ eligibility. Excludes byproducts/post-1836/infra goods so a 1836 CHAMPION pick is
# realistic. Post-1836 (automobiles/telephones/radios/aeroplanes/tanks/electronics/plastics)
# leak in via future-want prestige goods (e.g. turin_automobiles, ericsson telephones) — they
# are not 1836 champions.
EXCLUDE_CHAMP = {"hardwood", "oil", "rubber", "clippers", "gold", "steamers",
                 "services", "transportation", "electricity", "merchant_marine",
                 "automobiles", "telephones", "radios", "aeroplanes", "tanks",
                 "electronics", "plastics"}
IDENTITY_CROPS = {"silk", "tea", "dye", "coffee", "sugar", "tobacco", "opium", "wine", "fruit"}
STAPLE_FOOD = {"grain", "meat", "fish"}
# Champion-worthy manufacturing = heavy / military / capital goods only. Generic ubiquitous
# processing (groceries/paper/clothes/furniture/glass/fertilizer) is SUPPORT/welfare, NOT a
# national identity -- including it drowned out identity goods (e.g. JAP -> groceries/paper
# instead of silk/tea). Those generic goods still surface as support via the deficit ranking.
DISTINCTIVE_INDUSTRY = {"steel", "artillery", "small_arms", "tools", "engines",
                        "ammunition", "explosives"}
# flavour: only plantation + capped-mine RGOs count (NOT discoverable oil_rig/gold_field)
FLAVOUR_EXCLUDE_RGO = {"oil_rig", "gold_field"}

# Vic3 GOODS_SHORTAGE_PENALTY_THRESHOLD (common/defines/00_defines.txt): when supply/demand
# drops BELOW this, consuming buildings start taking output penalties. The <need> tag is shown
# ONLY for goods in this real penalty zone (a mild deficit self-corrects on price, no penalty).
SHORTAGE_RATIO = 0.5

# Short (<8 word) editorial identity per nation — for the enriched review sheet.
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


def main():
    nations = {r["tag"]: {"country": r["country"], "X": int(r["X"])} for r in load_csv("mod-nations.csv")}

    # market access = has trade_center at 1836
    tc = set()
    has = defaultdict(lambda: defaultdict(int))   # tag -> good -> levels
    for r in load_csv("state_buildings.csv"):
        if r["building"] == "trade_center":
            tc.add(r["tag"])
        g = BUILDING_GOOD.get(r["building"])
        if g:
            has[r["tag"]][g] += int(r["levels"])

    # arable/buildable goods per tag
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

    # prestige goods per tag
    prestige = defaultdict(set)
    for r in load_csv("future_needs_by_nation.csv"):
        for tok in r["prestige_goods"].split():
            if "(" in tok:
                prestige[r["tag"]].add(tok.split("(")[1].rstrip(")"))

    # produced / consumed per tag (active-PM accurate)
    produced = defaultdict(lambda: defaultdict(float))
    consumed = defaultdict(lambda: defaultdict(float))
    for r in load_csv("starting_economy_prod_cons.csv"):
        produced[r["tag"]][r["good"]] = float(r["produced"])
        consumed[r["tag"]][r["good"]] = float(r["consumed"])

    # (SoL-9 pop demand intentionally NOT loaded: shortage detection uses building-input
    # demand only - pop/SoL-9 demand overstates 1836 demand and mis-flags balanced goods.)

    # unused RGO per tag
    unused = {}
    for r in load_csv("unused_rgo_by_nation.csv"):
        unused[r["tag"]] = {
            "plantations": r["unused_plantations"].split(),
            "farms": r["unused_farms"].split(),
            "capped": r["unused_capped"].split(),
        }

    # user's earlier hand picks (champ_candidates.csv pick + support wishlist) -> just the goods
    old_pick = {}
    for r in load_csv("champ_candidates.csv"):
        def _clean(x):
            return (x or "").split("(")[0].strip()      # drop any "(score)" suffix
        pk = _clean(r.get("pick"))
        sp = _clean(r.get("support /what I kindof wanted") or r.get("support"))
        goods = [g for g in (pk, sp) if g and g != "-"]
        old_pick[r["tag"]] = " ".join(dict.fromkeys(goods))   # dedupe, keep order

    # company GOODS the nation's flavored companies target, as good[n] (n = how many of its
    # flavored-company prestige goods map to that good). Goods-only, slim (no company names).
    companies = {}   # tag -> {good: n}
    for r in load_csv("future_needs_by_nation.csv"):
        cnt = {}
        for tok in r["prestige_goods"].split():
            if "(" in tok:
                g = tok.split("(")[1].rstrip(")")
                if g in EXCLUDE_CHAMP and g not in ("merchant_marine",):
                    pass  # keep even post-1836 here (it's "aim for", informational)
                cnt[g] = cnt.get(g, 0) + 1
        companies[r["tag"]] = cnt

    # per-level goods output per good (global avg = total produced / total building levels),
    # to convert a goods deficit into a BUILDING-LEVEL count for the (have)<need> notation.
    _lvl, _out = defaultdict(float), defaultdict(float)
    for t in nations:
        for g, lv in has[t].items():
            _lvl[g] += lv
        for g, p in produced[t].items():
            _out[g] += p
    per_level = {g: _out[g] / _lvl[g] for g in _lvl if _lvl[g] > 0 and _out[g] > 0}
    DEFAULT_PER_LEVEL = 30.0

    def lvl_need(good, goods_deficit):
        if goods_deficit <= 0:
            return 0
        return max(1, math.ceil(goods_deficit / (per_level.get(good) or DEFAULT_PER_LEVEL)))

    rows = []
    for tag, info in nations.items():
        ma = "yes" if tag in tc else "no"
        h, ar, pr = has[tag], arable[tag], prestige[tag]
        prod, cons = produced[tag], consumed[tag]
        notes = []

        # ---------- CHAMPION (3 ranked) ----------
        pool = set(ar) | set(pr) | set(h.keys())
        champ_scored = []
        for g in pool:
            if g in EXCLUDE_CHAMP:
                continue
            score = 0.0
            if g in pr:
                score += 6
            if g in DISTINCTIVE_INDUSTRY and h.get(g, 0) > 0:
                score += 3 + min(h[g], 5)
            if g in IDENTITY_CROPS and g in ar:
                score += 4
            if (g in pr or g in IDENTITY_CROPS) and h.get(g, 0) > 0:
                score += 3 + min(h[g], 4)          # established producing identity
            if g in STAPLE_FOOD:
                score += 0.5
            if ma == "no" and g in IDENTITY_CROPS:
                score -= 3
            if score > 0:
                champ_scored.append((score, g))
        champ_scored.sort(key=lambda x: (-x[0], x[1]))
        champ_goods = {g for _, g in champ_scored[:3]}

        def have_disp(g):                           # good(levels) | good^ (potential, no build)
            lv = h.get(g, 0)
            return f"{g}({lv})" if lv > 0 else (f"{g}^" if g in ar else g)

        champ = [have_disp(g) for _, g in champ_scored[:3]]

        # ---------- SUPPORT: building-input SHORTAGE-PENALTY goods ----------
        # Penalty zone = production / building-input demand < SHORTAGE_RATIO (0.5): consuming
        # buildings take output penalties (Vic3 GOODS_SHORTAGE_PENALTY_THRESHOLD). Pop/SoL-9
        # demand is deliberately NOT used here - it overstates 1836 demand and mis-flags
        # balanced goods (e.g. JAP wood = 0.89 here = no penalty, matching the in-game market;
        # PAN wood = 0.40 = real penalty, matching in-game testing).
        def shortage(good):
            d, s = cons.get(good, 0.0), prod.get(good, 0.0)
            if d <= 0 or s / d >= SHORTAGE_RATIO:
                return (False, 0)
            return (True, lvl_need(good, d - s))      # levels to lift production up to demand

        sup_scored = []
        for g in cons:
            if g in champ_goods or g in EXCLUDE_CHAMP:
                continue
            pen, need = shortage(g)
            if not pen:
                continue
            w = 2.0 if (ma == "no" and g in ("iron", "wood")) else 1.0
            sup_scored.append(((cons[g] - prod.get(g, 0.0)) * w, g, need))
        sup_scored.sort(key=lambda x: (-x[0], x[1]))
        support_set = {g for _, g, _ in sup_scored[:5]}

        def need_disp(g, need):
            lv = h.get(g, 0)
            if lv > 0:
                return f"{g}({lv})<{need}>"
            return f"{g}^<{need}>" if g in ar else f"{g}(0)<{need}>"

        support = [need_disp(g, need) for _, g, need in sup_scored[:5]]
        if not support:
            notes.append("no input shortages")

        # ---------- FLAVOUR (6, GOODS-only): gold forced, then base gaps, plantations, mines ----
        # whaling -> meat* (* = whale, distinct from ranch meat). Flavour goods carry the same
        # shortage <need> tag only when the good is in the building-input penalty zone.
        def flav_disp(good, whale=False):
            base = (good + "*") if whale else good
            pen, need = shortage(good)
            if pen:
                lv = h.get(good, 0)
                return f"{base}({lv})<{need}>" if lv > 0 else f"{base}<{need}>"
            return base

        u = unused.get(tag, {"plantations": [], "farms": [], "capped": []})
        flav, seen = [], set()
        def add_flav(good, whale=False, force=False):
            key = (good, whale)
            if not good or key in seen:
                return
            if not force and (good in support_set or good in champ_goods):
                return
            seen.add(key); flav.append((good, whale))
        # gold ALWAYS first when any unused gold MINE exists (best ROI, 1/state)
        if "gold_mine" in u["capped"]:
            add_flav("gold", force=True)
        # desperately-wanted base good absent at start (iron/coal/tools)
        for g in ("iron", "coal", "tools"):
            if prod.get(g, 0.0) == 0 and (g in ar or cons.get(g, 0) > 0):
                add_flav(g)
        # unused plantations (identity crops) then capped mines / whaling / logging
        for b in u["plantations"] + u["capped"]:
            if b not in FLAVOUR_EXCLUDE_RGO:
                add_flav(BUILDING_GOOD.get(b), whale=(b == "whaling_station"))
        flav = flav[:6]
        flavour = " ".join(flav_disp(g, whale) for g, whale in flav) if flav else "none"
        if not flav:
            notes.append("developed, no unused RGO")
        if ma == "no":
            notes.append("isolated: iron+wood x2")

        cg = companies.get(tag, {})
        comp_goods = " ".join(f"{g}[{n}]" for g, n in sorted(cg.items(), key=lambda x: -x[1]))

        rows.append({
            "tag": tag, "country": info["country"], "X": info["X"], "market_access": ma,
            "identity": IDENTITY.get(tag, ""),
            "champ_candidates": " ".join(champ), "support_candidates": " ".join(support),
            "flavour": flavour, "company_goods": comp_goods,
            "old_picks": old_pick.get(tag, ""), "notes": "; ".join(notes),
        })

    rows.sort(key=lambda r: (-r["X"], r["country"]))
    cols = ["tag", "country", "X", "market_access", "identity", "champ_candidates",
            "support_candidates", "flavour", "company_goods", "old_picks", "notes"]

    LEGEND = [
        "Top40EcoBoost - per-nation Champion, Support, Flavour plan (goods only). Regenerate: gen_champ_support_flavour.py",
        "NOTATION (numbers are BUILDING LEVELS, not goods units):",
        "           good(2)<3> = nation has ~2 building levels making good but is in SHORTAGE PENALTY; build ~3 more to cover input demand.",
        "           <> appears ONLY when production divided by building-input demand is below 0.5 (Vic3 GOODS_SHORTAGE_PENALTY_THRESHOLD):",
        "                consuming buildings then take output penalties. Pop (SoL) demand is excluded - it overstates 1836 demand.",
        "           good^      = strong RGO or arable potential for good but builds NONE at 1836 start.",
        "           good*      = whaling-sourced (whale): meat* = meat from a whaling station (unique coastal flavour).",
        "           good[5]    = company col: good is targeted by 5 of the nation's flavored companies (aim to form them).",
        "CHAMP   = export identity (3 ranked candidates, pick 1).   SUPPORT = building inputs currently in shortage penalty.",
        "FLAVOUR = unbuilt RGOs to seed for character (goods only). Any unused GOLD mine is always listed first (best ROI).",
        "old_picks = your earlier hand picks (champion plus support wishlist).",
    ]

    # CSV source (git-diffable): legend lines (#) then header + rows
    out_csv = os.path.join(HERE, "SELECT_ECOBOOST_PLAN.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        for ln in LEGEND:
            f.write("# " + ln + "\n")
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # formatted XLSX
    xlsx_path = write_xlsx(os.path.join(HERE, "SELECT_ECOBOOST_PLAN.xlsx"), cols, rows, LEGEND)

    print(f"wrote {os.path.basename(out_csv)} + {os.path.basename(xlsx_path) if xlsx_path else '(xlsx skipped: openpyxl missing)'} ({len(rows)} nations)")
    for t in ("JAP", "PRU", "BRZ"):
        r = next((x for x in rows if x["tag"] == t), None)
        if r:
            print(f"  {t}: C[{r['champ_candidates']}] S[{r['support_candidates']}] F[{r['flavour']}] co[{r['company_goods']}]")


if __name__ == "__main__":
    main()
