# Testbook v2 — xlsx-driven, self-contained report

v2 assembles one `MAIN-<branch>-testing.html` from the **feature taxonomy in
`hk-config/data/testbook_status.xlsx`**. It imports nothing from the v1 testkit — all check
logic lives under `v2/testkit/`.

> **"feature" is a PROTECTED WORD** = the smallest independently testable mod game mechanic
> (a function of the mod you develop), enumerated in the xlsx IDENTITY (`mod`, `feature`, `id`,
> e.g. `ECO-YEARLY`). It is NOT a tab, view, panel, or HTML object. See DEV-RULES.

## One command

```
python testbook/v2/run_v2.py            # all mods   (or run.bat / run.sh)
python testbook/v2/run_v2.py ModName    # one mod
python testbook/v2/run_v2.py --open     # build + open in browser
```

`manifest.json` is **generated** from the xlsx — do not hand-edit it. After editing the tracker:

```
python testbook/v2/testkit/gen_manifest_from_xlsx.py
```

## Two kinds of rendered unit (both are "cards")

- **VIEW** (mod-wide) — `static` / `log`. Generic analyzers, **not features**. Output under
  `v2/<Mod>/_modwide/<view>/`. Rendered as `data-view` cards. Static = encoding/brace/quote;
  Log = errors + the health badges (lines emitted + errors).
