# THE debug framework — MASTER README (canonical entry point)

> **START HERE.** This is the one doc that tells a future session HOW to USE and READ the v2 testbook debug
> frameworks. It is linked from the ceremony/rule docs (`DEV-RULES.md`, `CEREMONIES.md`, `DOC-INDEX.md`,
> `testbook/v2/README.md`). Canonical DESIGN/vision home: `hk-config/roadmap/MOD-DEBUG-FRAMEWORK.md`.
> Governing rule: DEV-RULES "THE debugging framework — do NOT author ad-hoc debug scripts" ([[the-debug-framework]]).

## What THE framework is
ALL Victoria 3 mod debugging is driven through THE framework — three single-purpose frameworks over a shared
common lib, reading/writing one game-data area. **Never write a one-off debug script beside it; close gaps by
EXTENDING it generically.**

```
testbook/v2/tools/
├─ Framework-common/     shared core lib (lib_*) + the MASTER orchestrators (run-debug-master, run-scrub) + the
│                        mod-agnostic comment/fingerprint TOGGLE script. THIS readme.
├─ Framework-ModParse/   mod SOURCE  → Game-<game>/data-<Mod>/   (idempotent token files; the shared upstream)
├─ Framework-Logtriage/  game LOGS + data-<Mod> → Game-<game>/log-CURR-<run>/<Mod>/
├─ Framework-SaveParse/  .v3 SAVE  + data-<Mod> → Game-<game>/save-CURR-<save>/<Mod>/
└─ Game-Victoria3/       GAME-SPECIFIC config (config_game.toml [gitignored], config_naming.toml) + per-run DATA
                         (gitignored). A future PDX game = a new Game-<X>/. See Game-Victoria3/README.md.
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
| `MOD_NAME` | positional arg1 (always) | output namespace under `Game-<game>/` |
| `MOD_PATH` | positional arg2 (ModParse only) | mod source folder; else from `config_game.toml [mod_locations]` |
| `--save PATH` | SaveParse only | a specific `.v3`; else newest in the save-games dir |
| `--logs DIR` | Logtriage only | override the Vic3 logs dir |
| `--prefix P` | all | override the auto-derived mod prefix/abbr |
| `--rerun` | all | force rebuild/re-scan (else reuse if present) |

## MASTER orchestrators (run these) — **built 2026-06-30**
| script | what it does | example |
|---|---|---|
| `run-debug-master.py <MOD> [--save F] [--logs D]` | the whole flow: ModParse → Logtriage → SaveParse for one mod; prints the 3 `diagnostics.md` paths | `python Framework-common/run-debug-master.py NoUSChickenMod` |
| `run-scrub.py [--mod M] [--commit]` | wipe ALL generated data (`Game-<game>/data-*`, `log-CURR-*`, `save-CURR-*`), leaving CODE + configs + `benign.csv`. **Dry-run by default**; `--commit` actually deletes | `python Framework-common/run-scrub.py --commit` |

**Integration (decided 2026-06-30):** the masters STAY inside the framework folders. The v2 report build
(`run_v2.py` validate) and the future CI/CD pipeline invoke these masters IN-PLACE to (re)generate the per-run
outputs that feed the plug-and-play HTML components — the masters are the single integration entry point (no
duplicate launch logic in the report or CI).

You can also run any framework standalone: `Framework-ModParse/run-modparse.py <MOD> <PATH>`,
`Framework-Logtriage/run-logtriage.py <MOD>`, `Framework-SaveParse/run-saveparse.py <MOD>`.

## How to USE THE framework (the analysis flow — vision §C)
1. **`run-modparse <MOD> <PATH>`** → `Game-<game>/data-<Mod>/` (all tokens/filenames/kw/fp; idempotent).
2. **Run the game SHORT (1–3 months)** with a fresh versiontest log — FIRST do the pre-game ceremony (log
   clear + version bump; see WHERE-map). Then play, quit.
3. **`run-logtriage <MOD>`** + **`run-saveparse <MOD>`** (or just `run-debug-master <MOD>`) →
   `log-CURR-*` / `save-CURR-*` with `diagnostics.md` + CSVs.
4. **Read the diagnostics** (below). For feature PASS/FAIL, the deferred BDD layer (pytest-bdd) consumes these.

## How to READ / ANALYSE the outputs
- **Logtriage `diagnostics.md`** — markers **fired vs unfired** (an unfired `debug_log` marker = that
  effect/decision never ran; ≥100× = a possible re-fire loop), mod-attributable **errors** (benign-suppressed
  via the shared `benign.csv`), and **loc-for-all-kw** misses. NO mention of a mod kw in the logs is usually
  GOOD (no error); an unfired marker is usually BAD (code path didn't run).
- **SaveParse `diagnostics.md` + CSVs** — which `*_fingerprint_*` vars/modifiers **persisted** and on WHICH
  object (`doc_path`), with decoded values/dates; the **state/building census**; and **over-cap** tuples
  classified mod-script-error vs engine-overbuild. A fingerprint that is ABSENT from the save = its feature
  likely didn't fire (or the fp/debug lines are toggled OFF — see toggle script).
- `data-<Mod>/` is the idempotent inventory of everything the mod declares (the join keys).

## WHERE-map — every debug / test / ceremony script and its home
| script / job | home | game-specific? | status |
|---|---|---|---|
| shared lib (`lib_*`) | `Framework-common/` | no | built (Phase 1) |
| master run-all (`run-debug-master.py`) | `Framework-common/` | no | Phase 5 |
| **cleanup / scrub** (`run-scrub.py`) | `Framework-common/` | no | Phase 5 |
| **comment / fingerprint TOGGLE** (debug_log + `_fingerprint_` + dummy-use on/off, mod-agnostic) | `Framework-common/` | no | Phase 6 |
| ModParse / Logtriage / SaveParse jobs | `Framework-*/` | no (logic) | Phases 2–4 |
| game/machine config + per-run data | `Game-Victoria3/` | YES | configs built |
| **pre-game version-bump + LOG-CLEANUP** (fresh versiontest log before a run) | TARGET `Game-Victoria3/`; CURRENTLY the pre-game ceremony `hk-config/scripts/envSetup_pre_game_launch.ps1` + `clear-vic3-logs.ps1` | YES | exists in hk-config; relocation = a flagged follow-up (CEREMONIES + launcher reference it — confirm before moving) |
| pre-dev preflight / promote (debug on/off, versiontest enable) | `hk-config/scripts/predev_preflight.ps1` | YES | exists (ceremony) |

> The toggle script's home moved to `Framework-common` (mod-agnostic) per the 2026-06-30 refinement; this
> supersedes the earlier "hk-config/scripts" note. The pre-game LOG-CLEANUP + version-bump are GAME-specific
> (Vic3 launcher/logs/versiontest) and belong under `Game-Victoria3/`, but they currently live as the Ceremony-2
> PowerShell in hk-config and are wired into `CEREMONIES.md` + the launcher — moving them is a separate,
> confirm-first task, not silently done here.

## Pointers
Design/vision: `hk-config/roadmap/MOD-DEBUG-FRAMEWORK.md`. Rules: DEV-RULES "THE debugging framework",
"Save-fingerprint debugging", "Debug & fingerprint variable standardization". Per-framework contracts:
`Framework-{ModParse,Logtriage,SaveParse}/README.md` + their `MANIFEST.md`. Game specifics:
`Game-Victoria3/README.md`.
