# HOW_TO_USE — running THE debug framework (master scripts + config reference)

> **Companion to `README.md`** (the conceptual master README). This file is the practical cookbook: every
> master script, every invocation form with a REAL mod name, and exactly which config file to edit (and what to
> change) for each. Config edits are shown as fenced code blocks **headed with the file path** so it is obvious
> the snippet belongs in a *different* file, not in the shell.
>
> Naming: scripts are hyphenated CODE names (`run-debug-master.py`), configs/data are underscore names
> (`config_game.toml`), folders are hyphenated (`Framework-common`) — per DEV-RULES "Naming conventions".

## Where to run from
Every script self-locates (`__file__`), so it runs from any directory. All examples below assume your shell is
in the tools root:

```
cd testbook/v2/tools
```

Paths in this doc are written **from `tools/` onwards** (e.g. `Framework-common/config_game.toml` =
`testbook/v2/tools/Framework-common/config_game.toml`).

---

## 0. ONE-TIME SETUP — `config_game.toml` (the only per-machine file)

`Framework-common/config_game.toml` is **gitignored** (it holds machine-absolute paths that may contain your OS
username — PII). It does not exist on a fresh clone; copy the tracked template and fill it in:

```
cp Framework-common/config_game.example.toml Framework-common/config_game.toml
```

Then edit it. Blank a value (`""`) to let the framework auto-resolve it from `<Documents>/Paradox
Interactive/Victoria 3/`; set `[mod_locations]` so the scripts can find a mod by NAME without you passing its
folder as arg2:

```toml
# testbook/v2/tools/Framework-common/config_game.toml   (copy of config_game.example.toml; GITIGNORED)
game_files_path = ""        # unpacked vanilla game files (token verification); blank = not needed here
logs_dir        = ""        # blank => auto <Documents>/Paradox Interactive/Victoria 3/logs
save_games_dir  = ""        # blank => auto <Documents>/Paradox Interactive/Victoria 3/save games

[mod_locations]
NoUSChickenMod   = "C:/Users/<you>/Projects/victoria-3-mod/mod1-inov/NoUSChickenMod"
MyDiploPlayMod   = "C:/Users/<you>/Projects/victoria-3-mod/mod1/MyDiploPlayMod"
Top40EcoBoostMod = "C:/Users/<you>/Projects/victoria-3-mod/mod1/Top40EcoBoostMod"
KampaiNipponMod  = "C:/Users/<you>/Projects/victoria-3-mod/mod1-inov/KampaiNipponMod"
```

Use forward slashes. Once `[mod_locations]` is set, ModParse/toggle find a mod by name alone; otherwise pass the
mod folder explicitly (arg2 / `--path`).

---

## The standard arg contract (the 4 framework masters)

`run-debug-master`, `run-modparse`, `run-logtriage`, `run-saveparse` share one contract (via `lib_args`):

| arg | kind | meaning |
|---|---|---|
| `MOD_NAME` | positional arg1 (always required) | output namespace under `Game-Victoria3/` |
| `MOD_PATH` | positional arg2 (ModParse + debug-master) | mod source folder; else from `config_game.toml [mod_locations]` |
| `--save PATH` | SaveParse + debug-master | a specific `.v3`; else newest in the save-games dir |
| `--logs DIR` | Logtriage + debug-master | override the Vic3 logs dir |
| `--prefix P` | all four | override the auto-derived mod prefix/abbr (e.g. `nous`) |
| `--rerun` | all four | force rebuild/re-scan (else reuse outputs if already present) |

> `run-scrub` and `testbook-toggle-markers` (both in `Framework-common`) are utilities, **not** part of this
> contract — they take **no `MOD_NAME` positional**; they scope with `--mod`/`--path`. See §5–§6.

`MOD_NAME` is any of the real mods: `NoUSChickenMod`, `MyDiploPlayMod`, `Top40EcoBoostMod`, `KampaiNipponMod`,
`DesiStrategyMod`, `ExpFightMod`, `ExpMktAccessMod`, `InfraTaxMod`, `PvtCapCtrlMod`, `versiontestMod`.

---

## 1. `run-debug-master.py` — the whole flow (ModParse → Logtriage → SaveParse)
Home: `Framework-common/`. Runs all three frameworks in order for one mod, then prints the three output paths.
This is the single entry point the v2 report build + CI invoke.

