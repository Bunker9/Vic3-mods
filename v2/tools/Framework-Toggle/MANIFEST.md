# Framework-Toggle — script manifest

> One row per script/artifact. **BUILT 2026-07-03** (ss1–ss4 + `lib_toggle` + relocated `config_toggle.toml`).
> Supersedes the retired `Framework-common/testbook-toggle-markers.py`. Design home:
> `hk-config/roadmap/ROADMAP-debug-framework-rework.md` §Framework-Toggle.

| file | class | lines | purpose | status |
|---|---|---|---|---|
| `lib_toggle.py` | lib (imported → underscore) | cohesive | shared core: marker toggle, comment-agnostic brace tree, empty-scope collapse, `check_scopes`, BOM/EOL-preserving IO. Ported from the retired interim's proven `_collapse_scopes` | built |
| `ext-toggle-markers.py` | ext- | ≤25 | ss1: list debug_log/`_fingerprint_` marker lines in ONE file (read-only) | built |
| `run-toggle-file.py` | run- | ≤45 | ss2: toggle ONE file (`--on`/`--off`, dry-run default `--commit`); ss3 post-check; BOM+EOL preserved | built |
| `chk-toggle-scopes.py` | chk- | ≤25 | ss3: static check on ONE file — brace balance + no active configured-scope left empty-except-limit; exit 0/1 (chk-* executable, not pytest) | built |
| `run-toggle.py` | run- (master) | ≤55 | ss4: target = file / mod-or-repo folder / `--mod` NAME; loop over `lib_toggle`; `--on`/`--off`, dry-run default | built |
| `config_toggle.toml` | config (data) | n/a | comment marker + toggle patterns + extensions + `scope_keywords` set. RELOCATED from Framework-common 2026-07-03 | built |
| `test_file_to_del.txt` | fixture (disposable) | n/a | throwaway toggle fixture for manual verification (debug_log + fp lines + fp-only `if{}` scope + a real scope); safe to delete | temp |
| `README.md` | doc | n/a | framework contract (as-built) | done |
