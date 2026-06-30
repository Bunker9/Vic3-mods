# Framework-SaveParse — script manifest

> One row per script/artifact. **STUB skeleton created 2026-06-30; Phase 4 not yet implemented.** Code files
> are hyphen-named, import `../Framework-common`; the master runs the subs as SUBPROCESSES. Migrates the old
> `save-game-parser/*`. The old `save-game-parser/` dir is retired once this is built.

| file | class | lines | purpose | status |
|---|---|---|---|---|
| `run-saveparse.py` | run- (orchestrator) | ≤50 | resolve save → `ext-save-blocks` → `aggr-save-matches` + `aggr-state-census` → `anal-save-report` (subprocess) | built |
| `ext-save-blocks.py` | ext- (raw extractor) | ≤50 | one pass → `raw_buildings/states/countries/state_regions.csv` (MOD-AGNOSTIC, T101) | built |
| `aggr-save-matches.py` | aggr- | ≤50 | persisted mod-token / fingerprint occurrences → `aggr_save_matches.csv` | built |
| `aggr-state-census.py` | aggr- | cohesive (may exceed 50) | join raw_* → owner tag → `aggr_state_census.csv` + `aggr_census_overbuild.csv` (GENERIC cap-var pattern, kills `zw_mfg_cap`/T101) | built |
| `anal-save-report.py` | anal- | cohesive (may exceed 50) | fingerprints persisted/absent + over-cap classify → `diagnostics.md` | built |
| `config_saveparse.toml` | config (data) | n/a | manager targets+columns, ÷100000 factor, cap-var pattern, capped-building catalog, verdicts | built |
| `README.md` | doc | n/a | framework contract | done |
