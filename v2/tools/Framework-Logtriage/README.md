# Framework-Logtriage — game LOGS + `data-<Mod>` → `log-CURR/` (SORT-not-FILTER)

> Status: **REWORKED Sets 1-3 complete (2026-07-02); validated on the 2026-07-01 real run** (6189 error lines
> captured incl. the jomini/building_manager classes the old triage dropped; MyDiploPlay 5676 common-pool
> matches; smoke: 1890 tracked + 37 new signatures appended for review). The pre-rework pipeline
> (`anal-log-triage.py` + `benign.csv`) is retired. Design home:
> `hk-config/roadmap/ROADMAP-debug-framework-rework.md`. Imports `../Framework-common`.
> **Run this BEFORE any manual log deep-dive** (DEV-RULES "Triage framework FIRST").

Sorts EVERY line of every configured `*.log` into a COMMON pool (drops NOTHING — attribution is a later,
per-mod concern that deletes nothing), then joins per-mod keys against that pool, then runs a data-driven
diagnostics engine whose every finding string lives in a swappable rules CSV.

```
python run-logtriage.py                        # mods from config_logmods.toml
python run-logtriage.py <MOD> [<MOD> ...]      # explicit mods
python run-logtriage.py --all [--logs DIR]     # every config_game.toml [mod_locations] mod
```
Requires Framework-ModParse first (`data-<Mod>`). The three sets also run standalone:

| set | master | what it does | when to run alone |
|---|---|---|---|
| 1 | `run-log-sort.py [--logs DIR]` | archive prior `log-CURR*` ONCE (the SOLE archive point) + seed `smoke_detector.csv` → ROOT + sort ALL logs → COMMON raws + `_global/error_patterns.csv` | new game run, refresh the pool |
| 2 | `run-log-aggr.py <MOD>.../--all` | per mod: join the COMMON pool vs `data-<Mod>` → `<Mod>/aggr_*` + `metrics.csv` | re-attribute without re-sorting |
| 3 | `run-log-diag.py <MOD>.../--all [--literals CSV]` | seed `diag_literals.csv` → ROOT; global smoke metrics; evaluate + render `diagnostics.md` per mod + `_global` | re-diagnose after curating the CSVs |

## Outputs — `Game-Victoria3/log-CURR/`
| where | file | content |
|---|---|---|
| ROOT (common, Set 1) | `raw_loglines.csv` / `raw_errors.csv` | EVERY line / every error line + normalized signature |
| ROOT (common) | `smoke_detector.csv` · `diag_literals.csv` | loaded from the tracked `.example` seeds; smoke accrues counts + new signatures |
| `_global/` | `error_patterns.csv` · `metrics.csv` · `diag_fired.csv` · `diagnostics.md` | grouped signatures; smoke verdict metrics; global findings |
| `<Mod>/` (Sets 2-3) | `aggr_log_matches.csv` · `aggr_markers_status.csv` · `metrics.csv` · `diag_fired.csv` · `diagnostics.md` | matches over the pool; markers fired/unfired/re-fire; loc-for-all-kw; per-mod findings |

## The two curated CSVs (the ONLY things a session should edit here — append-only)
- **`smoke_detector`** (`human_agreed,pattern,count,example`): `Y` = agreed noise (suppressed) · `N` = tracked
  error (drives `tracked_errors`) · blank = unreviewed. `aggr-log-smoke` appends every UNSEEN signature with a
  blank verdict for human review — curate by filling Y/N, never delete rows.
- **`diag_literals`** (`id,text,condition,logical_reasoning,user_comments,status`): the diagnostics RULES; all
  human-readable finding text lives here (NO-LITERALS). `condition` = `metric OP value` over `metrics.csv`
  (safe evaluator, no `eval`; unknown metric ⇒ rule doesn't fire). **Swappable data:** `--literals <csv>`
  points the engine at another rules file — another PDX game or an experimental set — with zero code change.

## Config — `config_logtriage.toml`
Log filenames + severity map, refire-loop threshold, the smoke/diag example→ROOT names, every output filename.
No literals in the scripts. `config_logmods.toml` = the tracked mod list the top master batches by default.

## Scripts — see `MANIFEST.md`.
