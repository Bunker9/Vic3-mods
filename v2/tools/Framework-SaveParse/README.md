# Framework-SaveParse — game SAVE + `data-<Mod>` → `save-CURR-*`

> Status: **BUILT + VALIDATED (Phase 4, 2026-06-30)** on a melted 147 MB `.v3` (parsed 9903 buildings / 962
> states / 271 countries; found real fingerprints + census + over-cap). A BINARY ironman save yields 0 rows —
> feed a non-ironman / **melted** `.v3` (see note below). Replaced the original save-game-parser job (retired
> 2026-07-01). Design home: `hk-config/roadmap/MOD-DEBUG-FRAMEWORK.md`. Imports `../Framework-common`.

Where Logtriage joins keys against the LOGS, this joins them against a Victoria 3 **save** (`.v3`), which
durably persists a mod's variables + modifiers attributed to the exact object that carries them. Also runs a
state/building census + over-cap classification.

```
python run-saveparse.py <MOD_NAME> [--save <file.v3>] [--prefix P] [--rerun]
```
- Reads `Game-Victoria3/data-<MOD_NAME>/` (run Framework-ModParse first).
- `--save` a specific save; else newest `*.v3` in the save-games dir (from `config_game.toml`). Handles zip
  (`gamestate` member) + plaintext via `Framework-common.lib_parse`. (Save-games dir from `config_game.toml`.)
- **STEP 1 (automatic):** invokes `Framework-common/run-archive-curr.py save-CURR`, which creates the
  `Game-<game>/` data root if missing and demotes every prior `save-CURR*` to `save-<label>` so ONLY this run
  keeps the `CURR` marker (the latest-source signal for the report).

> **Save format note:** parses a TEXT gamestate — either a normal zip `.v3` (text `gamestate` member) or a
> plaintext/melted save. A BINARY ironman save is not parseable as-is (mojibake -> 0 rows); melt/decompress it
> first, or save in non-ironman mode.

## What persists (kind-dependent)
- **variables** → `flag=X` in the save (Vic3 has no `set_*_flag`; "flags" ARE variables). Numeric `type=value`
  vars are fixed-point ×100000 (decoded by the single `Framework-common` decoder).
- **modifiers** → `modifier=X` with a native `start_date` (a modifier doubles as a *dated* fingerprint).
- Loc keys / scripted effects / decision ids / file basenames are NOT save state — absence is normal.

## Outputs — `Game-Victoria3/save-CURR/<MOD_NAME>/` (raw → data/aggr → report)
| file | class | content |
|---|---|---|
| `raw_buildings.csv` / `raw_states.csv` / `raw_countries.csv` / `raw_state_regions.csv` | raw | one pass per save manager |
| `aggr_save_matches.csv` | aggr | one row per persisted mod-token/fingerprint occurrence (object `doc_path`, value, date) |
| `aggr_state_census.csv` | aggr | per (state×building) + (state×variable): owner tag · level/value (decoded) |
| `aggr_census_overbuild.csv` | aggr | (tag,state_region,building) over the mod's intended cap, classified |
| `diagnostics.md` | report | fingerprints persisted/absent + over-cap classify (mod-script-error vs engine-overbuild) |

## GENERIC cap analysis (kills the `zw_mfg_cap` hardcode — T101)
The over-cap check matches the mod's cap variable by a **config-driven PATTERN** (e.g. `*_*cap*`), never a
hardcoded `zw_mfg_cap`. Buildings whose cap is enforced by triggers/script-values (no stored numeric cap) are
reported **MISSING-CAP**, not a false pass. Raw extractors stay 100% mod-agnostic — no probe-tag literals
([[no-hardcode-test-probe-nations]], T101).

## Config — `config_saveparse.toml`
Manager targets + per-manager columns, the `÷100000` factor, the generic cap-var pattern, the capped-building
catalog, doc_path match strings, verdict strings. No literals in the scripts.

## Scripts — see `MANIFEST.md`.
