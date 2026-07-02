# Framework-Toggle — script manifest

> One row per script/artifact. ALL are STUBS (raise SystemExit) pending the Toggle build phase
> (`hk-config/roadmap/ROADMAP-debug-framework-rework.md` §Framework-Toggle). Registered 2026-07-02
> (make-your-bed backfill). The working interim toggle remains `Framework-common/testbook-toggle-markers.py`.

| file | class | lines | purpose | status |
|---|---|---|---|---|
| `ext-toggle-markers.py` | ext- | stub | ss1: find fp*/debug_log(_scopes) lines in ONE file | STUB |
| `run-toggle-file.py` | run- | stub | ss2: comment/uncomment ONE file (uses ss1+ss3) | STUB |
| `chk-toggle-scopes.py` | chk- | stub | ss3: brace balance + no empty scope after toggle | STUB |
| `run-toggle.py` | run- (master) | stub | ss4: repo/mod/file target; loop over ss2; --on/--off, dry-run default | STUB |
| `config_toggle.toml` | config (data) | n/a | RELOCATES here from Framework-common at build time (+ scope-keyword set) | TODO |
| `README.md` | doc | n/a | framework contract (stub status) | done |
