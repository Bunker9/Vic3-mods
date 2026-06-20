#!/usr/bin/env python3
"""
Feature ECO-YEARLY (Top40EcoBoostMod) — yearly-pulse eco building placements on the Timeline tab.
Uses the shared `timeline` analyzer (lib) and renders per-state placements by year.
Writes data_eco.json + aggr_eco.json + component.html (detail/grouped toggle).
"""
import sys, os

_D  = os.path.dirname(os.path.abspath(__file__))      # .../v2/<Mod>/<FEATURE-ID>
_V2 = os.path.normpath(os.path.join(_D, "..", ".."))  # .../v2
sys.path.insert(0, os.path.join(_V2, "testkit"))      # shared lib + analyzers (flat)

import lib_components as fb
import parse_timeline as tl_mod


def run(feature_dir=_D, logs_dir=None):
    mod  = fb.mod_name_from_feature_dir(feature_dir)
    logs = logs_dir or tl_mod.resolve_logs_dir()
    data = tl_mod.run(logs)
    eco  = data.get("eco", [])

    # --- aggregate: group by (year, country, building, type) summing count ---
    from collections import defaultdict
    grp = defaultdict(int)
    for r in eco:
        grp[(r["year"], r["country"], r["building"], r.get("type", "?"))] += r["count"]
    aggr = [{"year": y, "country": c, "building": b, "type": t, "count": n}
            for (y, c, b, t), n in sorted(grp.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1] or ""))]

    total = sum(r["count"] for r in eco)
    h = []
    h.append(f"<p>{fb.badge('grey', str(total) + ' total placements')}</p>")

    # Detail table (per-state)
    h.append("<div id='eco-detail'>")
    h.append(f"<p class='small'>Detail view — per state placement. "
             f"{fb.badge('grey', str(len(eco)) + ' rows')}</p>")
    if eco:
        rows = [[str(r["year"] or "?"), r["country"] or "?", r.get("state") or "?",
                 r["building"] or "?", r.get("type", "?"), str(r["count"])]
                for r in sorted(eco, key=lambda r: (r["year"] or 0, r["country"] or "", r["building"] or ""))]
        h.append(fb.tbl(["Year", "Country", "State", "Building", "Type", "Levels"],
                        rows, cfilter="1"))
    else:
        h.append("<p class='muted small'>No eco placements in log (run game with debug_log).</p>")
    h.append("</div>")

    # Grouped table (country+year+building rollup)
    h.append("<div id='eco-grouped' style='display:none'>")
    h.append(f"<p class='small'>Grouped view — by country + year + building. "
             f"{fb.badge('grey', str(len(aggr)) + ' rows')}</p>")
    if aggr:
        rows2 = [[str(r["year"] or "?"), r["country"] or "?",
                  r["building"] or "?", r.get("type", "?"), str(r["count"])]
                 for r in aggr]
        h.append(fb.tbl(["Year", "Country", "Building", "Type", "Total Levels"],
                        rows2, cfilter="1"))
    h.append("</div>")

    # Toggle button (injected before the tables)
    toggle_js = (
        "<div style='margin:6px 0'>"
        "<button class='pbtn' onclick=\""
        "var d=document.getElementById('eco-detail'),"
        "g=document.getElementById('eco-grouped'),"
        "b=this;"
        "if(d.style.display==='none'){d.style.display='';g.style.display='none';b.textContent='Switch to Grouped';}"
        "else{d.style.display='none';g.style.display='';b.textContent='Switch to Detail';}"
        "\">Switch to Grouped</button></div>"
    )
    h.insert(1, toggle_js)

    summary = {"placements": total, "rows": len(eco)}
    fb.write_data(feature_dir, "data_eco.json",  data)
    fb.write_data(feature_dir, "aggr_eco.json",  {"eco": aggr})
    fb.write_component(feature_dir, mod, "ECO-YEARLY", "timeline", "Eco placements (by year)", 0,
                       "\n".join(h), summary=summary)
    print(f"  [ECO-YEARLY] {mod}: {total} placements, {len(eco)} rows")


if __name__ == "__main__":
    run()
