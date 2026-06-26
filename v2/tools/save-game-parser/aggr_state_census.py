#!/usr/bin/env python3
r"""aggr_state_census.py — stage 1b: JOIN the raw_* extracts into the state/building census.

Reads ONLY the raw_*.csv from ext_save_blocks (+ the variable findings from aggr_save_matches) — never
the save. Bridges building.state -> states.country -> countries.definition (owner tag) and emits:
  state_census.csv     tidy/long: country_id, owner_tag, state_id, state_region, kind, name, value, vtype, detail
  census_overbuild.csv the capped building types (railway/power_plant/art_academy/manufacturing), one row
                       per (owner_tag,state,building) sorted by level desc — the actionable overbuild view.
"""
import os, re, csv
import lib_saveparse as L

# manufacturing buildings governed by the mod's stored numeric cap zw_mfg_cap (per state_region)
MFG_CAPPED = {"building_steel_mills", "building_tooling_workshops", "building_textile_mills",
              "building_furniture_manufacturies", "building_glassworks", "building_paper_mills",
              "building_chemical_plants", "building_motor_industry", "building_arms_industry",
              "building_munition_plants", "building_explosives_factory", "building_synthetics_plants",
              "building_electrics_industry", "building_food_industry", "building_shipyards",
              "building_military_shipyards"}
# trigger/script-value gated (no stored numeric cap to compare against)
TRIGGER_CAPPED = {"building_railway", "building_power_plant", "building_art_academy"}
CAPPED = MFG_CAPPED | TRIGGER_CAPPED


def _load(mod, name):
    h, r = L.read_csv(L.out_path(mod, name))
    if h is None:
        return [], {}
    idx = {c: i for i, c in enumerate(h)}
    return r, idx


def _decode(value, vtype):
    if vtype == "value" and re.fullmatch(r"-?\d+", value or ""):
        d = int(value) / 100000
        return str(int(d)) if d == int(d) else f"{d:.5f}".rstrip("0").rstrip(".")
    return value


def main(args):
    mod = args.mod_name
    builds, bi = _load(mod, "raw_buildings.csv")
    states, si = _load(mod, "raw_states.csv")
    countries, ci = _load(mod, "raw_countries.csv")
    if not builds:
        print("  aggr_state_census: no raw_buildings.csv — run ext_save_blocks first."); return

    state_country = {r[si["id"]]: r[si["country"]] for r in states} if states else {}
    state_region  = {r[si["id"]]: r[si["region"]] for r in states} if states and "region" in si else {}
    country_tag = {}
    for r in countries:
        tag = (r[ci.get("definition", -1)] or r[ci.get("tag", -1)] or "").strip()
        country_tag[r[ci["id"]]] = tag

    def owner(state_id):
        cid = state_country.get(state_id, "")
        return cid, country_tag.get(cid, "")

    # region NAME (template) -> mod manufacturing cap (zw_mfg_cap, stored per state_region):
    #   srid -> template (raw_state_regions)  joined with  srid -> zw_mfg_cap (var findings, doc_path srid)
    regions, ri = _load(mod, "raw_state_regions.csv")
    srid_template = {r[ri["id"]]: (r[ri["template"]] if "template" in ri else "") for r in regions}
    found, fi = _load(mod, "matched_savefile_loglines.csv")
    template_cap = {}
    for r in found:
        if fi and r[fi["fp"]] == "zw_mfg_cap":
            m = re.search(r"database\.(-?\d+)", r[fi["doc_path"]])
            if m and m.group(1) in srid_template:
                template_cap[srid_template[m.group(1)]] = r[fi["value"]]

    # --- census rows (buildings) + overbuild classification against the cap ---
    census = []
    over = []
    for r in builds:
        sid = r[bi["state"]]
        bld = r[bi["building"]]
        lvl = r[bi["levels"]] or "0"
        cid, tag = owner(sid)
        region = state_region.get(sid, "")
        subs = r[bi['subsidized']] if 'subsidized' in bi else ''
        detail = f"active={r[bi['active']] if 'active' in bi else ''};subsidized={subs};est={r[bi['establishment_date']] if 'establishment_date' in bi else ''}"
        census.append([cid, tag, sid, region, "building", bld, lvl, "building", detail])
        if bld in CAPPED:
            try:
                lv = int(lvl)
            except ValueError:
                lv = 0
            cap = template_cap.get(region, "")
            if bld in TRIGGER_CAPPED:
                verdict = "NO_STORED_CAP(trigger-gated)"
            elif cap == "":
                verdict = "SCRIPT_ERROR_no_cap_var"
            else:
                try:
                    capi = int(round(float(cap)))
                except ValueError:
                    capi = -1
                if capi <= 0:
                    verdict = "SCRIPT_ERROR_zero_cap"
                elif lv > capi:
                    verdict = f"OVER_BY_{lv - capi}_ENGINE_OVERBUILD"
                else:
                    verdict = "ok"
            over.append([tag, cid, sid, region, bld, lv, cap, verdict,
                         "yes" if subs == "yes" else "no"])

    # --- census rows (state / state-region variables from the findings) ---
    for r in found:
        if fi and r[fi["fp_type"]] in ("variable", "global_variable"):
            dp = r[fi["doc_path"]]
            if "states.database" in dp or "state_region_manager" in dp:
                m = re.search(r"database\.(-?\d+)", dp)
                sid = m.group(1) if m else ""
                cid, tag = owner(sid)
                census.append([cid, tag, sid, "", "state_variable", r[fi["fp"]],
                               r[fi["value"]], r[fi["vtype"]], dp])

    L.write_csv(L.out_path(mod, "state_census.csv"),
                ["country_id", "owner_tag", "state_id", "state_region", "kind", "name", "value", "vtype", "detail"],
                census)
    over.sort(key=lambda x: -x[5])
    L.write_csv(L.out_path(mod, "census_overbuild.csv"),
                ["owner_tag", "country_id", "state_id", "region", "building", "level", "cap", "verdict", "subsidized"], over)
    print(f"  -> state_census.csv: {len(census)} rows ({len(builds)} buildings + state vars)")
    print(f"  -> census_overbuild.csv: {len(over)} capped-building rows (top level={over[0][4] if over else 0})")
    return census


if __name__ == "__main__":
    main(L.parse_args("Join raw_* extracts into the state/building census (stage 1b)."))
