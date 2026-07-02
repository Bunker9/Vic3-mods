#!/usr/bin/env python3
"""aggr-save-census.py — SaveParse Set-1 aggregator (MOD-AGNOSTIC, parse-once): the ENRICH join over the raw
extracts (UAT SP-02: raw IDs from ext-save-blocks, names/links joined here — never re-reads the save).
Bridges building.state -> states.country -> countries.definition (owner tag) + countries.market +
states.region -> state_regions.template -> COMMON save-CURR/raw_state_census.csv, one row per building.
Per-mod cap/overbuild classification is Set-2 (aggr-save-overbuild). Standalone; run-save-parse invokes."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")


def _load(name):
    h, r = lib_io.read_csv(os.path.join(ROOT, name))
    return (r, {c: i for i, c in enumerate(h)}) if h else ([], {})


def main():
    builds, bi = _load("raw_buildings.csv")
    states, si = _load("raw_states.csv")
    countries, ci = _load("raw_countries.csv")
    regions, ri = _load("raw_state_regions.csv")
    if not builds:
        sys.exit("aggr-save-census: no raw_buildings.csv — run ext-save-blocks first (run-save-parse).")
    state_country = {r[si["id"]]: r[si["country"]] for r in states}
    # states.region holds the state-region TEMPLATE NAME (e.g. STATE_MINSK), NOT a numeric id — verified on
    # TEST_ME.v3 2026-07-02. Cap vars live on state_region_manager.database.<srid>; the srid->template map
    # (raw_state_regions) bridges them to these names in aggr-save-overbuild.
    state_template = {r[si["id"]]: r[si["region"]] for r in states} if "region" in si else {}
    country_tag = {r[ci["id"]]: (r[ci.get("definition", -1)] or r[ci.get("tag", -1)] or "").strip()
                   for r in countries}
    country_market = {r[ci["id"]]: r[ci["market"]] for r in countries} if "market" in ci else {}
    census = []
    for r in builds:
        sid, bld, lvl = r[bi["state"]], r[bi["building"]], (r[bi["levels"]] or "0")
        cid = state_country.get(sid, "")
        census.append([cid, country_tag.get(cid, ""), country_market.get(cid, ""), sid,
                       state_template.get(sid, ""), bld, lvl,
                       r[bi["active"]] if "active" in bi else "",
                       r[bi["subsidized"]] if "subsidized" in bi else "",
                       r[bi["establishment_date"]] if "establishment_date" in bi else ""])
    out = os.path.join(ROOT, CFG["outputs"]["census"])
    lib_io.write_csv(out, ["country_id", "owner_tag", "owner_market", "state_id", "state_region",
                           "building", "levels", "active", "subsidized", "establishment_date"], census)
    print(f"  -> {CFG['outputs']['census']}: {len(census)} building rows (owner/market/region enriched)")


if __name__ == "__main__":
    main()
