#!/usr/bin/env python3
"""
scan_starting_economy_1836.py -- split SoL-9 staple sheet + industrial supply-chain sheet,
built on the active-PM prod/cons table from scan_starting_economy.py.

Run scan_starting_economy.py FIRST (it writes starting_economy_prod_cons.csv, the long
per-(tag,good) produced/consumed table using each building's real active PMs).

Two output sheets (per user request, 2026-06-14 -- "split STAPLE_INDUS into 2 sheets"):

Each sheet is single-concept (no good's two roles crammed into one row -- staple = pop
welfare, industrial = supply-chain inputs):

  SELECT_STAPLE_1836.csv      -- pop-WELFARE only. For the kept staple goods:
      produced, pop_need_sol9, net
    pop_need_sol9 = wealth_9 buy-package need for that good * pop_millions (SoL 9 baseline,
    from common/buy_packages + common/pop_needs; see compute_staple_baseline). Treated as
    units per 1M pop -- a relative yardstick, not a calibrated absolute (no per-capita
    scaling define exists in common/defines). net = produced - pop_need_sol9. (Industrial
    consumption of staples like wood/fabric/paper is NOT mixed in here -- it lives in the
    industrial sheet's consumption column.)

  SELECT_INDUSTRIAL_1836.csv  -- supply-chain INPUTS only. Industrial-category goods that
    actually flow, PLUS wood (game-category staple, but the single largest intermediate
    input -- consumed by furniture/paper/tools buildings; its absence from the old
    industrial table was the red-flag bug that prompted this rewrite). Per good:
      produced, consumed (building inputs), net, pct_unmet
    These goods carry no pop need, so demand here is purely building-input consumption.

  SELECT_STAPLE_1836_baseline.csv -- the per-1M-pop SoL-9 need per staple good + sources.

Goods dropped from the STAPLE sheet (universal non-signal at 1836): services, transportation,
electricity, merchant_marine. The INDUSTRIAL sheet is data-driven (any industrial good with
real flow) -- note this now surfaces silk & dye as universal textile-input IMPORT gaps that
were invisible to the old first-PM scan; the previously-"minor" coal/sulfur/lead/fertilizer/
explosives/steel/engines remain but are narrow (only ~4-8 of the 40 touch them).

Usage: python scan_starting_economy_1836.py [GAME_DIR]
"""
import os, re, sys, csv
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
from _refpaths import game_path
DEFAULT_GAME = game_path()

KEPT_STAPLE = ["grain", "fish", "groceries", "fabric", "clothes", "wood", "furniture", "paper"]
# wood is staple-category but is the largest intermediate input -> explicitly cross-listed
# into the industrial sheet (the omission that prompted this rewrite).
INDUSTRIAL_EXTRA = ["wood"]
# preferred column order for the industrial sheet; any industrial good with flow not listed
# here is appended alphabetically.
INDUSTRIAL_ORDER = ["wood", "tools", "iron", "hardwood", "clippers", "silk", "dye",
                    "coal", "steel", "sulfur", "lead", "fertilizer", "explosives",
                    "engines", "glass", "oil"]


# --- brace helpers ----------------------------------------------------------
def match_brace(text, i):
    d = 0
    for k in range(i, len(text)):
        if text[k] == "{":
            d += 1
        elif text[k] == "}":
            d -= 1
            if d == 0:
                return k
    return len(text) - 1


def block_for(text, name, start=0):
    m = re.search(re.escape(name) + r"\s*=\s*\{", text[start:])
    if not m:
        return None
    i = start + m.end() - 1
    return text[i + 1:match_brace(text, i)]


# --- SoL-9 staple baseline (wealth_9 buy package x pop_needs weights) --------
def load_wealth9_goods(game):
    text = open(os.path.join(game, "common", "buy_packages", "00_buy_packages.txt"),
                 encoding="utf-8-sig").read()
    goods_body = block_for(block_for(text, "wealth_9"), "goods")
    return {m.group(1): float(m.group(2))
            for m in re.finditer(r"(popneed_\w+)\s*=\s*([\d.]+)", goods_body)}


def load_popneed_entries(game, categories):
    text = open(os.path.join(game, "common", "pop_needs", "00_pop_needs.txt"),
                 encoding="utf-8-sig").read()
    out = {}
    for cat in categories:
        body = block_for(text, cat)
        entries, idx = [], 0
        while body:
            m = re.search(r"entry\s*=\s*\{", body[idx:])
            if not m:
                break
            i = idx + m.end() - 1
            j = match_brace(body, i)
            ebody = body[i + 1:j]
            gm = re.search(r"goods\s*=\s*(\w+)", ebody)
            wm = re.search(r"weight\s*=\s*([\d.]+)", ebody)
            if gm:
                entries.append((gm.group(1), float(wm.group(1)) if wm else 1.0))
            idx = j + 1
        out[cat] = entries
    return out


