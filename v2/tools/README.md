# testbook/v2/tools — generic per-mod log-triage job

**Run this BEFORE manually deep-diving game logs** (DEV-RULES: "Triage framework FIRST").

```
python run_log_triage.py <MOD_NAME> [<MOD_PATH>] [--rerun] [--prefix P] [--logs DIR]
```
- `MOD_NAME` (arg1, required) — output namespace `tools/<MOD_NAME>/`. The **only** arg needed for a
  no-change regression rerun (lists already on disk).
- `MOD_PATH` (arg2, optional) — mod source folder; needed only to (re)build the lists.
- `--rerun` rebuild lists · `--prefix` override keyword prefix · `--logs` override Vic3 logs dir.

```
# first run (build lists from source + analyse):
python run_log_triage.py NoUSChickenMod "C:\...\mod1-inov\NoUSChickenMod" --rerun
# after the next game run (reuse lists, refresh analysis):
python run_log_triage.py NoUSChickenMod
```

## Architecture (thin orchestrator + single-purpose subs sharing a lib)
| script | stage | output in `tools/<MOD_NAME>/` |
|---|---|---|
| `lib_triage.py` | — | shared helpers (args, paths, log resolve, CSV IO, prefix detect, benign) |
| `ext_mod_files.py` | 1 | `list_files.csv` (file_id, rel_path, basename) |
| `ext_mod_keywords.py` | 2 | `list_kw.csv` (kw_id, kw, kind) — prefix auto-derived |
| `ext_mod_debuglines.py` | 3 | `list_debug_lines.csv` (dbg_id, text, file_id, line_no) |
| `ext_mod_loc.py` | 3b | `list_loc.csv` (loc_id, key, file_id, line_no) |
| `aggr_log_matches.py` | 4 | `matched_loglines.csv` (one row per file/kw/dbg match in the logs) |
| `anal_log_triage.py` | 5 | `markers_status.csv` + `diagnostics.md` |
| `run_log_triage.py` | master | sequences 1→5, owns reuse/rerun |

Every script honours the same arg contract and is runnable standalone for debugging.

## Reading `diagnostics.md`
- **Markers fired vs unfired** — a defined `debug_log` marker that never appears = that
  effect/decision never ran. A marker firing ≥100× is flagged as a possible re-fire loop.
- **Error lines** — `error.log` lines, with agreed-benign noise suppressed (see below).

## Shared benign catalog — `tools/benign.csv` (human-curated, lives OUTSIDE all mods)
Error messages recur across mods, so the benign catalog is **shared**. Each distinct error line is
normalised to a mod-agnostic signature (filenames / quoted values / mod tokens / numbers masked) and
matched against the catalog. Columns: `human_agreed, pattern, count`.
- `human_agreed = Y` → truly benign → **suppressed**.
- `human_agreed = N` → NOT benign → reported every run as a **tracked error** (verdict FAIL).
- blank → unreviewed → reported as a **new benign error** until you flag it.

Workflow: run triage → it prints up to two lines —
`N new benign errors like 'sig(count)',...` (freshly added, pending review) and
`M existing tracked errors like 'sig(count)',...` (your `N`-flagged patterns). Open `benign.csv`,
set `human_agreed` Y/N per row, re-run. `count` = occurrences in the most recent run.

Generated per-mod CSV/md are gitignored (regenerable). The scripts and the shared `benign.csv` are
tracked.
