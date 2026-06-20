#!/usr/bin/env python3
"""
Feature MDP-BLOB (MyDiploPlayMod) — runtime blob-chain on the Timeline tab: wars started +
claims/homelands granted per year (from the shared `timeline` analyzer).
Writes data_diplo.json + component.html.
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
    wars   = data.get("wars", [])
    dcounts = data.get("diplo_counts", [])

    h = []
    h.append(f"<p>{fb.badge('grey', str(len(wars)) + ' wars')} "
             f"{fb.badge('grey', str(len(dcounts)) + ' diplo grant rows')}</p>")

    # Wars table
    h.append(f"<h4 style='margin:8px 0 4px'>Wars started "
             f"{fb.badge('grey', str(len(wars)))}</h4>")
    if wars:
        rows = [[str(w["year"] or "?"), w["attacker"] or "?", w["target"] or "?"]
                for w in sorted(wars, key=lambda w: (w["year"] or 0, w["attacker"] or ""))]
        h.append(fb.tbl(["Year", "Attacker", "Target"], rows, cfilter="1,2"))
    else:
        h.append("<p class='muted small'>No runtime wars in log (history wars not shown here).</p>")

    # Claims / homelands table
    h.append(f"<h4 style='margin:12px 0 4px'>Claims / homelands granted "
             f"{fb.badge('grey', str(len(dcounts)))}</h4>")
    if dcounts:
        # Pops column dropped (v2-harden item e): MDP_POP is legacy, removed from the mod,
        # so the column was always 0 and just added noise.
        rows2 = [[str(r["year"] or "?"), r["country"] or "?",
                  str(r["claims"]), str(r["homelands"])]
                 for r in sorted(dcounts, key=lambda r: (r["year"] or 0, r["country"] or ""))]
        h.append(fb.tbl(["Year", "Country", "Claims", "Homelands"],
                        rows2, cfilter="1"))
    else:
        h.append("<p class='muted small'>No MDP_CLAIM / MDP_HOMELAND markers in log.</p>")

    summary = {"wars": len(wars), "diplo_rows": len(dcounts)}
    fb.write_data(feature_dir, "data_diplo.json", data)
    fb.write_component(feature_dir, mod, "MDP-BLOB", "timeline", "Runtime blob chain (wars/claims)", 0,
                       "\n".join(h), summary=summary)
    print(f"  [MDP-BLOB] {mod}: {len(wars)} wars, {len(dcounts)} diplo rows")


if __name__ == "__main__":
    run()
