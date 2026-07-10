# Framework-Toggle — mod-source debug/fingerprint marker TOGGLE

> Status: **BUILT 2026-07-03** (ss1–ss4 + `lib_toggle` + `config_toggle.toml`). Supersedes and retires the old
> monolithic `Framework-common/testbook-toggle-markers.py` (git rm'd). Design home:
> `hk-config/roadmap/ROADMAP-debug-framework-rework.md` (§Framework-Toggle).

Comments (`--off`) / uncomments (`--on`) every `debug_log` / `debug_log_scopes` / `_fingerprint_` line across mod
source `.txt`, **plus** the wrapper lines of any scope left fingerprint-only (an `if { limit … <fp> }` whose only
effect was a fingerprint collapses cleanly on `--off`, restores on `--on`). BOM + line endings preserved.
**Dry-run by default; `--commit` writes.** The empty-scope collapse and the post-toggle check operate over the
configured `scope_keywords` set, so data/definition blocks are never touched.

## Scripts (a thin master + independently-runnable per-file subs over one shared lib)
| script | role |
|---|---|
| `lib_toggle.py` | shared core (imported BY NAME → underscore): marker toggle, comment-agnostic brace tree, empty-scope collapse, scope check, BOM/EOL-preserving file IO |
| `ext-toggle-markers.py` (ss1) | find debug_log/`_fingerprint_` marker lines in ONE file → print locations (read-only) |
| `run-toggle-file.py` (ss2) | toggle ONE file (`--on`/`--off`, `--commit`); runs the ss3 check after |
| `chk-toggle-scopes.py` (ss3) | STATIC check on ONE file: brace balance + no active configured-scope left empty-except-limit; exit 0/1 |
| `run-toggle.py` (ss4 MASTER) | target = single file / mod-or-repo folder / `--mod` NAME; loop; aggregate |

**Design note:** the roadmap phrasing "ss2 uses ss1+ss3" and "ss4 loops calling ss2" is realised via the shared
importable `lib_toggle` (the DEV-RULES tooling-design pattern: thin subs + one `lib_*`), not a subprocess per
file — so dry-run aggregation is exact and there is no process-spawn-per-file cost. Each sub is still
independently runnable on any file by absolute path (for debugging one file).

## Usage
```
# whole mod (folder walk), preview then apply:
python run-toggle.py --off --mod MyDiploPlayMod
python run-toggle.py --off --mod MyDiploPlayMod --commit

# a single file or explicit folder by absolute path:
python run-toggle.py --on "C:/…/mod1/Top40EcoBoostMod/common/scripted_effects/eco_effects.txt" --commit

# one file with the standalone subs:
python ext-toggle-markers.py <file.txt>
python run-toggle-file.py --off --commit <file.txt>
python chk-toggle-scopes.py <file.txt>
```

> **Promote / Ceremony 3 = `--off --commit`** per mod, then verify ZERO active `debug_log` / `_fingerprint_`
> lines remain (DEV-RULES save-fingerprint / debug-var promote discipline).

## Config — `config_toggle.toml`
`comment_marker`, the toggle `patterns`, the `extensions` touched, and the `scope_keywords` set the collapse/check
operate over. Relocated here from `Framework-common/` when the split landed.

## Scripts — see `MANIFEST.md`.
