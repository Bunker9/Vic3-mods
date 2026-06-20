# Testbook Script Manifest

Naming convention mirrors `hk-config/tools/`: prefix signals role.

---

## Naming convention

| Prefix | Role | Reads | Writes |
|--------|------|-------|--------|
| `run_*` | Orchestrator — entry point, ties stages together | authored files + logs | all generated outputs |
| `chk_*` | Static checker — no logs needed | mod source files | `<Mod>/static.json`, `<Mod>/standards.json` |
| `log_*` | Log parser — reads game logs, outputs structured JSON | `debug.log`, `error.log` | `log.json`, `timeline.json` |
| `rnd_*` | Renderer — turns JSON into HTML | `*.json` | `*.html` |
| `data_*` | (future) Intermediate cleaned data, derived from raw log JSON | `log.json` | `data_*.json` |
| `aggr_*` | (future) Aggregated summaries across runs | `data_*.json` | `aggr_*.json` |
| `utils` | Shared helpers (no prefix — imported, not run directly) | — | — |

---

## Current scripts

### Orchestrators

| Script | Description |
|--------|-------------|
| `v1/testkit/run_test.py` | Master entry point. Runs all stages for one or all mods. |
| `validate.bat` | Double-click shortcut: calls `run_test.py` from the project root. |

### Static checkers (`v1/testkit/checks/`)

| Script | Description |
|--------|-------------|
| `chk_structure.py` → `structure.py` | File encoding, brace balance, folder layout |
| `chk_standards.py` → `standards.py` | Advisory authoring standards (picture, loc keys, etc.) |
| `chk_conflict.py` → `conflict.py` | Cross-mod file path collision detection |
| `rebalance_verify.py` | One-off spot-check for a specific rebalance pass (not in main run) |

### Log parsers (`v1/testkit/checks/`)

| Script | Description |
|--------|-------------|
| `log_triage.py` | Parses `error.log` + `debug.log` → per-mod errors, census, tables |
| `timeline.py` | Parses `debug.log` → wars, eco builds, claims/homelands per year |

### Renderers (`testkit/`)

| Script | Description |
|--------|-------------|
| `render_html.py` | Generates the combined self-contained HTML report |

### Shared (`v1/testkit/checks/`)

| Script | Description |
|--------|-------------|
| `utils.py` | `resolve_logs_dir()` and other helpers shared across checkers/parsers |

---

## Log markers (what mods emit for the timeline)

| Marker | Mod | Meaning |
|--------|-----|---------|
| `WAR DECLARED` | MyDiploPlayMod | War started; preceded by `mdp_attacker:` / `mdp_tgt:` scope dump |
| `MDP_CLAIM` | MyDiploPlayMod | One claim granted; attributed via `Root:` or `mdp_attacker:` scope |
| `MDP_HOMELAND` | MyDiploPlayMod | One homeland granted |
| `MDP_POP` | MyDiploPlayMod | One pop grant (legacy; removed from mod) |
| `ECO_PLACED <type>` | Top40EcoBoostMod | Building placed; type = champ / support / flavour |
| `$B$` header | Top40EcoBoostMod | Building name header preceding ECO_PLACED |

---

## Data flow

```
Victoria 3 game run
    └─> debug.log, error.log
            ├─> log_triage.py  -> log.json       (per-mod errors + census)
            └─> timeline.py    -> timeline.json   (wars + eco + claims per year)

mod1/<Mod>/ source files
    ├─> structure.py   -> static.json
    ├─> standards.py   -> standards.json
    └─> conflict.py    -> conflicts.json

All JSON + authored bdd.md/observe.md
    └─> render_html.py -> <branch>.html  (the report)
```