```
# mod folder resolved from config_game.toml [mod_locations]:
python Framework-common/run-debug-master.py NoUSChickenMod

# mod folder given explicitly as arg2 (no [mod_locations] entry needed):
python Framework-common/run-debug-master.py MyDiploPlayMod "C:/Users/<you>/Projects/victoria-3-mod/mod1/MyDiploPlayMod"

# point at a specific save + a specific logs dir, force a clean re-scan:
python Framework-common/run-debug-master.py Top40EcoBoostMod --save "C:/path/TEST_ME.v3" --logs "C:/path/logs" --rerun

# override the auto-detected prefix (if detection picks a vanilla word):
python Framework-common/run-debug-master.py KampaiNipponMod --prefix knip
```

Outputs (printed at the end):
- `Game-Victoria3/data-<MOD>/` — the idempotent token inventory
- `Game-Victoria3/log-CURR/<MOD>/diagnostics.md`
- `Game-Victoria3/save-CURR/<MOD>/diagnostics.md`

Configs it reads (transitively, via the three sub-frameworks): `config_game.toml`, `config_modparse.toml`,
`config_logtriage.toml` + `benign.csv`, `config_saveparse.toml`.

---

## 2. `run-modparse.py` — mod SOURCE → `data-<Mod>/` (run this FIRST)
Home: `Framework-ModParse/`. Builds the idempotent `data-<Mod>/raw_*.csv` token files that BOTH downstream
frameworks read. Must run before Logtriage/SaveParse. Byte-identical across reruns for the same source.

```
# resolve folder from config:
python Framework-ModParse/run-modparse.py NoUSChickenMod

# explicit folder (arg2):
python Framework-ModParse/run-modparse.py DesiStrategyMod "C:/Users/<you>/Projects/victoria-3-mod/mod1-inov/DesiStrategyMod"

# force a rebuild + pin the prefix:
python Framework-ModParse/run-modparse.py MyDiploPlayMod --prefix mdp --rerun
```

Output: `Game-Victoria3/data-<MOD>/` → `raw_files.csv`, `raw_keywords.csv`, `raw_debuglines.csv`,
`raw_loc.csv`, `raw_fingerprints.csv`.

**Config — `Framework-ModParse/config_modparse.toml`.** Tune scanned file types, the fingerprint infix, the
prefix-detection stopwords (vanilla words that must NOT win auto-detection), or the output filenames:

```toml
# testbook/v2/tools/Framework-ModParse/config_modparse.toml
[scan]
extensions = [".txt", ".yml", ".yaml", ".gui", ".json"]   # add an extension here to scan it

[prefix]
# if a mod's real short prefix is being shadowed by a vanilla command word, add that word here:
stopwords = ["add", "set", "has", "building", "country", "state", "modifier", "..."]
```

---

## 3. `run-logtriage.py` — game LOGS + `data-<Mod>` → `log-CURR/<Mod>/`
Home: `Framework-Logtriage/`. Scans `error.log` / `debug.log` / `game.log` against the mod's join keys; reports
markers **fired vs unfired**, mod-attributable errors (benign-suppressed), and loc-for-all-kw misses. **Run this
BEFORE any manual log deep-dive** (DEV-RULES "Triage framework FIRST"). Needs ModParse to have run.

```
# default logs dir (auto-resolved from config_game.toml / Documents):
python Framework-Logtriage/run-logtriage.py NoUSChickenMod

# override the logs dir (e.g. an archived run) + force re-scan:
python Framework-Logtriage/run-logtriage.py Top40EcoBoostMod --logs "C:/path/to/logs" --rerun
```

Output: `Game-Victoria3/log-CURR/<MOD>/` → `diagnostics.md` + `aggr_log_matches.csv` + `aggr_markers_status.csv`.

**Config — `Framework-Logtriage/config_logtriage.toml`.** Change which log files are scanned (and their
severity), the re-fire-loop threshold, or the benign-noise catalog:

```toml
# testbook/v2/tools/Framework-Logtriage/config_logtriage.toml
[logs]
files = [["error.log", "error"], ["debug.log", "debug"], ["game.log", "info"]]
[analysis]
refire_flag = 100        # a marker hit-count above this flags a suspected re-fire loop
[benign]
file = "benign.csv"      # the shared human-curated benign-error catalog (next file)
```

