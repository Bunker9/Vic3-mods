# THE debug framework — MASTER README (canonical entry point)

> **START HERE.** This is the one doc that tells a future session HOW to USE and READ the v2 testbook debug
> frameworks. It is linked from the ceremony/rule docs (`DEV-RULES.md`, `CEREMONIES.md`, `DOC-INDEX.md`,
> `testbook/v2/README.md`). Canonical DESIGN/vision home: `hk-config/roadmap/MOD-DEBUG-FRAMEWORK.md`.
> Governing rule: DEV-RULES "THE debugging framework — do NOT author ad-hoc debug scripts" ([[the-debug-framework]]).

## What THE framework is
ALL Victoria 3 mod debugging is driven through THE framework — single-purpose frameworks over a shared
common lib, reading/writing one game-data area. **Never write a one-off debug script beside it; close gaps by
EXTENDING it generically.**

## The analysis MANDATE — what Claude DOES with the outputs (SORT, don't FILTER; attribute to a mod FEATURE)
> **"feature" is a PROTECTED word** — a real mod game-mechanic (a `testbook_status.xlsx` IDENTITY id, e.g.
> `ECO-CHAMP`), NEVER a tab / view / HTML object. Below, "feature" always means that.

Running the frameworks is not about hiding noise — it is to LIST/SORT and ATTRIBUTE:
1. **LIST/SORT every error — never FILTER.** The raw stages capture every log line + every save object; nothing
   is deleted. A "known/benign" verdict SORTS a signature, it must not hide it. (The current `smoke_detector`
   benign-suppress model VIOLATES this — flagged for rework, see TODO T107.)
2. **Go over the SAVE data blocks for feature-related content.** For any/all mod, join the persisted
   vars / modifiers / fingerprints / building + state census against each mod-FEATURE's declared tokens
   (kw / vars / modifiers / `debug_log` — the per-feature list in `v2/<Mod>/`) to judge, per feature:
   **intended-effect / side-effect / no-effect.**
3. **Attribute with a PROBABILITY.** Give an explicit confidence that an observed effect (or error) is caused by
   that mod-feature vs vanilla / another mod — not a binary. Over-build errors are attributed to the pulse/seeding
   feature that most likely caused them, NOT rubber-stamped "benign".
4. **Diagnostics are DATA, keyed to a mod-feature.** Findings come from `diag_literals` rules
   (`id, text, condition, logical_reasoning, user_comments, status` + a mod-FEATURE dimension — TODO T108), never
   hardcoded prose. Concrete save-side checks the diagnostics MUST carry: over-build of **railways**, **art
   academies**, and **light & heavy manufacturing** buildings; **market goods trading too cheap globally**; and
   **industrial / staple goods priced >25% over base**.
5. **`actinfo` is a PROTECTED SCORING WORD** — "actionable info". Every file an `aggr_*` / `diag_*` / `gen_*`
   stage produces must be SCORED on whether a human gains ACTINFO by looking at it. A generated aggr/diag with
   NO actinfo (an identical-across-mods generic boilerplate, an empty per-mod file, a mod-agnostic census
   duplicated per-mod, a bare flag) is **SLOP** by definition and must be removed or made feature-attributed.
   The bar for a per-mod file is: does it tell you something TRUE and ACTIONABLE about THAT mod's feature(s)?

```
testbook/v2/tools/
├─ Framework-common/     shared core lib (lib_*) + MASTER orchestrators (run-debug-master, run-scrub,
│                        run-archive-curr) + the mod-agnostic TOGGLE script + the GAME CONFIG (config_game.toml
│                        [gitignored, from config_game.example.toml] + config_naming.toml). THIS readme.
├─ Framework-ModParse/   mod SOURCE  → Game-<game>/data-<Mod>/   (idempotent token files; the shared upstream)
├─ Framework-Logtriage/  game LOGS + data-<Mod> → Game-<game>/log-CURR/<Mod>/
├─ Framework-SaveParse/  .v3 SAVE  + data-<Mod> → Game-<game>/save-CURR/<Mod>/
├─ Framework-Toggle/     debug/fp marker TOGGLE split — ss1-ss4 over lib_toggle (run-toggle master; per-file subs)
└─ Game-<game>/          DATA ONLY — per-run outputs (data-<Mod>/, log-CURR*/, save-CURR*/); gitignored WHOLESALE
                         at repo level, NO code/config here. Created on demand. A future PDX game = a new Game-<X>/.
```

