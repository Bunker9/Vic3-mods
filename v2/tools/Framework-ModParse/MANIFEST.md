# Framework-ModParse — script manifest

> One row per script/artifact. Built in Phase 2 (2026-06-30); smoke-tested + idempotent. Code files are
> hyphen-named (run-/ext-); they import `../Framework-common` (top-level via sys.path) and the master invokes
> the `ext-*` as SUBPROCESSES. Arg contract + shared primitives come from `Framework-common`.

| file | class | lines | purpose | status |
|---|---|---|---|---|
| `run-modparse.py` | run- (orchestrator) | 27 | sequence the `ext-*` extractors (subprocess) → `data-<Mod>/` | built |
| `ext-mod-files.py` | ext- | 27 | mod source filenames → `raw_files.csv` | built (from `tools/ext_mod_files.py`) |
| `ext-mod-keywords.py` | ext- | 43 | mod keywords/tokens → `raw_keywords.csv` (the shared join key) | built |
| `ext-mod-debuglines.py` | ext- | 38 | active `debug_log` markers → `raw_debuglines.csv` | built |
| `ext-mod-loc.py` | ext- | 38 | localization keys → `raw_loc.csv` | built |
| `ext-mod-fingerprints.py` | ext- | 46 | declared `*_fingerprint_*` markers + op → `raw_fingerprints.csv` | built (NEW) |
| `config_modparse.toml` | config (data) | n/a | scan extensions, fingerprint infix, output file names | built |
| `README.md` | doc | n/a | framework contract | done |
