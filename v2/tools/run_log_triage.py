#!/usr/bin/env python3
r"""
run_log_triage.py — MASTER orchestrator for the generic per-mod log-triage job.

Thin driver: builds (or reuses) the mod's key lists, joins them against the game logs, and analyses
the result into diagnostics. The work lives in the single-purpose sub-scripts (each independently
runnable); this just sequences them and owns the reuse/rerun decision.

Pipeline:
  ext_mod_files (1) -> ext_mod_keywords (2) -> ext_mod_debuglines (3) -> ext_mod_loc (3b)
  -> aggr_log_matches (4) -> anal_log_triage (5)

Standardized args (see lib_triage):
  arg1  MOD_NAME   (required)  — output namespace testbook/v2/tools/<MOD_NAME>/
  arg2  MOD_PATH   (optional)  — mod source folder; required only to (re)build lists
  --rerun                      — force-rebuild lists (else reuse-if-present, build-if-missing)
  --prefix P / --logs DIR      — overrides

Examples:
  python run_log_triage.py NoUSChickenMod "C:\...\mod1-inov\NoUSChickenMod" --rerun
  python run_log_triage.py NoUSChickenMod          # regression rerun: reuse lists, refresh scan
"""
import lib_triage as L
import ext_mod_files, ext_mod_keywords, ext_mod_debuglines, ext_mod_loc
import aggr_log_matches, anal_log_triage

LISTS = ["list_files.csv", "list_kw.csv", "list_debug_lines.csv", "list_loc.csv"]


def main(args):
    L.tools_dir(args.mod_name)   # ensure output dir exists
    have_all = all(L.read_csv(L.out_path(args.mod_name, f))[0] is not None for f in LISTS)
    build = args.rerun or not have_all

    print(f"== triage {args.mod_name} ==  (lists: {'BUILD' if build else 'reuse'})")
    if build:
        if not args.mod_path:
            raise SystemExit(
                "run_log_triage: lists missing or --rerun set, but no MOD_PATH (arg2) given.\n"
                "  Pass the mod folder to (re)build the lists, e.g.:\n"
                f'    python run_log_triage.py {args.mod_name} "<path-to-mod>" --rerun')
        ext_mod_files.main(args)
        ext_mod_keywords.main(args)
        ext_mod_debuglines.main(args)
        ext_mod_loc.main(args)

    aggr_log_matches.main(args)
    anal_log_triage.main(args)
    print(f"== done -> {L.tools_dir(args.mod_name, create=False)} ==")


if __name__ == "__main__":
    main(L.parse_args("Run the full per-mod log-triage pipeline (master)."))
