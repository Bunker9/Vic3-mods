#!/usr/bin/env python3
r"""run_save_parser.py — MASTER orchestrator for the per-mod save-game fingerprint parser.

Thin driver. Reads the mod's join keys from tools/<MOD_NAME>/list_kw.csv (owned by the triage job),
scans the newest (or --save) Victoria 3 save for the mod's persisted variables / modifiers and its
deliberate <abbr>_fingerprint_* markers, and writes the per-mod CSV + diagnostics into
tools/save-game-parser/<MOD_NAME>/.

Pipeline:  aggr_save_matches (1) -> anal_save_report (2)

Args (see lib_saveparse):
  arg1  MOD_NAME   (required)   output namespace tools/save-game-parser/<MOD_NAME>/
  --save PATH                   override the save file (.v3); else newest in the 'save games' dir
  --prefix P                    override the auto-derived mod abbreviation
  --rerun                       force re-scan (else reuse matched CSV if present)

Examples:
  python run_save_parser.py NoUSChickenMod
  python run_save_parser.py NoUSChickenMod --save "C:\...\save games\autosave.v3" --rerun
"""
import lib_saveparse as L
import aggr_save_matches, ext_save_blocks, aggr_state_census, anal_save_report


def main(args):
    L.out_dir(args.mod_name)
    have = L.read_csv(L.out_path(args.mod_name, "matched_savefile_loglines.csv"))[0] is not None
    have_raw = L.read_csv(L.out_path(args.mod_name, "raw_buildings.csv"))[0] is not None
    do_scan = args.rerun or not have or not have_raw

    print(f"== save-parse {args.mod_name} ==  (scan: {'RUN' if do_scan else 'reuse'})")
    if do_scan:
        aggr_save_matches.main(args)     # 1  : mod-token / fingerprint findings
        ext_save_blocks.main(args)       # 1a : raw per-manager extracts (buildings/states/countries)
    aggr_state_census.main(args)         # 1b : join raw_* -> state/building census + overbuild view
    anal_save_report.main(args)          # 2  : diagnostics
    print(f"== done -> {L.out_dir(args.mod_name, create=False)} ==")


if __name__ == "__main__":
    main(L.parse_args("Run the full per-mod save-game fingerprint parser (master)."))
