# Framework-Logtriage — script manifest

> One row per script/artifact. **BUILT (Phase 3, 2026-06-30; smoke-tested).** Code files are hyphen-named,
> import `../Framework-common` (top-level via sys.path); the master runs the `aggr-`/`anal-` stages as
> SUBPROCESSES. Replaced the original log-triage job (retired 2026-07-01).

| file | class | lines | purpose | status |
|---|---|---|---|---|
| `run-logtriage.py` | run- (orchestrator) | ≤50 | read `data-<Mod>` → `aggr-log-matches` → `anal-log-triage` (subprocess); reuse/`--rerun` | built |
| `aggr-log-matches.py` | aggr- | ≤50 | join game logs vs `data-<Mod>` keys/files/debuglines → `aggr_log_matches.csv` | built |
| `anal-log-triage.py` | anal- | cohesive (may exceed 50) | markers fired/unfired + benign-filtered errors + loc-for-all-kw → `aggr_markers_status.csv` + `diagnostics.md` | built |
| `config_logtriage.toml` | config (data) | n/a | log filenames+severity, refire threshold, benign path, verdict strings, output names | built |
| `benign.csv` | data (shared, TRACKED) | n/a | mod-agnostic benign error signatures (`human_agreed,pattern,count`) | built (seeded; human-curated over time) |
| `README.md` | doc | n/a | framework contract | done |

## Rework additions — 2026-07-01 (SORT-not-FILTER + split masters + diagnostics engine)
| file | class | purpose | status |
|---|---|---|---|
| `run-log-sort.py` | run- (Set1 master) | archive log-CURR once + seed smoke + run ext-log-lines/aggr-log-errorpatterns | built + tested (6189 errors) |
| `ext-log-lines.py` | ext- | ALL `*.log` → COMMON `log-CURR/raw_errors.csv` + `raw_loglines.csv` (drops NOTHING) | built |
| `aggr-log-errorpatterns.py` | aggr- | group error signatures → `_global/error_patterns.csv` (dep-free) | built |
| `lib_diag.py` | lib_ | safe condition evaluator + `fired` + `render_md` (imported) | built |
| `chk-diagnostics.py` | chk- | data-driven evaluator self-test (`python chk-diagnostics.py`, NOT pytest); 5/5 | built |
| `diag_snippets.example.csv` | literal | evaluator test cases (condition,metrics,expected,sample_snippet) | built |
| `smoke_detector.example.csv` | literal | tracked seed → loaded to log-CURR ROOT (`human_agreed,pattern,count,example`) | built |
| `diag_literals.example.csv` | literal | log diagnostics rules (`id,text,condition,logical_reasoning,user_comments,status`) | built |
| `config_logmods.toml` | config | mod list for the convenience top-master | built |
| `ext-diag-eval.py` / `gen-diag-md.py` / `run-log-diag.py` | ext-/gen-/run- | Set-3 wiring over lib_diag | STUB (needs Set-2 metrics) |
| `run-log-aggr.py` / `aggr-log-matches.py` (refocus) / `run-logtriage.py` (top) | run-/aggr- | Set-2 per-mod + top master | TODO next session |
| `anal-log-triage.py` (OLD) | anal- | superseded by Set-1/2/3; retire when Set-2/3 land | retire pending |
