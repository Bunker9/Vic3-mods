#!/usr/bin/env python3
"""aggr-state-census.py — SaveParse aggregator: JOIN the raw_* extracts (+ the variable findings) into the
state/building census + overbuild view. Reads ONLY the CSVs (never the save). Bridges building.state ->
states.country -> countries.definition (owner tag). The cap variable is matched by a CONFIG-DRIVEN PATTERN
(mod-agnostic; replaces the hardcoded zw_mfg_cap, T101). Ported from save-game-parser/aggr_state_census.py.
Cohesive aggregator (exceeds the 50-line glue target by design)."""
import os
import re
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
MFG = set(CFG["census"]["manufacturing_capped"])
TRIG = set(CFG["census"]["trigger_capped"])
CAPPED = MFG | TRIG
CAP_RX = re.compile(CFG["census"]["cap_var_pattern"])


def _load(d, name):
    h, r = lib_io.read_csv(os.path.join(d, name))
    return (r, {c: i for i, c in enumerate(h)}) if h else ([], {})


def main(args):
    d = lib_paths.run_dir("save-CURR", args.mod_name)
    builds, bi = _load(d, "raw_buildings.csv")
    states, si = _load(d, "raw_states.csv")
    countries, ci = _load(d, "raw_countries.csv")
    if not builds:
        print("  aggr-state-census: no raw_buildings.csv — run ext-save-blocks first.")
        return
    state_country = {r[si["id"]]: r[si["country"]] for r in states} if states else {}
    state_region = {r[si["id"]]: r[si["region"]] for r in states} if states and "region" in si else {}
    country_tag = {}
    for r in countries:
        country_tag[r[ci["id"]]] = (r[ci.get("definition", -1)] or r[ci.get("tag", -1)] or "").strip()

    def owner(sid):
        cid = state_country.get(sid, "")
        return cid, country_tag.get(cid, "")

    regions, ri = _load(d, "raw_state_regions.csv")
    srid_template = {r[ri["id"]]: (r[ri["template"]] if "template" in ri else "") for r in regions}
    found, fi = _load(d, CFG["outputs"]["matches"])
    template_cap = {}
    for r in found:                                   # GENERIC cap-var (T101): any *_cap on a state_region
        if fi and CAP_RX.search(r[fi["fp"]]):
            m = re.search(r"database\.(-?\d+)", r[fi["doc_path"]])
            if m and m.group(1) in srid_template:
                template_cap[srid_template[m.group(1)]] = r[fi["value"]]

    census, over = [], []
    for r in builds:
        sid, bld, lvl = r[bi["state"]], r[bi["building"]], (r[bi["levels"]] or "0")
        cid, tag = owner(sid)
        region = state_region.get(sid, "")
        subs = r[bi['subsidized']] if 'subsidized' in bi else ''
        detail = (f"active={r[bi['active']] if 'active' in bi else ''};subsidized={subs};"
                  f"est={r[bi['establishment_date']] if 'establishment_date' in bi else ''}")
        census.append([cid, tag, sid, region, "building", bld, lvl, "building", detail])
        if bld in CAPPED:
            try:
                lv = int(lvl)
            except ValueError:
                lv = 0
            cap = template_cap.get(region, "")
            if bld in TRIG:
                verdict = "NO_STORED_CAP(trigger-gated)"
            elif cap == "":
                verdict = "SCRIPT_ERROR_no_cap_var"
            else:
                try:
                    capi = int(round(float(cap)))
                except ValueError:
                    capi = -1
                verdict = ("SCRIPT_ERROR_zero_cap" if capi <= 0 else
                           (f"OVER_BY_{lv - capi}_ENGINE_OVERBUILD" if lv > capi else "ok"))
            over.append([tag, cid, sid, region, bld, lv, cap, verdict, "yes" if subs == "yes" else "no"])

    for r in found:
        if fi and r[fi["fp_type"]] in ("variable", "global_variable"):
            dp = r[fi["doc_path"]]
            if "states.database" in dp or "state_region_manager" in dp:
                m = re.search(r"database\.(-?\d+)", dp)
                sid = m.group(1) if m else ""
                cid, tag = owner(sid)
                census.append([cid, tag, sid, "", "state_variable", r[fi["fp"]],
                               r[fi["value"]], r[fi["vtype"]], dp])

    lib_io.write_csv(os.path.join(d, CFG["outputs"]["census"]),
                     ["country_id", "owner_tag", "state_id", "state_region", "kind", "name",
                      "value", "vtype", "detail"], census)
    over.sort(key=lambda x: -x[5])
    lib_io.write_csv(os.path.join(d, CFG["outputs"]["overbuild"]),
                     ["owner_tag", "country_id", "state_id", "region", "building", "level",
                      "cap", "verdict", "subsidized"], over)
    print(f"  -> {CFG['outputs']['census']}: {len(census)} rows · "
          f"{CFG['outputs']['overbuild']}: {len(over)} capped rows")
    return census


if __name__ == "__main__":
    main(lib_args.parse_args("SaveParse: join raw_* into the state/building census.", save=True))
