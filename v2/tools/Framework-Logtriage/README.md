# Framework-Logtriage — game LOGS + `data-<Mod>` → `log-CURR-*`

> Status: **BUILT — Phase 3 complete (2026-06-30); smoke-tested on NoUSChickenMod** (surfaced 6 real errors
> incl. the set-but-unused fingerprints — empirically confirming the dummy-use rule — and the loc-for-all-kw
> check). Ported the old `tools/aggr_log_matches.py` +
> `tools/anal_log_triage.py` here. Design home: `hk-config/roadmap/MOD-DEBUG-FRAMEWORK.md`. Imports `../Framework-common`.
> **Run this BEFORE any manual log deep-dive** (DEV-RULES "Triage framework FIRST").

Joins a mod's `data-<Mod>` token lists (from Framework-ModParse) against the game LOGS for the current run, and
reports markers fired-vs-unfired + mod-attributable errors (benign-filtered).

```
python run-logtriage.py <MOD_NAME> [--logs DIR] [--rerun]
```
- Reads `Game-Victoria3/data-<MOD_NAME>/raw_keywords.csv` etc. (run Framework-ModParse first).
- `--logs` overrides the logs dir (else from `config_game.toml`).

## Outputs — `Game-Victoria3/log-CURR-<ts>-<branch>/<MOD_NAME>/`
| file | class | content |
|---|---|---|
| `aggr_log_matches.csv` | aggr | one row per file/kw/dbg match in the logs (was `matched_loglines.csv`) |
| `aggr_markers_status.csv` | aggr | per-marker fired/unfired + count (was `markers_status.csv`) |
| `diagnostics.md` | report | markers fired-vs-unfired, errors (benign-suppressed), **loc-for-all-kw** findings |

## Repurposed: loc-for-all-kw check (§C.3, was the DEAD `list_loc.csv`)
`raw_loc.csv` (from ModParse) is now CONSUMED: every player-facing kw (modifier/event/decision name) must have a
matching loc entry; a kw with no loc = a static-check finding surfaced in `diagnostics.md` (and later the
Static component). Previously `list_loc.csv` was produced but never read.

## Shared benign catalog — `benign.csv` (human-curated, mod-agnostic, TRACKED)
Each distinct error line is normalised to a mod-agnostic signature and matched. Columns `human_agreed,pattern,count`:
`Y`→benign (suppressed) · `N`→tracked error (FAIL) · blank→new/unreviewed. Lives here (not under any mod).

## Config — `config_logtriage.toml`
Log filenames + severity map (`error.log`=error, `debug.log`=debug, `game.log`=info), refire-loop threshold,
benign-catalog path, verdict strings. No literals in the scripts.

## Scripts — see `MANIFEST.md`.
