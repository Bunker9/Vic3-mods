# Testbook — Vic3 mod test harness

Two side-by-side report engines that read the same game logs (`debug.log` / `error.log`)
and the same mod sources under `mod1/`:

```
testbook/
├─ v2/   ACTIVE — manifest-driven, plug-and-play feature folders, self-contained.
│        Run:  python testbook/v2/run_v2.py            (see v2/README.md)
├─ v1/   ARCHIVE — the original monolithic harness (run_test.py + render_html.py).
│        Run:  python testbook/v1/testkit/run_test.py  (or double-click validate.bat)
└─ validate.bat   thin forwarder -> v1/validate.bat (legacy double-click entry)
```

## v1 vs v2

| | v1 (`v1/`) | v2 (`v2/`) |
|---|---|---|
| Entry | `v1/testkit/run_test.py` | `v2/run_v2.py` |
| Structure | one renderer + `checks/` | manifest + per-feature `extract.py` + `component.html` |
| Output | `v1/<branch>.html` + per-mod `v1/<Mod>/report.html` | `v2/MAIN-<branch>-testing.html` |
| Status | frozen archive | active development |

The two share the **per-mod authored spec** under `v1/<Mod>/` (`bdd.md`, `observe.md`,
`props.toml`). v2 reads `props.toml` from there but imports no v1 **code** (it is
self-contained — its own check modules live in `v2/testkit/generic/`).

## Why v1 is kept

It is the reviewed/last-known-good report and the source the v2 generic checks were ported
from. It still runs; it is not deleted, just boxed so the root stays clean and v2 is the
obvious active engine.

## Moved on 2026-06-18

Everything that used to sit at the testbook root (`testkit/`, the per-mod folders, the v1
docs/reports) moved into `v1/`. Internal paths were refactored accordingly. External
references were updated the same day to `testbook/v1/testkit/...` — including the
master-promotion CI gate (`.github/workflows/static-checks.yml` in mod1 + mod1-bpp, which
now sources `_harness/v1/testkit/checks/structure.py`), container `CLAUDE.md`, `hk-config/`
docs + roadmap, and `CEREMONIES.md`. v2 (`run_v2.py`) is the active engine; v1 is the archive.
