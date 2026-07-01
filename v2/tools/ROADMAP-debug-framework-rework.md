# ROADMAP — debug-framework rework (ModParse+ / SaveParse / Logtriage / Toggle / Diagnostics)

> **Authoritative design for the rework.** Status legend per file below: `STUB` = dummy header-comment only
> (this pass) · `TODO` = to implement · `DONE`. Governing rules land in `hk-config/docs/DEV-RULES.md` +
> memory. Master usage entry point stays `Framework-common/README.md` + `HOW_TO_USE.md`.

## Why (the 4 faults the first real run exposed)
1. **SaveParse re-parsed the 147 MB save PER MOD** — raw country/state/building/pop extraction is mod-agnostic;
   must run ONCE into a COMMON pool, then per-mod analysis reads it.
2. **Logtriage FILTERED logs instead of SORTING them** — only mod-token-matched lines survived, so real
   `jomini_script_system` / `building_manager` cpp errors (no mod keyword) were dropped. Must SORT every line of
   every `*.log` into common `raw_*`, drop NOTHING, attribute later. `benign.csv` → `smoke_detector.csv`.
   Diagnostics text was hardcoded → NO-LITERALS violation.
3. **Toggle was monolithic** — modularize.
4. **ModParse (the one good framework) gains an additive unfiltered token-dump** — every token + occurrence, no
   filters, commented-out excluded.

## Principles (→ DEV-RULES + memory)
- **SORT, don't FILTER** — raw stages keep everything.
- **Parse-once / analyse-per-mod as SEPARATE masters** — (1) parse-only → COMMON `raw_*` at run ROOT, (2) per-mod
  aggr, (3) diagnostics, (4) convenience top-master (all sets, all mods).
- **ROOT = the live build area** (`save-CURR/`, `log-CURR/`, gitignored). Curated inputs are TRACKED `*.example.*`
  in the framework folder, LOADED into ROOT at runtime — same pattern as `config_game.example.toml`→`config_game.toml`.
- **NO LITERALS IN CODE** — `smoke_detector` + `diag_literals` are DATA. `diag_literals` schema:
  `id, text, condition, logical_reasoning, user_comments, status`  (`status` = `keep`|`ignore`).
- **Naming:** code `.py/.ps1` = hyphens (`run-`/`ext-`/`aggr-`/`chk-`/`gen-`/`anal-`); data/config/CSV/TOML =
  underscores; importable modules + pytest keep `_` (`lib_*`, `test_*.py`); masters call hyphen subs as subprocesses.
- **FUTURE GUARDRAIL (new DEV-RULE):** once these feed the v2 HTML components, Claude may ONLY run MASTER scripts,
  edit configs, and APPEND to `smoke_detector`/`diag_literals` CSVs; NO ad-hoc analysis scripts.

## File inventory + status
### Framework-ModParse/ (additive only)
| file | kind | status | purpose |
|---|---|---|---|
| `ext-mod-tokens.py` | ext- | STUB | scan `.txt` (exclude commented) → `data-<Mod>/raw_tokens.csv` = `keyword,occurrence`, ALL tokens, no filter |
| `run-modparse.py` | run- | TODO | call `ext-mod-tokens` after the existing extractors |

### Framework-SaveParse/ (3 sets + split masters + convenience)
| file | kind | status | purpose |
|---|---|---|---|
| `run-save-parse.py` | run- (Set1 master) | STUB | parse save ONCE → COMMON raws at `save-CURR/` ROOT; skip if present / `--rerun` |
| `ext-save-blocks.py` | ext- | TODO | retarget output to `save-CURR/` ROOT (+ add `raw_pops.csv` manager) |
| `aggr-save-census.py` | aggr- | STUB | raws → `save-CURR/raw_state_census.csv` (mod-agnostic part of the old census) |
| `run-save-aggr.py` | run- (Set2 master) | STUB | per mod: COMMON raws + `data-<Mod>` → `save-CURR/<Mod>/aggr_*` |
| `aggr-save-matches.py` | aggr- | TODO | persisted mod tokens/vars/modifiers/fingerprints (doc_path+value) |
| `aggr-save-overbuild.py` | aggr- | STUB | per-mod over-cap classify (T101 cap pattern) |
| `run-save-diag.py` | run- (Set3 master) | STUB | save diagnostics → `save-CURR/<Mod>/diagnostics.md`; reuse Logtriage's `lib_diag`/renderer OR a light own version (decided at impl — NO pre-abstraction) |
| `run-saveparse.py` | run- (top) | TODO | convenience: Set1→Set2→Set3, all mods |
| `config_saveparse.toml` | config | TODO | + `raw_pops` manager |
| `diag_literals.example.csv` | literal | STUB | save-side diagnostics rules |

