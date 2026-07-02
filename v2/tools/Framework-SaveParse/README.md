# Framework-SaveParse — game SAVE + `data-<Mod>` → `save-CURR/` (parse-once)

> Status: **REWORKED Sets 1-3 complete (2026-07-02)** — the save is parsed ONCE into a COMMON pool; per-mod
> analysis joins the pool and NEVER re-reads the 147 MB file (the old per-mod re-parse pipeline is retired).
> Includes the market/goods price extraction (T103). A BINARY ironman save yields 0 rows — feed a
> non-ironman / **melted** `.v3`. Design home: `hk-config/roadmap/ROADMAP-debug-framework-rework.md`.
> Imports `../Framework-common`; Set-3 reuses the SHARED diagnostics engine in `../Framework-Logtriage`.

Where Logtriage joins keys against the LOGS, this joins them against a Victoria 3 **save** (`.v3`), which
durably persists a mod's variables + modifiers attributed to the exact object (`doc_path`). Plus the
state/building census, over-cap classification, and per-market goods prices.

```
python run-saveparse.py <MOD> [<MOD> ...] [--save <file.v3>] [--prefix P] [--rerun]
python run-saveparse.py --all
```
Requires Framework-ModParse first (`data-<Mod>`). The three sets also run standalone:

| set | master | what it does | when to run alone |
|---|---|---|---|
| 1 | `run-save-parse.py [--save F] [--rerun]` | archive prior `save-CURR*` ONCE + parse the save ONCE → the COMMON pool (skipped entirely when the pool exists and no `--rerun`) | new save to analyse |
| 2 | `run-save-aggr.py <MOD>.../--all` | per mod: filter/join the pool vs `data-<Mod>` → `<Mod>/aggr_*` + `metrics.csv` | re-attribute without re-parsing |
| 3 | `run-save-diag.py <MOD>.../--all [--literals CSV]` | the SHARED engine (`Framework-Logtriage/ext-diag-eval` + `gen-diag-md`, `--kind save-CURR`) → `<Mod>/diagnostics.md` | re-diagnose after curating rules |

## Outputs — `Game-Victoria3/save-CURR/`
| where | file | content |
|---|---|---|
| ROOT (common, Set 1) | `raw_buildings/raw_states/raw_countries/raw_state_regions/raw_pops.csv` | one streaming pass per save manager (RAW IDs — UAT SP-02) |
| ROOT (common) | `raw_flags.csv` | EVERY persisted `flag=`/`variable=`/`modifier=`/`global_variable=` with doc_path (SORT-not-FILTER; undecoded) |
| ROOT (common) | `raw_market_goods.csv` · `goods_ids.csv` | per (market × goods): current/min/max price, sample date (T103); the id→name catalog (generated from `game_files_path` goods files, or the tracked seed) |
| ROOT (common) | `raw_state_census.csv` | the ENRICH join: building rows with owner tag + owner market + state-region template |
| `<Mod>/` (Sets 2-3) | `aggr_save_matches.csv` · `aggr_census_overbuild.csv` · `metrics.csv` · `diag_fired.csv` · `diagnostics.md` | mod tokens/fingerprints persisted (decoded values/dates); over-cap verdicts (T101 generic cap pattern); engine findings |

## What persists (kind-dependent)
- **variables** → `flag=X` in the save (Vic3 has no `set_*_flag`; "flags" ARE variables). Numeric `type=value`
  vars are fixed-point ×100000 (decoded in Set-2 via the single `Framework-common` decoder).
- **modifiers** → `modifier=X` with a native `start_date` (a modifier doubles as a *dated* fingerprint).
- Loc keys / scripted effects / decision ids are NOT save state — absence is normal (the `metrics.csv`
  `kw_absent_suspect` counts only absences NOT matching the config `nonpersist_pattern`).

## GENERIC cap analysis (T101) + goods prices (T103)
Over-cap matches the mod's cap variable by the **config `cap_var_pattern`** on state-region variables — never
a hardcoded name; trigger-gated buildings report `NO_STORED_CAP`, not a false pass. Goods prices come from
`market_manager` `price_trend` channels (numeric goods id; LAST sample = current price); join
`raw_market_goods` × `goods_ids` × `raw_countries.market` for "what does good G cost in country C's market".
Per-state trade/local-goods blocks are NOT yet extracted (tracked in T103's remainder).

## Config — `config_saveparse.toml`
Manager targets + per-manager columns (incl. `pops`), the ÷100000 factor, the cap-var pattern + capped
catalogs, the nonpersist pattern, the goods/market keys + catalog names, the diag seed names, every output
filename. No literals in the scripts.

## Scripts — see `MANIFEST.md`.
