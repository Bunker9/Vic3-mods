# Framework-common/scratch/ — manual analysis query capture trail

> **RULE (user, 2026-07-04):** EVERY ad-hoc / manual query Claude runs to analyse the framework outputs
> (error attribution, save cross-referencing, goods prices, over-cap, feature verification, …) MUST be saved
> here — one dated file per analysis session. These are the capture trail AND the SPEC for what the framework
> must eventually automate (the per-mod-FEATURE diagnostics + `actinfo` bar, TODO T108). A manual query that
> found `actinfo` is a diagnostic the framework SHOULD generate itself.

Not a place for framework code (that lives in the `Framework-*` dirs, registered in MANIFEST). These are
throwaway-but-kept investigation snippets: reproducible query + what it reveals + the finding.

## Index
- `2026-07-04_great-test-bug-analysis.md` — GREAT_TEST.v3 + 88K-line logs: error attribution, PvtCap over-cap,
  goods-price diagnostic, SteadyInnov `stdinnv_decisions.txt:41` bug.
