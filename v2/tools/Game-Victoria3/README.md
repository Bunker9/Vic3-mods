# Game-Victoria3 — game-specific config + per-run data

> The game-specific layer of THE debug framework. The `Framework-*` code is game-agnostic; everything that is
> specific to *this* game (Victoria 3) — absolute paths, naming conventions, and the per-run data — lives here.
> A future PDX game = a new sibling `Game-<X>/`. Entry point: `../Framework-common/README.md` (the master README).

## Config (tracked, except the machine file)
| file | tracked? | what |
|---|---|---|
| `config-game.example.toml` | YES (template) | copy → `config-game.toml`, fill in YOUR abs paths |
| `config-game.toml` | **NO (gitignored)** | per-machine abs paths: `game_files_path`, `logs_dir`, `save_games_dir`, `[mod_locations]`. May contain your OS username ⇒ never committed (PII rule). Blank a key ⇒ framework auto-resolves it. **The ONLY file you edit on a new machine/OS** (vision §A/§Z). |
| `config-naming.toml` | YES | the class-prefix naming conventions (§B) — the machine-readable companion to DEV-RULES "Naming conventions". |

## Per-run DATA (all gitignored — regenerable)
| dir | produced by | content |
|---|---|---|
| `data-<Mod>/` | Framework-ModParse | idempotent token inventory (`raw_*`/`data_*`/`aggr_*`); the shared join keys |
| `log-CURR-<ts>-<branch>/<Mod>/` | Framework-Logtriage | one game run's log-triage outputs (markers, errors, diagnostics.md) |
| `save-CURR-<name>/<Mod>/` | Framework-SaveParse | a save's fingerprint/census/over-cap outputs |
`CURR` marks the current run under analysis; older runs may be kept beside it as archives.

## Game-specific scripts (pre-run ceremony)
The framework's Logtriage/SaveParse read the logs/save a game run produces, so a run must be prepared the
Victoria-3 way FIRST. These steps are GAME-SPECIFIC and their natural home is here under `Game-Victoria3/`:
- **pre-game LOG-CLEANUP + versiontest version-bump** — so `error.log`/`debug.log` show only this run + the
  day-1 popup confirms the build. **Currently** implemented as the Ceremony-2 PowerShell in
  `hk-config/scripts/envSetup_pre_game_launch.ps1` (+ `clear-vic3-logs.ps1`), wired into `CEREMONIES.md` and
  the launcher. Relocating them under `Game-Victoria3/` is a confirm-first follow-up (they have ceremony +
  launcher references) — not done implicitly. Until then, run the Ceremony-2 script before each test launch.

See the master README (`../Framework-common/README.md`) "WHERE-map" for the full script-home table.
