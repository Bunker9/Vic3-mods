# Top40EcoBoostMod — Changelog

## v0.5.0-dev (2026-06-12) — generic anti-death-spiral flavour
Feedback: most nations lack global market access at start and hit a supply/demand
shortage death-spiral (wood the worst early). Added a **generic flavour for every target**
(no per-nation config), wired into `eco_startup` before each nation's bespoke pass:
- `eco_generic_flavour`: **+5 wood** (logging camp), **+5 grain** (each staple farm the
  nation already grows; else the first staple it can construct), **+1 food industry** if teched.
- `eco_seed_spread_n` helper: adds 1 level to each of the top-N highest-gdp constructible
  states (additive), so per-state arable/resource caps clamp cleanly instead of overflowing.

## Runtime flow
`on_game_started_after_lobby` → `eco_startup`: (1) grant military techs to all targets,
(2) **`eco_generic_flavour`** for all targets, (3) per-nation `eco.2` build pass
(champ/support/bespoke flavour) → `eco.3` champ-state SoL at yr 20 → player-only `eco.4` toast.

## Prior
SoL flat +4 per incorporated state (P1/P2); capped champ/support spread engine; PAN + PRU configured.
