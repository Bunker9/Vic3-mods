# Testbook — How to Use

A self-contained test harness for Vic3 mods. One command regenerates all reports
from the latest game logs. No separate sync step.

---

## Quick start

```
python testbook/v1/testkit/run_test.py           # test all mods
python testbook/v1/testkit/run_test.py ModName   # test one mod
python testbook/v1/testkit/run_test.py --open    # also open the report in browser
```

Then press **F5** in the browser to refresh after a fix.

---

## Workflow

1. **Load the mod** in Victoria 3 with `debug_mode` enabled.
2. **Play the scenario** described in `<Mod>/observe.md` (usually a few years).
3. **Quit** to main menu (forces a final log flush).
4. **Run** `python testbook/v1/testkit/run_test.py` from the project root.
5. Open the generated `<branch>.html` report (or let `--open` do it).
6. Fill in the **BDD** `Y/N` answers in `<Mod>/bdd.md` based on what you saw.
7. Re-run to update the report with your answers.

---

## What the report shows

| Tab | Content |
|-----|---------|
| Static | File encoding, brace balance, folder layout per mod |
| Log | Per-mod error.log triage, census (buildings placed vs cap), custom tables |
| BDD | Your in-game observations vs the expected behaviour checklist |
| Conflicts | Cross-mod file path collisions (hard = real overrides) |
| Timeline | Per-year wars, eco building placements, claims/homelands granted |

---

## Files you author (never overwritten by the harness)

| File | Purpose |
|------|---------|
| `<Mod>/bdd.md` | Behaviour-driven test questions + your Y/N answers |
| `<Mod>/observe.md` | Notes on what to watch and recent triage |
| `<Mod>/props.toml` | Per-mod config: census expected caps, custom log tables, benign errors |

---

## Files generated (gitignored or archive-only)

| File | Notes |
|------|-------|
| `log.json` | Raw parsed log data (gitignored) |
| `timeline.json` | Parsed timeline events (gitignored) |
| `conflicts.json` | Cross-mod conflict scan |
| `<branch>.html` | Combined report (gitignored root copy) |
| `<Mod>/report.html` | Per-mod archived copy (committed) |
| `<Mod>/static.json` | Static check results |
| `<Mod>/_meta.txt` | Last-tested stamp for INDEX.md |
| `INDEX.md` | Recency-ordered run index (regenerated each run) |

---

## Adding a new mod

1. Create `testbook/<ModName>/bdd.md`, `observe.md`, `props.toml` (copy from an existing mod).
2. The harness auto-discovers it from `mod1/<ModName>/.metadata/metadata.json`.

## Adding a custom log table

In `props.toml`:
```toml
[[tables]]
title  = "My Table"
marker = "MY_MARKER"
source_file = "my_effects.txt"
columns = ["Country", "Value", "Notes"]
```

The mod logs: `debug_log = "MY_MARKER <val1> | <val2> | <val3>"` inside a `debug_log_scopes` block.

---

## Enabling debug logs in-game

Add to your `Documents/Paradox Interactive/Victoria 3/user_settings.txt`:
```
debug_mode=yes
```
Or launch with `-debug_mode` on the command line.