### Framework-Logtriage/ (SORT-not-FILTER, 3 sets + split masters + convenience)
| file | kind | status | purpose |
|---|---|---|---|
| `run-log-sort.py` | run- (Set1 master) | STUB | read ALL `*.log` → COMMON raws at `log-CURR/` ROOT; loads smoke seed |
| `ext-log-lines.py` | ext- | STUB | EVERY error line → `raw_errors.csv`; all lines → `raw_loglines.csv` |
| `aggr-log-errorpatterns.py` | aggr- | STUB | group error signatures → `log-CURR/_global/error_patterns.csv` (append-only). dep-free `lib_parse.normalize_error`; `drain3` optional (flagged) |
| `run-log-aggr.py` | run- (Set2 master) | STUB | per mod: join raws vs `data-<Mod>` keys → `log-CURR/<Mod>/aggr_*` |
| `aggr-log-matches.py` | aggr- | TODO | markers fired/unfired + re-fire + loc-for-all-kw over the FULL pool |
| `run-log-diag.py` | run- (Set3 master) | STUB | orchestrate the diagnostics engine → `log-CURR/<Mod>/diagnostics.md` + global |
| `lib_diag.py` | lib_ | STUB | safe `condition` evaluator over a metrics dict (no `eval`) |
| `ext-diag-eval.py` | ext- | STUB | metrics + `diag_literals` → fired rows (`condition` TRUE & `status=keep`) |
| `gen-diag-md.py` | gen- | STUB | render fired rows (`text`+`logical_reasoning`) → `diagnostics.md`; ALL strings from CSV |
| `chk-diagnostics.py` | pytest | STUB | assert conditions eval TRUE/FALSE vs `diag_snippets.example.csv` (error-log snippets) |
| `diag_snippets.example.csv` | literal | STUB | sample error-log snippets → expected metrics/outcome (test fixtures) |
| `run-logtriage.py` | run- (top) | TODO | convenience: all sets, all mods in `config_logmods.toml` |
| `config_logtriage.toml` | config | TODO | log files/severity, refire N, output names |
| `config_logmods.toml` | config | STUB | tracked list of mod names the convenience master batches |
| `smoke_detector.example.csv` | literal | STUB | `human_agreed,pattern,count,example` — `example` = exact matched line |
| `diag_literals.example.csv` | literal | STUB | log-side diagnostics rules |

### Framework-Toggle/ (NEW)
| file | kind | status | purpose |
|---|---|---|---|
| `ext-toggle-markers.py` | ext- | STUB | ss1: find fp*/`debug_log`(_scopes) in ONE file |
| `run-toggle-file.py` | run- | STUB | ss2: comment/uncomment ONE file (uses ss1+ss3) |
| `chk-toggle-scopes.py` | chk- | STUB | ss3: brace balance + no empty scope (if/else_if/else/immediate/when_taken/option/trigger/…) after toggle |
| `run-toggle.py` | run- (master) | STUB | ss4: target = repo folder / mod folder / single file; loop |
| `config_toggle.toml` | config | TODO | move here; add the scope-keyword set |

### Framework-common/ (no new diagnostics code)
The diagnostics engine + pytest live in **Framework-Logtriage** (above), not here — the pytest is driven by
error-LOG snippets and there is no proven second consumer. If SaveParse Set-3 later needs the same
condition-evaluator, extract ONLY `lib_diag` to common THEN (extract-on-second-use). Framework-common keeps its
existing `lib_*` + masters unchanged.

### Game-Victoria3/ (DATA ONLY, gitignored — example stubs demonstrate the runtime layout; scrubbed)
```
data-<Mod>/  raw_{files,keywords,debuglines,loc,fingerprints,tokens}.csv   + _LAYOUT.md
save-CURR/   raw_{countries,states,buildings,state_regions,pops,state_census}.csv   (COMMON, built once)
   _EXAMPLE_Mod/  aggr_save_matches.example.csv aggr_census_overbuild.example.csv diagnostics.example.md
log-CURR/    raw_errors.csv raw_loglines.csv smoke_detector.csv (loaded from .example)
   _global/       error_patterns.example.csv errors.example.md
   _EXAMPLE_Mod/  aggr_log_matches.example.csv aggr_markers_status.example.csv diagnostics.example.md
```

## Build order (execution)
1. Roadmap (this) + dummy stubs — DONE this pass (understanding-proof).
2. Framework-Logtriage diagnostics engine + `chk-diagnostics.py` (log-side; SaveParse reuses only if proven).
3. ModParse `ext-mod-tokens`. 4. SaveParse split. 5. Logtriage split. 6. Toggle split.
7. Docs/rules/memory/gitignore/DOC-INDEX. 8. Verification (plan §Verification).

## Non-actionable note
The weekly-limit refund/reset request cannot be done by Claude (no tool/capability for usage limits/billing/quotas;
needs Anthropic support / account admin).

## Naming clarification (2026-07-01) — tests are `chk-*`, not pytest
Only `lib_*` (imported by name) keep underscore. A TEST is executable, not a lib, so it is a `chk-*` script run via
`python chk-*.py` (e.g. `chk-diagnostics.py`) — NOT pytest `test_*.py`. This avoids the underscore exception for tests.

## Build status — 2026-07-01 session 1 (DONE + tested)
- ModParse `ext-mod-tokens.py` — unfiltered token dump -> raw_tokens.csv (InfraTax: 316 distinct / 12467 total).
- Logtriage Set 1 (CORE FIX): ext-log-lines + aggr-log-errorpatterns + run-log-sort -> common log-CURR/raw_errors.csv
  (6189 error lines, incl 1888 jomini/building_manager that the old triage dropped) + _global/error_patterns.csv
  (42 signatures; top = mdp_expander_decisions.txt:21 "Invalid right side during comparison 'c'" x1871 = a real bug).
- Diagnostics engine core: lib_diag (safe evaluator + fired + render_md) + chk-diagnostics (data-driven self-test 5/5)
  + diag_snippets.example.csv. config_logtriage.toml extended ([smoke] + common outputs).
- NEXT: Logtriage Set 2 (aggr-log-matches refocus + run-log-aggr -> per-mod metrics) + Set 3 wiring
  (ext-diag-eval/gen-diag-md/run-log-diag over lib_diag) + run-logtriage top; then SaveParse split; Toggle split.