## Framework-common — the shared core lib (`lib_*`)
Imported by every framework script. The dir name is hyphenated (consistent with the other `Framework-*`), so
it is NOT a Python package — scripts put it on `sys.path` and import the modules top-level:
```python
import os, sys
COMMON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Framework-common")
sys.path.insert(0, COMMON)
import lib_args, lib_io, lib_paths, lib_config, lib_parse
```
| module | owns |
|---|---|
| `lib_args` | the standardized CLI arg contract (below) |
| `lib_io` | deterministic text/CSV IO (`write_csv(..., sort=True)` ⇒ idempotent `data-<Mod>`) |
| `lib_paths` | self-location + ALL external path resolution from `config_game.toml`; the `data-<Mod>` / `<kind>-<label>/<mod>` output layout. The single I/O-path lib (§Z). |
| `lib_config` | read-only TOML loader (`tomllib`) |
| `lib_parse` | prefix detect · fixed-point `decode_value` · `iter_save_lines`/`iter_save_blocks` · `normalize_error` |

See `MANIFEST.md` for the full module + master-script registry.

## Standard arg contract (every script, via `lib_args`)
| arg | kind | meaning |
|---|---|---|
| `MOD_NAME` | positional — SUB-scripts take exactly ONE; the 4 MASTERS take one or MORE (looped per mod) | output namespace under `Game-<game>/` |
| `--all` | masters only | run for EVERY mod in `config_game.toml [mod_locations]` |
| `--path DIR` | masters (ModParse/debug-master; single MOD_NAME only) — subs take it as positional arg2 `MOD_PATH` | mod source folder; else from `config_game.toml [mod_locations]` |
| `--save PATH` | SaveParse only | a specific `.v3`; else newest in the save-games dir |
| `--logs DIR` | Logtriage only | override the Vic3 logs dir |
| `--prefix P` | all | override the auto-derived mod prefix/abbr |
| `--rerun` | all | force rebuild/re-scan (else reuse if present) |

## MASTER orchestrators (run these) — **built 2026-06-30**
| script | what it does | example |
|---|---|---|
| `run-debug-master.py <MOD> [--save F] [--logs D]` | the whole flow: ModParse → Logtriage → SaveParse for one mod; prints the 3 `diagnostics.md` paths | `python Framework-common/run-debug-master.py NoUSChickenMod` |
| `run-scrub.py [--mod M] [--commit]` | wipe ALL generated data (`Game-<game>/data-*`, `log-CURR*`, `save-CURR*`), leaving CODE + configs + the tracked `*.example.csv` seeds. **Dry-run by default**; `--commit` actually deletes | `python Framework-common/run-scrub.py --commit` |

**Integration (decided 2026-06-30):** the masters STAY inside the framework folders. The v2 report build
(`run_v2.py` validate) and the future CI/CD pipeline invoke these masters IN-PLACE to (re)generate the per-run
outputs that feed the plug-and-play HTML components — the masters are the single integration entry point (no
duplicate launch logic in the report or CI).

You can also run any framework standalone: `Framework-ModParse/run-modparse.py <MOD> <PATH>`,
`Framework-Logtriage/run-logtriage.py <MOD>`, `Framework-SaveParse/run-saveparse.py <MOD>`.

**Newest-only CURR:** as their STEP 1, `run-logtriage` / `run-saveparse` invoke
`Framework-common/run-archive-curr.py` to strip the `CURR` marker from every prior `log-CURR*` / `save-CURR*`
dir (and CREATE the `Game-<game>/` data root if missing), so the just-created run is the SOLE `*-CURR` folder —
the marker the report/unit-test layer uses to find the latest data source.

## How to USE THE framework (the analysis flow — vision §C)
1. **`run-modparse <MOD> <PATH>`** → `Game-<game>/data-<Mod>/` (all tokens/filenames/kw/fp; idempotent).
2. **Run the game SHORT (1–3 months)** with a fresh versiontest log — FIRST do the pre-game ceremony (log
   clear + version bump; see WHERE-map). Then play, quit.
3. **`run-logtriage <MOD>`** + **`run-saveparse <MOD>`** (or just `run-debug-master <MOD>`) →
   `log-CURR/` / `save-CURR/` with `diagnostics.md` + CSVs.
