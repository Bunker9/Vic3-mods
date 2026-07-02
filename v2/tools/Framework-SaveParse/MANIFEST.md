# Framework-SaveParse — script manifest

> One row per script/artifact. **REWORKED (parse-once Sets 1-3, completed 2026-07-02; incl. the T103
> market/goods extraction).** Code files are hyphen-named, import `../Framework-common`; masters run their
> stages as SUBPROCESSES. The pre-rework per-mod pipeline (`aggr-state-census.py` + `anal-save-report.py`)
> was RETIRED 2026-07-02 (its T101 cap logic PORTED into `aggr-save-overbuild`). Set-3 reuses the SHARED
> diagnostics engine in `Framework-Logtriage` (`--kind save-CURR`) over `Framework-common/lib_diag`.
> Design home: `hk-config/roadmap/ROADMAP-debug-framework-rework.md`.

| file | class | lines | purpose | status |
|---|---|---|---|---|
| `run-saveparse.py` | run- (TOP master) | ≤50 | Set1 → Set2 → Set3; mods positional / `--all`; `--save --prefix --rerun` | built 07-02 |
| `run-save-parse.py` | run- (Set1 master) | ≤50 | archive prior `save-CURR*` ONCE + parse ONCE → COMMON pool; reuse-if-present / `--rerun` | built 07-02 |
| `ext-save-blocks.py` | ext- | ≤60 | one pass → `raw_<mgr>.csv` per configured manager (incl. `pops`; RAW IDs, mod-agnostic, T101) | built (retargeted to ROOT 07-02) |
| `ext-save-flags.py` | ext- | ≤40 | one pass → `raw_flags.csv`: EVERY persisted var/modifier, no mod filter (SORT-not-FILTER) | built 07-02 |
| `ext-save-goods.py` | ext- | ≤55 | market_manager `price_trend` channels → `raw_market_goods.csv` (market × goods: current/min/max price) — T103 | built 07-02 |
| `ext-goods-catalog.py` | ext- | ≤50 | goods id→name catalog from `game_files_path` goods files (definition order); tracked-seed fallback → `goods_ids.csv` | built 07-02 |
| `aggr-save-census.py` | aggr- | ≤55 | the ENRICH join (UAT SP-02): raws → `raw_state_census.csv` (owner tag/market/region template) | built 07-02 (mod-agnostic) |
| `run-save-aggr.py` | run- (Set2 master) | ≤30 | per mod: `aggr-save-matches` + `aggr-save-overbuild` (subprocess) | built 07-02 |
| `aggr-save-matches.py` | aggr- | ≤60 | filter the COMMON `raw_flags` pool to the mod's kw + `*_fingerprint_*`; decode values → `aggr_save_matches.csv` | built 07-02 (refocused; never re-reads the save) |
| `aggr-save-overbuild.py` | aggr- | cohesive | T101 cap verdicts (ported) → `aggr_census_overbuild.csv` + per-mod `metrics.csv` (fp / persisted / absent-suspect / overbuild) | built 07-02 |
| `run-save-diag.py` | run- (Set3 master) | ≤45 | seed `diag_literals.csv` → ROOT; per mod call the SHARED engine with `--kind save-CURR` | built 07-02 |
| `config_saveparse.toml` | config (data) | n/a | managers(+pops), decode factor, cap pattern + catalogs, nonpersist pattern, goods/market keys, diag seeds, output names | built |
| `diag_literals.example.csv` | literal (tracked seed) | n/a | save-side diagnostics rules → loaded to `save-CURR/diag_literals.csv` | built (seeded) |
| `goods_ids.example.csv` | literal (tracked seed) | n/a | goods id→name fallback catalog (used only when `game_files_path` is blank) | built (empty template) |
| `README.md` | doc | n/a | framework contract (usage) | done |
