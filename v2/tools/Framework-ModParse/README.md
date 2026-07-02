# Framework-ModParse — mod SOURCE → `data-<Mod>` token files (idempotent)

> Status: **BUILT — Phase 2 complete (2026-06-30); smoke-tested + idempotent** (NoUSChickenMod: byte-identical
> across reruns). Built on `Framework-common` (replaced the original `ext_mod_*` extractors, retired 2026-07-01). Design home:
> `hk-config/roadmap/MOD-DEBUG-FRAMEWORK.md`. Imports `../Framework-common` (top-level modules via sys.path).

The upstream framework. Reads a mod's SOURCE tree and emits the `data-<Mod>` token files that BOTH downstream
frameworks (Logtriage, SaveParse) consume. This is the explicit single-source contract that replaces the old
implicit cross-job `list_kw.csv` read.

```
python run-modparse.py <MOD_NAME> <MOD_PATH> [--prefix P] [--rerun]
```
- `MOD_NAME` (arg1) — output namespace `Game-Victoria3/data-<MOD_NAME>/`.
- `MOD_PATH` (arg2) — the mod source folder (resolved via `config_game.toml` `[mod_locations]` if omitted).
- The master runs the `ext-*` extractors as **subprocesses** (hyphenated code filenames are not importable);
  `ext-mod-files` runs first (the others FK its `raw_files.csv`). Each `ext-*` is standalone-runnable too.

## Idempotency guarantee (§A)
Output depends ONLY on the mod source at its current commit. Same commit ⇒ byte-identical `data-<Mod>` files
whenever run (today / +1mo / +1yr): `lib_io.walk_files` sorts the tree, ids are assigned in that stable order,
and no timestamps/abs-paths are written into the data. Verified by re-running + comparing checksums.

## Outputs — `Game-Victoria3/data-<MOD_NAME>/` (raw → data → aggr, §B)
| file | class | content |
|---|---|---|
| `raw_files.csv` | raw | every mod source file (file_id, rel_path, basename) |
| `raw_keywords.csv` | raw | mod keywords/tokens (kw_id, kw, kind) — prefix auto-derived. **The shared join key.** |
| `raw_debuglines.csv` | raw | ACTIVE (uncommented) `debug_log` markers (dbg_id, text, file_id, line_no) |
| `raw_loc.csv` | raw | localization keys (loc_id, key, file_id, line_no) |
| `raw_fingerprints.csv` | raw | declared `<abbr>_fingerprint_*` markers (fp_id, fp_name, op[set/change/has/other], file_id, line_no) — feeds SaveParse + the set-before-change check |
| `raw_tokens.csv` | raw | UNFILTERED token dump: ALL identifiers + occurrence counts (commented-out excluded) — `keyword,occurrence` (rework additive, 2026-07-01) |
| `data_*.csv` / `aggr_*.csv` | data / aggr | raw enriched via lookups/joins, and rollups — added when a consumer needs them (none yet) |

## Config — `config_modparse.toml`
`[scan].extensions` (which file types to walk), `[markers].fingerprint_infix`, `[outputs]` (the raw_* file
names). Parse-logic regexes (debug_log, loc, identifier) live in the scripts / `Framework-common.lib_parse`,
not in config.

## Scripts — see `MANIFEST.md`.
