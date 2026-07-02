#!/usr/bin/env python3
"""aggr-save-overbuild.py — SaveParse Set-2 aggregator: per-mod over-cap classification (T101 logic PORTED
from the retired aggr-state-census, not rewritten) + the per-mod metrics.csv the Set-3 engine evaluates.
Reads the COMMON save-CURR/raw_state_census.csv + this mod's aggr_save_matches.csv (cap vars matched by the
config-driven pattern on state_regions) + data-<Mod>/raw_keywords.csv (absent-token analysis) ->
save-CURR/<Mod>/aggr_census_overbuild.csv + metrics.csv. Cohesive aggregator (may exceed the 50-line glue
target). Standalone; run-save-aggr invokes it."""
import os
import re
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
MFG, TRIG = set(CFG["census"]["manufacturing_capped"]), set(CFG["census"]["trigger_capped"])
CAP_RX = re.compile(CFG["census"]["cap_var_pattern"])
NONPERSIST = re.compile(CFG["analysis"]["nonpersist_pattern"])
INFIX = CFG["markers"]["fingerprint_infix"]
ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")


def _load(path, hint):
    h, r = lib_io.read_csv(path)
    if h is None:
        sys.exit(f"aggr-save-overbuild: missing {os.path.basename(path)} — {hint}")
    return r, {c: i for i, c in enumerate(h)}


def main(args):
    out_dir = lib_paths.run_dir("save-CURR", args.mod_name)
    census, xi = _load(os.path.join(ROOT, CFG["outputs"]["census"]), "run run-save-parse first (Set 1)")
    found, fi = _load(os.path.join(out_dir, CFG["outputs"]["matches"]), "run aggr-save-matches first (Set 2)")
    regions, ri = _load(os.path.join(ROOT, "raw_state_regions.csv"), "run run-save-parse first (Set 1)")
    srid_template = {r[ri["id"]]: r[ri["template"]] for r in regions}
    template_cap = {}          # GENERIC cap-var (T101): any *_cap on a state_region, keyed by TEMPLATE name
    for r in found:            # (census.state_region holds the template name; srid_template bridges the ids)
        if CAP_RX.search(r[fi["fp"]]) and "state_region_manager" in r[fi["doc_path"]]:
            m = re.search(r"database\.(-?\d+)", r[fi["doc_path"]])
            if m and m.group(1) in srid_template:
                template_cap[srid_template[m.group(1)]] = r[fi["value"]]
    over, problems = [], 0
    for r in census:
        bld = r[xi["building"]]
        if bld not in MFG and bld not in TRIG:
            continue
        try:
            lv = int(r[xi["levels"]] or "0")
        except ValueError:
            lv = 0
        cap = template_cap.get(r[xi["state_region"]], "")
        if bld in TRIG:
            verdict = "NO_STORED_CAP(trigger-gated)"
        elif not template_cap:
            verdict = "NO_CAP_SYSTEM(mod defines no cap vars)"   # not an error: this mod has no cap feature
        elif cap == "":
            verdict = "SCRIPT_ERROR_no_cap_var"
        else:
            try:
                capi = int(round(float(cap)))
            except ValueError:
                capi = -1
            verdict = ("SCRIPT_ERROR_zero_cap" if capi <= 0 else
                       (f"OVER_BY_{lv - capi}_ENGINE_OVERBUILD" if lv > capi else "ok"))
        problems += verdict not in ("ok", "NO_STORED_CAP(trigger-gated)",
                                    "NO_CAP_SYSTEM(mod defines no cap vars)")
        over.append([r[xi["owner_tag"]], r[xi["country_id"]], r[xi["state_id"]], r[xi["state_region"]],
                     bld, lv, cap, verdict, "yes" if r[xi["subsidized"]] == "yes" else "no"])
    over.sort(key=lambda x: -x[5])
    lib_io.write_csv(os.path.join(out_dir, CFG["outputs"]["overbuild"]),
                     ["owner_tag", "country_id", "state_id", "region", "building", "level",
                      "cap", "verdict", "subsidized"], over)
    data = lib_paths.data_dir(args.mod_name, create=False)
    _h, kwrows = lib_io.read_csv(os.path.join(data, "raw_keywords.csv"))
    persisted = {r[fi["fp"]] for r in found}
    kws = [r[1] for r in (kwrows or [])]
    absent_suspect = [k for k in kws if k not in persisted and not NONPERSIST.search(k)]
    fps = {t for t in persisted if INFIX in t}
    metrics = [["fingerprints", len(fps)],
               ["persisted_occurrences", len(found)],
               ["persisted_other", len(persisted - fps)],
               ["kw_absent_suspect", len(absent_suspect)],
               ["capped_rows", len(over)],
               ["overbuild_rows", problems]]
    lib_io.write_csv(os.path.join(out_dir, CFG["outputs"]["metrics"]), ["metric", "value"], metrics)
    print(f"  [overbuild] {len(over)} capped rows ({problems} problem verdicts); "
          f"fp={len(fps)} absent-suspect={len(absent_suspect)} -> metrics.csv")


if __name__ == "__main__":
    main(lib_args.parse_args("SaveParse Set2: per-mod over-cap classify + metrics."))