4. **Read the diagnostics** (below). For feature PASS/FAIL, the deferred BDD layer (pytest-bdd) consumes these.

## How to READ / ANALYSE the outputs
- **Logtriage (SORT-not-FILTER, reworked 2026-07-02)** — `log-CURR/` ROOT holds the COMMON pool (EVERY log
  line + every error, nothing dropped); `_global/` = grouped error signatures + the smoke-detector verdict
  metrics + a global `diagnostics.md`; `<Mod>/` = matches over the pool, markers **fired vs unfired**
  (unfired marker = that effect/decision never ran; ≥100× = possible re-fire loop), loc-for-all-kw, and a
  per-mod `diagnostics.md`. Findings text is DATA (`diag_literals`); noise triage is the curated
  `smoke_detector` (Y=noise, N=tracked, blank=review me — new signatures auto-append). NO mention of a mod
  kw in the logs is usually GOOD; an unfired marker is usually BAD (code path didn't run).
- **SaveParse `diagnostics.md` + CSVs** — which `*_fingerprint_*` vars/modifiers **persisted** and on WHICH
  object (`doc_path`), with decoded values/dates; the **state/building census**; and **over-cap** tuples
  classified mod-script-error vs engine-overbuild. A fingerprint that is ABSENT from the save = its feature
  likely didn't fire (or the fp/debug lines are toggled OFF — see toggle script).
- `data-<Mod>/` is the idempotent inventory of everything the mod declares (the join keys).

## WHERE-map — every debug / test / ceremony script and its home
| script / job | home | game-specific? | status |
|---|---|---|---|
| shared lib (`lib_*`) | `Framework-common/` | no | built |
| master run-all (`run-debug-master.py`) | `Framework-common/` | no | built |
| **cleanup / scrub** (`run-scrub.py`) | `Framework-common/` | no | built |
| **comment / fingerprint TOGGLE** (debug_log + `_fingerprint_` on/off, mod-agnostic) | `Framework-Toggle/` (ss1–ss4 over `lib_toggle`: `run-toggle` master + per-file subs) | no | built (interim `testbook-toggle-markers` RETIRED 2026-07-03) |
| **KEEP-newest-CURR** (`run-archive-curr.py`; STEP 1 of log/save masters, standalone; creates Game-<game>/ if missing) | `Framework-common/` | no | built 2026-07-01 |
| ModParse / Logtriage / SaveParse jobs | `Framework-*/` | no (logic) | built (reworked: parse-once + SORT-not-FILTER Sets) |
| game/machine CONFIG (`config_game.toml` + `.example` + `config_naming.toml`) | `Framework-common/` | YES (values) | built |
| per-run DATA (`data-<Mod>/`, `log-CURR*/`, `save-CURR*/`) | `Game-<game>/` (gitignored wholesale) | n/a (data) | built |
| **pre-game version-bump + LOG-CLEANUP** (fresh versiontest log before a run) | `hk-config/scripts/envSetup_pre_game_launch.ps1` + `clear-vic3-logs.ps1` | YES | exists in hk-config (Game-<game>/ is data-only, so game CODE cannot live there); a dedicated game-code home = a flagged follow-up |
| pre-dev preflight / promote (debug on/off, versiontest enable) | `hk-config/scripts/predev_preflight.ps1` | YES | exists (ceremony) |

> The toggle script's home moved to `Framework-common` (mod-agnostic) per the 2026-06-30 refinement; this
> supersedes the earlier "hk-config/scripts" note. The pre-game LOG-CLEANUP + version-bump are GAME-specific
> (Vic3 launcher/logs/versiontest); since `Game-<game>/` is DATA-ONLY (no code/config), they stay in the
> Ceremony-2 PowerShell in hk-config (wired into `CEREMONIES.md` + the launcher). A future game-specific CODE
> home (distinct from the data folder) is a confirm-first follow-up, not silently done here.

## Pointers
Design/vision: `hk-config/roadmap/MOD-DEBUG-FRAMEWORK.md`. Rules: DEV-RULES "THE debugging framework",
"Save-fingerprint debugging", "Debug & fingerprint variable standardization". Per-framework contracts:
`Framework-{ModParse,Logtriage,SaveParse}/README.md` + their `MANIFEST.md`. Game config:
`Framework-common/config_game.example.toml` (the `Game-<game>/` folder is a gitignored, code-free data sink).
