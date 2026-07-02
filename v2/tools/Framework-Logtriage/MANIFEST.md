# Framework-Logtriage — script manifest

> One row per script/artifact. **REWORKED (SORT-not-FILTER Sets 1-3, completed 2026-07-02).** Code files are
> hyphen-named, import `../Framework-common` (top-level via sys.path); masters run their stages as
> SUBPROCESSES. The pre-rework pipeline (`anal-log-triage.py` + `benign.csv`) was RETIRED 2026-07-02
> (benign's curated rows migrated into `smoke_detector.example.csv`). Design home:
> `hk-config/roadmap/ROADMAP-debug-framework-rework.md`.

| file | class | lines | purpose | status |
|---|---|---|---|---|
| `run-logtriage.py` | run- (TOP master) | ≤50 | Set1 → Set2 → Set3; mods = positional / `--all` / `config_logmods.toml` fallback; the ONLY flow entry | built 07-02 |
| `run-log-sort.py` | run- (Set1 master) | ≤50 | archive prior `log-CURR*` ONCE (sole archive point) + seed smoke_detector → ROOT + run ext/aggr below | built 07-01 |
| `ext-log-lines.py` | ext- | ≤50 | ALL `*.log` → COMMON `log-CURR/raw_loglines.csv` + `raw_errors.csv` (+signature); drops NOTHING | built 07-01 |
| `aggr-log-errorpatterns.py` | aggr- | ≤50 | group error signatures → `_global/error_patterns.csv` (dep-free `normalize_error`) | built 07-01 |
| `run-log-aggr.py` | run- (Set2 master) | ≤50 | per mod: `aggr-log-matches` + `aggr-log-markers` (subprocess) | built 07-02 |
| `aggr-log-matches.py` | aggr- | ≤55 | join COMMON `raw_loglines` vs `data-<Mod>` keys → `<Mod>/aggr_log_matches.csv` (never re-reads logs) | built 07-02 (refocused) |
| `aggr-log-markers.py` | aggr- | ≤60 | marker fired/unfired + re-fire flag + loc-for-all-kw → `<Mod>/aggr_markers_status.csv` + `metrics.csv` | built 07-02 |
| `run-log-diag.py` | run- (Set3 master) | ≤50 | seed diag_literals → ROOT; `aggr-log-smoke` (global); per target `ext-diag-eval` + `gen-diag-md` | built 07-02 |
| `aggr-log-smoke.py` | aggr- | ≤55 | `raw_errors` × smoke_detector → `_global/metrics.csv`; accrues counts/examples + APPENDS new signatures for review | built 07-02 |
| `ext-diag-eval.py` | ext- | ≤45 | rules × `<target>/metrics.csv` → `<target>/diag_fired.csv`; `--literals` = SWAPPABLE rules CSV (per game/version, UAT LT-06) | built 07-02 |
| `gen-diag-md.py` | gen- | ≤40 | metrics + fired rows → `<target>/diagnostics.md`; ALL prose from the CSV (NO-LITERALS) | built 07-02 |
| `lib_diag.py` | lib_ | 52 | safe condition evaluator (no `eval`) + `fired()` + `render_md()` | built 07-01 |
| `chk-diagnostics.py` | chk- | 38 | data-driven evaluator self-test (`python chk-diagnostics.py`, NOT pytest) | built 07-01 (5/5) |
| `config_logtriage.toml` | config (data) | n/a | log files+severity, refire threshold, [smoke]+[diag] example→ROOT names, all output names | built |
| `config_logmods.toml` | config (data) | n/a | tracked mod list the TOP master batches when called with no mods/`--all` | built |
| `smoke_detector.example.csv` | literal (tracked seed) | n/a | curated rule-out list (`human_agreed,pattern,count,example`); loaded → `log-CURR/smoke_detector.csv`; holds the migrated benign rows | built |
| `diag_literals.example.csv` | literal (tracked seed) | n/a | diagnostics rules (`id,text,condition,logical_reasoning,user_comments,status`); loaded → `log-CURR/diag_literals.csv` | built |
| `diag_snippets.example.csv` | literal (test fixtures) | n/a | evaluator test cases for `chk-diagnostics` | built |
| `README.md` | doc | n/a | framework contract (usage) | done |
