# Framework-Logtriage — script manifest

> One row per script/artifact. **STUB skeleton created 2026-06-30; Phase 3 not yet implemented.** Code files
> are hyphen-named, import `../Framework-common` (top-level via sys.path); the master runs the `aggr-`/`anal-`
> stages as SUBPROCESSES. Migrates the old `tools/run_log_triage.py` + `aggr_log_matches.py` + `anal_log_triage.py`.

| file | class | lines | purpose | status |
|---|---|---|---|---|
| `run-logtriage.py` | run- (orchestrator) | ≤50 | read `data-<Mod>` → `aggr-log-matches` → `anal-log-triage` (subprocess); reuse/`--rerun` | built |
| `aggr-log-matches.py` | aggr- | ≤50 | join game logs vs `data-<Mod>` keys/files/debuglines → `aggr_log_matches.csv` | built |
| `anal-log-triage.py` | anal- | cohesive (may exceed 50) | markers fired/unfired + benign-filtered errors + loc-for-all-kw → `aggr_markers_status.csv` + `diagnostics.md` | built |
| `config_logtriage.toml` | config (data) | n/a | log filenames+severity, refire threshold, benign path, verdict strings, output names | built |
| `benign.csv` | data (shared, TRACKED) | n/a | mod-agnostic benign error signatures (`human_agreed,pattern,count`) | built (seeded; merge curated rows from `tools/benign.csv` if desired) |
| `README.md` | doc | n/a | framework contract | done |