**Benign-error allowlist — `Framework-Logtriage/benign.csv`** (columns `human_agreed,pattern,count`). Add a row
to suppress a known, agreed-benign error from the verdict:

```csv
# testbook/v2/tools/Framework-Logtriage/benign.csv
human_agreed,pattern,count
Y,should be in utf8-bom encoding,0
Y,<a substring of the benign error line you want to ignore>,0
```

---

## 4. `run-saveparse.py` — `.v3` SAVE + `data-<Mod>` → `save-CURR/<Mod>/`
Home: `Framework-SaveParse/`. Reads which `*_fingerprint_*` vars/modifiers PERSISTED and on which object, the
state/building census, and over-cap tuples (mod-script-error vs engine-overbuild). Needs ModParse to have run.
**The save must be TEXT/melted** — a binary/ironman `.v3` parses to mojibake (0 rows).

```
# newest *.v3 in the save-games dir:
python Framework-SaveParse/run-saveparse.py NoUSChickenMod

# a specific (melted) save, force re-scan:
python Framework-SaveParse/run-saveparse.py KampaiNipponMod --save "C:/path/TEST_ME.v3" --rerun
```

Output: `Game-Victoria3/save-CURR/<MOD>/` → `diagnostics.md` + `aggr_save_matches.csv` +
`aggr_state_census.csv` + `aggr_census_overbuild.csv`.

**Config — `Framework-SaveParse/config_saveparse.toml`.** Change the fixed-point factor, the generic cap-var
detection regex, or which buildings are stored-cap vs trigger-gated:

```toml
# testbook/v2/tools/Framework-SaveParse/config_saveparse.toml
[decode]
fixed_point_factor = 100000          # Vic3 stores numeric vars as int(real * factor)
[census]
cap_var_pattern = "_cap(_|$)"        # a persisted state/region var matching this = the mod's numeric cap
manufacturing_capped = ["building_steel_mills", "..."]   # buildings compared vs the stored cap
trigger_capped       = ["building_railway", "building_power_plant", "..."]  # no stored cap -> reported MISSING-CAP
```

---

## 5. `run-scrub.py` — wipe regenerable per-run DATA (cleanup)
Home: `Framework-common/`. Deletes generated `data-*` / `log-CURR*` / `save-CURR*` dirs under `Game-Victoria3/`,
leaving CODE + the tracked configs + `benign.csv`. **Dry-run by default; `--commit` actually deletes.** Takes
**no `MOD_NAME` positional** — scope with `--mod`.

```
# preview EVERYTHING that would be deleted (safe, no deletion):
python Framework-common/run-scrub.py

# actually delete all generated data:
python Framework-common/run-scrub.py --commit

# scope to one mod's outputs only:
python Framework-common/run-scrub.py --mod NoUSChickenMod --commit
```

---

## 6. `testbook-toggle-markers.py` — flip debug_log + fingerprints ON/OFF (mod-agnostic)
Home: `Framework-common/`. Comments (`--off`) or uncomments (`--on`) every `debug_log` / `debug_log_scopes` /
`_fingerprint_` line across mod source `.txt`. **Dry-run by default; `--commit` rewrites** (BOM + line endings
preserved). `--on`/`--off` is required and mutually exclusive. Takes **no `MOD_NAME` positional**; scope with
`--mod` (a `[mod_locations]` key) or `--path` (explicit folder). Without either it toggles ALL configured mods.

```
# preview turning markers OFF across every configured mod:
python Framework-common/testbook-toggle-markers.py --off

# turn markers ON for one mod and apply:
python Framework-common/testbook-toggle-markers.py --on --mod MyDiploPlayMod --commit

# target a folder not in config:
python Framework-common/testbook-toggle-markers.py --off --path "C:/Users/<you>/Projects/victoria-3-mod/mod1/Top40EcoBoostMod" --commit
```

> **Promote / Ceremony 3 = `--off --commit`** across all mods, then verify ZERO active `debug_log` /
> `_fingerprint_` lines remain (DEV-RULES "Save-fingerprint debugging" promote discipline).

