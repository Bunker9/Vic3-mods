# testbook/v2/tools/save-game-parser — per-mod save-game fingerprint parser

Companion to the log-triage job (`tools/`). Where triage joins a mod's keys against the game **logs**,
this joins them against a Victoria 3 **save** (`.v3`), which DURABLY persists a mod's variables and
modifiers — each attributed to the exact object that carries it — for a whole playthrough, offline.

```
python run_save_parser.py <MOD_NAME> [--save <file.v3>] [--prefix P] [--rerun]
```
- `MOD_NAME` (arg1, required) — output namespace `save-game-parser/<MOD_NAME>/`. Join keys are read from
  `tools/<MOD_NAME>/list_kw.csv` (built by `run_log_triage.py`), so run the triage job for the mod first.
- `--save` — a specific save; default = **newest `*.v3`** in the Vic3 `save games` dir. Handles a plaintext
  (decompressed/melted) save AND the normal zip `.v3` (reads its `gamestate` member).
- `--prefix` — override the auto-derived mod abbreviation · `--rerun` — force re-scan.

## What persists (and what never does)
Save-state is **kind-dependent**. Only these leave a fingerprint:
- **variables** — `set_variable = { name = X value = … }` → stored as `flag=X` (Vic3 has **no** `set_*_flag`
  effect; "flags" ARE variables — see `docs/vic3-token-gotchas.md`). Numeric `type=value` vars are
  fixed-point **×100000** (decoded back to the real value in the CSV; calibrated: JIANGXI cap 1008 ↔ 100800000).
- **modifiers** — `modifier=X` with a native `start_date` (so a modifier doubles as a *dated* fingerprint).

Loc keys, scripted effects/triggers, decision ids, script-values, and file basenames are NOT save state —
their absence is normal and reported separately.

## Architecture (thin master + single-purpose subs sharing a lib)
| script | stage | output in `save-game-parser/<MOD_NAME>/` |
|---|---|---|
| `lib_saveparse.py` | — | shared: args, paths, kw-list load, save resolve (zip/plaintext), streaming scanner |
| `aggr_save_matches.py` | 1 | `matched_savefile_loglines.csv` (one row per persisted occurrence) |
| `anal_save_report.py` | 2 | `diagnostics.md` (fingerprints found · other persisted · expected/suspicious absent) |
| `run_save_parser.py` | master | resolves the save, sequences 1→2, owns reuse/rerun |

### `matched_savefile_loglines.csv` columns
`mod, fp, fp_type, save_token, section, doc_path, value, vtype, date, line_no, sample`
- **fp_type** — `variable` / `modifier` / `global_variable` / `other`
- **doc_path** — dotted breadcrumb of enclosing named blocks, e.g.
  `country_manager.database.470.timed_modifiers.modifiers` — the quick way to navigate to it in the save.
- **value** — decoded variable value (blank for modifiers) · **date** — modifier `start_date` (blank for vars)
- **line_no** — 1-based line in the (decompressed) save.

## Fingerprints
The scan always also matches the generic `<abbr>_fingerprint_*` pattern, so deliberate save-fingerprint
markers (DEV-RULES "Save-fingerprint debugging") are picked up even before they're in `list_kw.csv`. Add
`set_variable = { name = <abbr>_fingerprint_<feature> value = yes }` markers to a mod, run a game, then
re-scan — the new markers appear under "Deliberate fingerprints found".

Per-mod outputs are gitignored (regenerable from a save); the scripts + this README are tracked.
