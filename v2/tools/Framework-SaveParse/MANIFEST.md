# Framework-SaveParse — script manifest

> One row per script/artifact. **BUILT (Phase 4, 2026-06-30; validated on a melted save).** Code files are
> hyphen-named, import `../Framework-common`; the master runs the subs as SUBPROCESSES. Replaced the original
> save-game-parser job (retired 2026-07-01).

| file | class | lines | purpose | status |
|---|---|---|---|---|
| `run-saveparse.py` | run- (orchestrator) | ≤50 | resolve save → `ext-save-blocks` → `aggr-save-matches` + `aggr-state-census` → `anal-save-report` (subprocess) | built |
| `ext-save-blocks.py` | ext- (raw extractor) | ≤50 | one pass → `raw_buildings/states/countries/state_regions.csv` (MOD-AGNOSTIC, T101) | built |
| `aggr-save-matches.py` | aggr- | ≤50 | persisted mod-token / fingerprint occurrences → `aggr_save_matches.csv` | built |
| `aggr-state-census.py` | aggr- | cohesive (may exceed 50) | join raw_* → owner tag → `aggr_state_census.csv` + `aggr_census_overbuild.csv` (GENERIC cap-var pattern, kills `zw_mfg_cap`/T101) | built |
| `anal-save-report.py` | anal- | cohesive (may exceed 50) | fingerprints persisted/absent + over-cap classify → `diagnostics.md` | built |
| `config_saveparse.toml` | config (data) | n/a | manager targets+columns, ÷100000 factor, cap-var pattern, capped-building catalog, verdicts | built |
| `README.md` | doc | n/a | framework contract | done |

## Rework additions — registered 2026-07-02 (parse-once split; stubs pending build phase)
> Design: `hk-config/roadmap/ROADMAP-debug-framework-rework.md` §SaveParse. UAT directives: the raw extract
> stays ID-only and a SEPARATE enrich script joins IDs→names via lookup lists (SP-02); per-market goods
> prices = TODO T103. The old per-mod pipeline rows above RETIRE when the split lands (port the proven T101
> cap logic from `aggr-state-census`, don't rewrite it).

| file | class | purpose | status |
|---|---|---|---|
| `run-save-parse.py` | run- (Set1 master) | parse save ONCE → COMMON raws at `save-CURR/` ROOT; skip-if-present/`--rerun` | STUB |
| `aggr-save-census.py` | aggr- | COMMON raws → `save-CURR/raw_state_census.csv` (mod-agnostic census) | STUB |
| `run-save-aggr.py` | run- (Set2 master) | per mod: COMMON raws + `data-<Mod>` → `save-CURR/<Mod>/aggr_*` | STUB |
| `aggr-save-overbuild.py` | aggr- | per-mod over-cap classify (generic cap pattern, T101 port) | STUB |
| `run-save-diag.py` | run- (Set3 master) | save diagnostics via the (literals-parameterized) diag engine | STUB |
| `diag_literals.example.csv` | literal (tracked seed) | save-side diagnostics rules | built (seeded) |
