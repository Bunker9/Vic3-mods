# RESUME — "THE framework" ironing (save-parser + log-triage)

> **Session handoff, 2026-06-26 EOD. HIGH PRIORITY — resume here next session (fresh limits).**
> Co-located with the code. Authoritative narrative: hk-config `docs/PROGRESS.md` (2026-06-26 EOD entry,
> read at every hello). Design/vision home: hk-config `roadmap/MOD-DEBUG-FRAMEWORK.md`.
> Governing rule: DEV-RULES "THE debugging framework"; memory `the-debug-framework`.

## What this task is
Perfect — modularize + reuse + consistent docs/nomenclature — EVERY sub-script of the two debugging jobs so
they become THE framework for all future mod debugging. Later, v2 reports present analysis HTML components
(UI plug-and-play) addable to report tabs for unit-test reporting; they consume the jobs' diagnostics.md/CSVs.

## The two jobs (the substrate)
- **log-triage** — this folder (`testbook/v2/tools/`): `run_log_triage.py` + `lib_triage.py` +
  `ext_mod_files/keywords/debuglines/loc` → `aggr_log_matches` → `anal_log_triage`; shared `benign.csv`.
- **save-game-parser** — `save-game-parser/`: `run_save_parser.py` + `lib_saveparse.py` + `ext_save_blocks`
  (raw) + `aggr_save_matches` + `aggr_state_census` → `anal_save_report`. Reads triage's `list_kw.csv`.

## Seams to iron (refine against the user's pasted vision)
1. Two `lib_*` (`lib_triage`/`lib_saveparse`) duplicate primitives (args/paths/CSV IO/prefix detect/benign)
   → ONE shared core lib.
2. Stage-numbering diverges (log-triage 1–5 vs save-parser 1a/1/1b/2); class prefixes already consistent →
   unify the stage model & vocabulary.
3. Cross-job `list_kw.csv` dependency is implicit → make it an explicit shared contract / single source.
4. Both emit `diagnostics.md` → design the plug-and-play HTML-component output contract HERE, not per-job.
5. Raw extractors stay generic/mod-agnostic, no probe-tag hardcoding (gameplay-followups #5 / TODO T101).

## DO FIRST next session
1. Read PROGRESS 2026-06-26 EOD + `roadmap/MOD-DEBUG-FRAMEWORK.md`.
2. **WAIT for the user's vision paste** in MOD-DEBUG-FRAMEWORK.md "## Vision (user)" before editing scripts.
3. Then iron against it (shared lib → unified stages → HTML-component contract). EXTEND the framework; per
   the governing rule, do NOT write one-off debug scripts.
