#!/usr/bin/env python3
"""
compute_x.py — Mod 1 X-factor, pop-first priority.

Reads tools/country_stats.csv and computes per country:
    pop_term  = sqrt(pop_millions)            # POPULATION first (sqrt so Qing's 366M
                                              #   leads but doesn't flatten the ladder)
    gdp_index = gdp_proxy / gdp_proxy(ref)    # GDP second, ref (GBR) = 1.0
    X_raw     = POP_W*pop_term + GDP_W*gdp_index + STATE_W*homeland_states
    X         = min(floor(X_raw), CAP)        # homeland (core) states third

Priority is pop > gdp > states, enforced by the weights below (the calibration knob).
States term uses HOMELAND states only (core economy), not colonial holdings.

Usage: python compute_x.py [--top 60] [--ref GBR]
"""
import os, csv, math, argparse

# --- CALIBRATION KNOBS (pop-first) ---
# Baseline formula (chosen so the unspecified / "must stay" nations land correctly:
# Turkey 9, Japan 8, Prussia 7, Spain/Austria/Mexico 6, Brazil/Korea/Persia 5,
# Hungary/Portugal/Two Sicilies 4, Hyderabad/Dai Nam 3, specialists 2).
POP_W, GDP_W, STATE_W, CAP = 1.0, 3.0, 0.2, 10

# --- DESIGN OVERRIDES (pin specific nations; these beat the formula) ---
# Used where design intent contradicts raw stats (e.g. Punjab > Hyderabad). Only listed
# tags are affected, so nothing else can drift / no outliers. Empty = pure formula.
X_OVERRIDE = {
    # giants — keep at the top (build the most here)
    "CHI": 10, "BIC": 10, "RUS": 10,
    # ease the western great powers down a notch
    "GBR": 9, "FRA": 9, "USA": 9,
    # raise to 5
    "EGY": 5, "PAN": 5, "DEI": 5,
    # raise to 4
    "SWE": 4, "NET": 4, "SAR": 4, "SOK": 4,
    # set to 3
    "CLM": 3, "GRE": 3, "ARG": 3, "NEP": 3,
    # explicit 2 (incl. floored must-include expanders that start tiny)
    "PHI": 2, "OMA": 2, "SHW": 2, "SAF": 2,
}

def main():
    here = os.path.dirname(__file__)
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=os.path.join(here, "country_stats.csv"))
    ap.add_argument("--out", default=os.path.join(here, "country_x.csv"))
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--ref", default="GBR")
    args = ap.parse_args()

    rows = []
    with open(args.inp, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in ("gdp_proxy", "pop", "homeland_states", "total_states", "provinces"):
                r[k] = float(r[k])
            rows.append(r)

    ref = next((r for r in rows if r["tag"] == args.ref), None)
    if not ref or ref["gdp_proxy"] == 0:
        raise SystemExit(f"Reference tag {args.ref} not found / zero gdp_proxy")
    ref_gdp = ref["gdp_proxy"]

    for r in rows:
        pop_m = r["pop"] / 1_000_000
        gdp_idx = r["gdp_proxy"] / ref_gdp
        x_raw = POP_W * math.sqrt(pop_m) + GDP_W * gdp_idx + STATE_W * r["homeland_states"]
        x_formula = min(int(math.floor(x_raw)), CAP)
        pinned = r["tag"] in X_OVERRIDE
        r.update(pop_m=round(pop_m, 2), gdp_index=round(gdp_idx, 3), x_raw=round(x_raw, 2),
                 x_formula=x_formula, x=(X_OVERRIDE[r["tag"]] if pinned else x_formula),
                 pinned=("PIN" if pinned else ""))

    rows.sort(key=lambda r: (r["x"], r["x_raw"]), reverse=True)

    cols = ["tag", "country", "x", "pinned", "x_formula", "x_raw",
            "pop_m", "gdp_index", "homeland_states", "total_states"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows: w.writerow(r)

    print(f"Formula: X = min(floor({POP_W}*sqrt(popM) + {GDP_W}*gdp_idx + {STATE_W}*homeland_states), {CAP})"
          f"  + {len(X_OVERRIDE)} design overrides  [gdp_idx vs {args.ref}=1.0]\n")
    print(f"{'#':>3} {'tag':<4} {'country':<20} {'X':>2} {'':>3} {'f':>2} {'x_raw':>6} {'popM':>7} {'gdp_i':>6} {'home':>4}")
    print("-" * 64)
    for i, r in enumerate(rows[:args.top], 1):
        print(f"{i:>3} {r['tag']:<4} {r['country'][:20]:<20} {r['x']:>2} {r['pinned']:>3} "
              f"{r['x_formula']:>2} {r['x_raw']:>6} {r['pop_m']:>7} {r['gdp_index']:>6} {int(r['homeland_states']):>4}")
    print(f"\nFull ladder ({len(rows)} tags) -> {args.out}   (PIN = design override; f = formula value)")

if __name__ == "__main__":
    main()