def compute_staple_baseline(game):
    wealth9 = load_wealth9_goods(game)
    entries = load_popneed_entries(game, list(wealth9.keys()))
    baseline = {g: 0.0 for g in KEPT_STAPLE}
    sources = {g: [] for g in KEPT_STAPLE}
    for cat, qty in wealth9.items():
        ce = entries.get(cat, [])
        tw = sum(w for _, w in ce)
        if tw <= 0:
            continue
        for good, w in ce:
            if good in baseline:
                share = qty * w / tw
                baseline[good] += share
                sources[good].append((cat, round(share, 3)))
    return baseline, sources


def main():
    game = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GAME
    if not os.path.isdir(game):
        sys.exit(f"Game dir not found: {game}")

    pc_path = os.path.join(HERE, "starting_economy_prod_cons.csv")
    if not os.path.isfile(pc_path):
        sys.exit("Run scan_starting_economy.py first (missing starting_economy_prod_cons.csv)")

    # pivot long table -> produced[tag][good], consumed[tag][good], category, country
    produced = defaultdict(lambda: defaultdict(float))
    consumed = defaultdict(lambda: defaultdict(float))
    category = {}
    country = {}
    with open(pc_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t, g = r["tag"], r["good"]
            country[t] = r["country"]
            category[g] = r["category"]
            produced[t][g] = float(r["produced"])
            consumed[t][g] = float(r["consumed"])

    pop = {}
    with open(os.path.join(HERE, "country_stats.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pop[r["tag"]] = int(r["pop"])

    tags = sorted(country, key=lambda t: -pop.get(t, 0))

    print("Computing wealth_9 staple baseline ...")
    baseline, sources = compute_staple_baseline(game)
    with open(os.path.join(HERE, "SELECT_STAPLE_1836_baseline.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["good", "baseline_need_per_1m_pop", "wealth9_sources (popneed:share)"])
        for g in KEPT_STAPLE:
            w.writerow([g, round(baseline[g], 2),
                        "; ".join(f"{c}:{s}" for c, s in sources[g])])

    # --- STAPLE sheet (pop welfare only) --------------------------------------
    s_cols = ["tag", "country", "pop"]
    for g in KEPT_STAPLE:
        s_cols += [f"{g}_produced", f"{g}_pop_need", f"{g}_net"]
    with open(os.path.join(HERE, "SELECT_STAPLE_1836.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=s_cols)
        w.writeheader()
        for t in tags:
            pm = pop.get(t, 0) / 1_000_000
            row = {"tag": t, "country": country[t], "pop": pop.get(t, 0)}
            for g in KEPT_STAPLE:
                p = round(produced[t].get(g, 0.0), 1)
                pn = round(baseline[g] * pm, 1)
                row.update({f"{g}_produced": p, f"{g}_pop_need": pn, f"{g}_net": round(p - pn, 1)})
            w.writerow(row)

    # --- INDUSTRIAL sheet -----------------------------------------------------
    ind_goods = sorted(g for g, c in category.items() if c == "industrial")
    ind_goods = [g for g in ind_goods if g in INDUSTRIAL_ORDER or True]  # keep all w/ flow
    ind_list = INDUSTRIAL_EXTRA + [g for g in INDUSTRIAL_ORDER if g in ind_goods and g not in INDUSTRIAL_EXTRA]
    ind_list += [g for g in ind_goods if g not in ind_list]  # any stragglers

    i_cols = ["tag", "country"]
    for g in ind_list:
        i_cols += [f"{g}_produced", f"{g}_consumed", f"{g}_net", f"{g}_pct_unmet"]
    with open(os.path.join(HERE, "SELECT_INDUSTRIAL_1836.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=i_cols)
        w.writeheader()
        for t in tags:
            row = {"tag": t, "country": country[t]}
            for g in ind_list:
                p = round(produced[t].get(g, 0.0), 1)
                c = round(consumed[t].get(g, 0.0), 1)
                row.update({f"{g}_produced": p, f"{g}_consumed": c, f"{g}_net": round(p - c, 1),
                            f"{g}_pct_unmet": round((c - p) / c * 100, 1) if c > 0 else 0.0})
            w.writerow(row)

    print(f"Wrote SELECT_STAPLE_1836.csv ({len(KEPT_STAPLE)} staple goods)")
    print(f"Wrote SELECT_INDUSTRIAL_1836.csv ({len(ind_list)} goods: {', '.join(ind_list)})")
    print(f"Wrote SELECT_STAPLE_1836_baseline.csv")


if __name__ == "__main__":
    main()