**Config — `Framework-common/config_toggle.toml`.** Change the comment marker, the line patterns, or which file
types are touched:

```toml
# testbook/v2/tools/Framework-common/config_toggle.toml
[toggle]
comment_marker = "#"
patterns = ['^\s*debug_log(_scopes)?\s*=', '_fingerprint_']   # add a regex to toggle more line kinds
extensions = [".txt"]                                          # loc .yml is intentionally never toggled
```

---

## 7. `run-archive-curr.py` — keep the `CURR` marker on ONLY the newest run
Home: `Framework-common/` (beside `run-scrub`). **Runs automatically as STEP 1 of `run-logtriage` and
`run-saveparse`** — you rarely call it by hand. It first CREATES the `Game-<game>/` data root if missing (it is
gitignored, so absent on a fresh clone / after scrub), then strips `CURR` from every prior `log-CURR*` /
`save-CURR*` dir (`log-CURR` → `log-<mtime>`, `log-CURR-<label>` → `log-<label>`) so that after the master
creates the fresh `<kind>/`, exactly one folder bears `CURR` — the marker the report / unit-test layer uses to
locate the latest data source. Idempotent.

```
# standalone (e.g. to tidy leftover CURR dirs without a full run):
python Framework-common/run-archive-curr.py log-CURR
python Framework-common/run-archive-curr.py save-CURR
```

> **Multi-mod note:** each `run-logtriage` / `run-saveparse` invocation resets `CURR` to the mod it just ran.
> If you analyse several mods in one sitting, only the LAST keeps `CURR`; earlier mods are archived under their
> own `log-<ts>/<Mod>/`. (If you want all mods from one game session to share a single `CURR`, that's a
> session-aware variant — ask and it can be added.)

---

## Other config files (rarely edited)
- `Framework-common/config_naming.toml` — the class-prefix naming rules (machine-readable mirror of DEV-RULES);
  reference only, not a tuning knob.

---

## Quick reference

| Script | Home | Positional | Key flags | Output |
|---|---|---|---|---|
| `run-debug-master.py` | `Framework-common/` | `MOD_NAME [MOD_PATH]` | `--save --logs --prefix --rerun` | data + both diagnostics |
| `run-modparse.py` | `Framework-ModParse/` | `MOD_NAME [MOD_PATH]` | `--prefix --rerun` | `data-<Mod>/raw_*.csv` |
| `run-logtriage.py` | `Framework-Logtriage/` | `MOD_NAME` | `--logs --prefix --rerun` | `log-CURR/<Mod>/` |
| `run-saveparse.py` | `Framework-SaveParse/` | `MOD_NAME` | `--save --prefix --rerun` | `save-CURR/<Mod>/` |
| `run-scrub.py` | `Framework-common/` | — | `--mod --commit` | (deletes generated data) |
| `testbook-toggle-markers.py` | `Framework-common/` | — | `--on/--off --mod --path --commit` | (rewrites mod `.txt`) |
| `run-archive-curr.py` | `Framework-common/` | `<log-CURR\|save-CURR>` | — | auto STEP 1 of log/save masters; demotes prior CURR + creates Game-<game>/ if missing |

| Config file (from `tools/`) | Tracked? | What you change there |
|---|---|---|
| `Framework-common/config_game.toml` | no (per-machine) | paths + `[mod_locations]` — the ONE setup file |
| `Framework-common/config_game.example.toml` | yes | template (copy, don't edit) |
| `Framework-common/config_naming.toml` | yes | naming-rule reference |
| `Framework-ModParse/config_modparse.toml` | yes | scan extensions, prefix stopwords, output names |
| `Framework-Logtriage/config_logtriage.toml` | yes | log files/severity, re-fire threshold |
| `Framework-Logtriage/benign.csv` | yes | benign-error allowlist rows |
| `Framework-SaveParse/config_saveparse.toml` | yes | fixed-point factor, cap regex, capped building lists |
| `Framework-common/config_toggle.toml` | yes | comment marker, toggle patterns, extensions |

See `README.md` (concepts + how to READ the diagnostics) and each `Framework-*/README.md` for per-framework
detail. Design/vision: `hk-config/roadmap/MOD-DEBUG-FRAMEWORK.md`.
