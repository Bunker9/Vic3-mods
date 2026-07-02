# Framework-Toggle — mod-source debug/fingerprint marker TOGGLE (STUBS — not yet built)

> Status: **STUB set (registered 2026-07-02; created 2026-07-01 rework pass).** All four scripts raise
> `SystemExit` until built. Until then the WORKING toggle is `Framework-common/testbook-toggle-markers.py`
> (see `Framework-common/HOW_TO_USE.md` §6) — this framework will SUPERSEDE it. Design home:
> `hk-config/roadmap/ROADMAP-debug-framework-rework.md` (§Framework-Toggle).

Modularizes the monolithic toggle into the standard sub-script shape: comment (`--off`) / uncomment (`--on`)
every `debug_log` / `debug_log_scopes` / `_fingerprint_` (+ dummy-use) line across mod source `.txt`, with a
scope-integrity check so no emptied `if`/`option`/`trigger` block is left behind.

## Planned scripts (build order ss1→ss4)
| script | role |
|---|---|
| `ext-toggle-markers.py` | ss1: find fp/debug_log lines in ONE file |
| `run-toggle-file.py` | ss2: comment/uncomment ONE file (uses ss1 + ss3) |
| `chk-toggle-scopes.py` | ss3: brace balance + no empty scope after toggle |
| `run-toggle.py` | ss4 MASTER: target = repo folder / mod folder / single file; loop over ss2 |

`config_toggle.toml` moves here from `Framework-common/` (+ gains the scope-keyword set) when ss1–ss4 are built.

## Scripts — see `MANIFEST.md`.
