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
| `ext-save-battles.py` | ext- | cohesive | `battle_manager` + `naval_battle_manager` → `raw_battles.csv`. EVERY battle emits a row (`row_kind=battle`) whether or not it carries a statistics array, plus one row per per-culture casualty entry; battle-level attacker/defender manpower + battalions ride on every row, the save's only DATED manpower-loss record. SORT-not-FILTER: an earlier cut required a full num_dead/wounded/demoralized triple and silently dropped 25 of 40 battles | built 08-16 (mod-agnostic) |
| `ext-save-stateall.py` | ext- | cohesive | EVERYTHING belonging to ONE state, from EVERY manager, every field verbatim → `raw_state<ID>_all.csv` + `raw_state<ID>_index.csv`. Two passes: index records matching `state=`/`location=`/`region=`/`home_hq=`/`capital=`/the state record itself (keeping WHY it matched), then dump every key=value incl. nested blocks. No manager list, no field list — deciding what matters happens after the dump | built 08-16 (mod-agnostic) |
| *(goods catalog)* | literal seed | n/a | `goods_ids.example.csv` is seeded → `save-CURR/goods_ids.csv` by `run-save-parse` STEP 2; GENERATED offline by `hk-config/tools/testbook_lookup_generators/anal-goods-ids.py` + hand-curated (frameworks never read base game files — user rule 2026-07-02) | seed pattern |
| `aggr-save-census.py` | aggr- | ≤55 | the ENRICH join (UAT SP-02): raws → `raw_state_census.csv` (owner tag/market/region template) | built 07-02 (mod-agnostic) |
| `aggr-save-employment.py` | aggr- | cohesive | COMMON per-state employment/vacancy census: building `staffing` vs `levels` (EMPTY buildings) paired with pop `wealth` (DESTITUTE workforce) → `aggr_employment.csv` + `aggr_employment_pops.csv` (state × profession). Answers "idle pops sitting next to empty buildings, in matching professions?" | built 07-16 (mod-agnostic) |
| `run-save-aggr.py` | run- (Set2 master) | ≤30 | per mod: `aggr-save-matches` + `aggr-save-overbuild` (subprocess) | built 07-02 |
| `aggr-save-matches.py` | aggr- | ≤60 | filter the COMMON `raw_flags` pool to the mod's kw + `*_fingerprint_*`; decode values → `aggr_save_matches.csv` | built 07-02 (refocused; never re-reads the save) |
| `aggr-save-overbuild.py` | aggr- | cohesive | T101 cap verdicts (ported) → `aggr_census_overbuild.csv` + per-mod `metrics.csv` (fp / persisted / absent-suspect / overbuild) | built 07-02 |
| `run-save-diag.py` | run- (Set3 master) | ≤45 | seed `diag_literals.csv` → ROOT; per mod call the SHARED engine with `--kind save-CURR` | built 07-02 |
| `config_saveparse.toml` | config (data) | n/a | managers(+pops), decode factor, cap pattern + catalogs, nonpersist pattern, goods/market keys, diag seeds, output names | built |
| `diag_literals.example.csv` | literal (tracked seed) | n/a | save-side diagnostics rules → loaded to `save-CURR/diag_literals.csv` | built (seeded) |
| `goods_ids.example.csv` | literal (tracked seed) | n/a | the goods catalog (`goods_id,goods_name,base_price`; 49 market-traded goods, hand-curated: Services/Transportation/Electricity/Gold excluded — no price channels) | built (user-curated 07-02) |
| `README.md` | doc | n/a | framework contract (usage) | done |