- **FEATURE** (per mod) — a real mechanic named by the xlsx **id**. If `v2/<Mod>/<ID>/extract.py`
  exists it is run and rendered (`data-feature` card); otherwise a **stub** card shows its xlsx
  metadata (markers, status) as "extractor pending". A feature appears on every tab in its
  WHERE-TO-DISPLAY list; per-tab output is `component_<tab>.html` (a single `component.html`
  serves the feature's first tab).

## Layout

```
v2/
├─ run_v2.py            orchestrator: read manifest -> run views+features -> assemble report
├─ run.bat / run.sh     one-click launchers
├─ manifest.json        GENERATED from testbook_status.xlsx (tabs + per-mod features/views)
├─ tools/               THE debug framework (Framework-common + ModParse/Logtriage/SaveParse + Game-Victoria3)
├─ testkit/             shared library + analyzers + extractors (flat, class-prefixed; no v1 imports)
│  ├─ gen_manifest_from_xlsx.py   the manifest generator (tab normalization heuristic lives here)
│  ├─ lib_components.py   CSS/JS + helpers: tbl (ptable), xtable, badge, card/stub, write_component
│  ├─ lib_buildstamp.py · lib_paths.py    (build-stamp label · resolve_logs_dir)
│  ├─ chk_structure.py · chk_standards.py  static checks on mod files
│  ├─ chk-mods-have-metadata.py  repo-level guard: every mod folder MUST have .metadata/metadata.json
│  │                     (closes the CI hole where a metadata-less mod is silently skipped;
│  │                     wire into static-checks.yml via a UI edit: `python _harness/v2/testkit/chk-mods-have-metadata.py .`)
│  ├─ parse_log.py · parse_timeline.py     game-log parsers
│  └─ ext_static.py · ext_log.py           generic VIEW extractors (the mod-wide views)
└─ <Mod>/
   ├─ _modwide/<view>/    generated static + log view outputs (gitignored)
   └─ <FEATURE-ID>/       a feature (e.g. ECO-YEARLY/): extract.py + data*/aggr*/seed* +
                          component[_<tab>].html (generated, gitignored)
```

## THE debug framework (`tools/`) — 4 frameworks + a shared core + a game data area

> **REWORK Phases 1-4 DONE (2026-07-01 → 07-03): Logtriage SORT-not-FILTER Sets 1-3 + SaveParse parse-once
> Sets 1-3 (incl. market/goods prices) + Framework-Toggle ss1-ss4 split; old jobs (`anal-log-triage`,
> `aggr-state-census`+`anal-save-report`, interim `testbook-toggle-markers`) retired. Phase 5 sweep in tail.** The
> frameworks sit over a shared `Framework-common/`, all literals/paths in TOML configs + curated CSVs.
> **Usage cookbook: `Framework-common/HOW_TO_USE.md`.** Canonical design: `hk-config/roadmap/
> MOD-DEBUG-FRAMEWORK.md` + `hk-config/roadmap/ROADMAP-debug-framework-rework.md` (design docs live in
> hk-config, never here — DEV-RULES "Testbook docs are USAGE-ONLY"). Governing rule: DEV-RULES "THE debugging
> framework — do NOT author ad-hoc debug scripts" ([[the-debug-framework]]).

All mod debugging is driven through THE framework (run the jobs, read their `diagnostics.md`/CSVs); gaps are
closed by EXTENDING it generically, never by a one-off script beside it. Each script is modular (`run_*` master
+ `ext_*`/`aggr_*`/`anal_*` subs over `Framework-common`), config-driven, and follows the arg contract `arg1=MOD_NAME`,
`arg2=MOD_PATH`.

- **`Framework-common/`** — the ONE shared core lib (args · io · paths · config · parse) + the master
  orchestrators + the toggle script + the usage cookbook (`HOW_TO_USE.md`).
- **`Framework-ModParse/`** — mod SOURCE → `data-<Mod>` token files (IDEMPOTENT); the shared upstream both
  downstream frameworks consume. `run-modparse.py <MOD> <PATH>`.
- **`Framework-Logtriage/`** — game LOGS → `log-CURR/` (SORT-not-FILTER: COMMON raws of EVERY line at ROOT,
  per-mod matches/markers/metrics, data-driven diagnostics via `smoke_detector` + `diag_literals` curated
  CSVs). Run BEFORE any manual log deep-dive. `run-logtriage.py [<MOD>... | --all]` (none = config_logmods).
- **`Framework-SaveParse/`** — `.v3` SAVE + `data-<Mod>` → `save-CURR/` (parse-once: COMMON pool of manager
  raws + ALL persisted vars/modifiers + market goods PRICES + goods catalog + census; per-mod fingerprints,
  T101 over-cap verdicts, metrics, diagnostics via the shared engine). The save is never re-read per mod.
  `run-saveparse.py [<MOD>... | --all]`.
- **`Framework-Toggle/`** — debug/fp marker toggle SPLIT (ss1–ss4 over `lib_toggle`): `run-toggle.py` master
  (target = file / mod folder / `--mod`) + independently-runnable per-file subs `ext-toggle-markers` (find),
  `run-toggle-file` (toggle one file), `chk-toggle-scopes` (brace + empty-scope check). Comments/uncomments
  `debug_log`/`_fingerprint_` lines + fp-only scope wrappers; BOM + line endings preserved; `--commit` to write.
- **`Game-Victoria3/`** — **DATA ONLY**: per-run outputs (`data-<Mod>/`, `log-CURR*/`, `save-CURR*/`), gitignored
  WHOLESALE at repo level (`tools/Game-*/`), NO code/config here (created on demand by the masters). The game
  CONFIG (`config_game.example.toml`, `config_naming.toml`, gitignored per-machine `config_game.toml`) lives in
  `Framework-common/`. A future PDX game = a new `Game-<X>/` data folder.
- **`run-debug-master.py`** (in `Framework-common/`) — runs ModParse → Logtriage → SaveParse end-to-end for a mod.
- **`run-scrub.py`** (in `Framework-common/`) — wipes ALL generated data, leaving code + configs only (dry-run
  default, `--commit`).

Each framework folder has its own `README.md` (contract) + `MANIFEST.md` (every script registered).
Method for the fingerprint markers themselves: DEV-RULES "Save-fingerprint debugging" + "Debug & fingerprint
variable standardization". **DEFERRED (designed, not yet built):** a pytest-bdd BDD layer, plug-and-play v2 HTML
components fed by the jobs' `diagnostics.md`/CSVs, and CI.

## Canonical tabs

`static` Static Checks · `log` Log · `census` Census / State · `modifier` Modifiers ·
`timeline` Timeline · `diplo` Diplomacy · `config` Config · `bdd` BDD · `errors` Errors.

## Global "Errors" view (game-wide cpp error capture)

`static` and `log` are **per-mod** views. The **Errors** tab is a **GLOBAL framework view** rendered
ONCE (not per mod): the engine's cpp `error.log` groups errors by the *vanilla* file that threw them
(e.g. `_ship_transfer.txt`, `command_values.txt`, the canton/sakoku trade-center tooltips) — they
carry no mod marker, so they cannot be attributed per mod the way `log` markers are.

- `testkit/parse_errors.py` — parses `error.log` into grouped signatures: count, a raw snippet, the
  referenced script file, and a **relevance class**: `mod-data` (a mod's seeded data tripped a
  vanilla evaluation, e.g. trade centers under canton/sakoku) · `mod-script` (a path under one of
  our mods) · `vanilla?` (vanilla file, but **possibly mod-amplified** — more wars/naval units →
  more `_ship_transfer`/naval errors) · `uncertain`. The `vanilla?` flag is deliberate: a vanilla
  `script_value` div/0 CAN be triggered by mod code that breaks a game rule, so these are surfaced
  for human judgement, not auto-dismissed.
- `testkit/ext_errors.py` — renders that into the Errors panel (`v2/_global/errors/`), wired into
  `run_v2.py` as a framework tab (not from the xlsx, since it is not a per-mod feature).

The xlsx `tab/visual` cell is free-text; `gen_manifest_from_xlsx.py` normalizes it to these ids
(split on `+` / `/`, keyword match). **That mapping is the one heuristic — review it in the
generator** if a feature lands on the wrong tab.

## Implemented so far

- Views: `static`, `log` for every mod (log shows the emitted/errors health badges).
- Features: `ECO-YEARLY` (eco placements by year+state, Timeline) and `MDP-BLOB` (wars +
  claims/homelands, Timeline). The other 33 features are xlsx-declared **stubs** — the report is
  a live coverage map; each lights up when its `<Mod>/<ID>/extract.py` is written.

## Adding / implementing

- **Add a feature**: add a row to `testbook_status.xlsx` (mod, feature, id, tab, markers) and
  re-run the generator — it appears as a stub immediately.
- **Implement it**: create `v2/<Mod>/<ID>/extract.py` with a `run(feature_dir, logs_dir)` that
  imports `lib_components` (+ a shared analyzer like `parse_timeline`) and calls
  `fb.write_component(...)`. Re-run `run_v2.py`.

## eco-STATE note

`timeline.py` reads the placement state from the `debug_log_scopes` dump the mod already emits
(`[...]: State <name>` This-scope, `Root: Country <name>`); each `ECO_PLACED` marker is parked
and bound to the next scope dump, so placements get the right state with no mod change.
