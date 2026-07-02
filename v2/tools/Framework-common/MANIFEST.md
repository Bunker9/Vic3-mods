# Framework-common — manifest (shared lib + master scripts)

> One row per module/script. ALL rows below are BUILT (lib core Phase 1; masters/toggle Phases 5-6; multi-mod
> `--all` front-end added 2026-07-01). Hyphenated dir ⇒ not a Python package: callers put this dir on
> `sys.path` and import the modules top-level (see README). `lib_*` keep `_` (Python can't `import a-b`).
> The TOGGLE script is INTERIM — the Framework-Toggle split (stubs) supersedes it when built.

| file | class | lines | purpose | status |
|---|---|---|---|---|
| `lib_args.py` | lib_ | 73 | the ONE standardized CLI arg contract (MOD_NAME/MOD_PATH/--save/--logs/--prefix/--rerun) + the MASTER multi-mod front-end (`parse_master_args`, `--all`, `selected_mods`) | built |
| `lib_io.py` | lib_ | 50 | deterministic text/CSV IO (`write_csv(sort=)`) + `walk_files` | built |
| `lib_paths.py` | lib_ | 73 (cohesive) | self-location + all external path resolution via `config_game.toml`; the `data-<Mod>` / `<kind>-<label>/<mod>` output layout | built |
| `lib_config.py` | lib_ | 21 | read-only TOML loader (`tomllib`) | built |
| `lib_parse.py` | lib_ | 92 (cohesive) | prefix detect · fixed-point decode · save `iter_save_lines`/`iter_save_blocks` · `normalize_error` | built |
| `run-debug-master.py` | run- | ≤50 | MASTER: run ModParse → Logtriage → SaveParse for one mod | built |
| `run-scrub.py` | run- | ≤50 | MASTER: wipe all generated data, leave code + configs (dry-run default, `--commit`) | built |
| `run-archive-curr.py` | run- | ≤50 | STEP 1 of the log/save masters (also standalone): create the `Game-<game>/` data root if missing + demote prior `*-CURR` dirs so only the newest keeps the marker | built 2026-07-01 |
| `testbook-toggle-markers.py` | testbook- | cohesive | mod-agnostic ON/OFF toggle of `debug_log`/`debug_log_scopes` + `_fingerprint_` lines (dry-run default, `--commit`; BOM + line endings preserved) | built (dry-run tested; supersedes hk-config `testbook_toggle_debuglog.py`) |
| `config_toggle.toml` | config (data) | n/a | the toggle's line PATTERNS + comment marker + which extensions to touch | built |
| `config_game.example.toml` | config (tracked) | n/a | template for the per-machine game config (paths + `[mod_locations]`); copy → `config_game.toml` | tracked |
| `config_game.toml` | config (gitignored) | n/a | per-machine abs paths (may contain OS username → PII); the ONE file edited on a new machine; loaded by `lib_paths` | per-machine (never committed) |
| `config_naming.toml` | config (tracked) | n/a | class-prefix naming conventions (machine-readable mirror of DEV-RULES) | tracked |
| `README.md` | doc | n/a | the MASTER README (canonical entry point) | done |
| `HOW_TO_USE.md` | doc | n/a | practical cookbook: every master script's invocations + per-script config | done |
