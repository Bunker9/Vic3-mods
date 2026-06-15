# Top40EcoBoostMod — Changelog

## v0.6.1-dev (2026-06-15) — oil/rubber redesign + v2 table
- **Oil/rubber FIX:** the day-1 history seeder (`zz_eco_starters_oil_rubber.txt`) was wrong —
  `oil_rig`/`rubber_plantation` are discoverable RGOs gated behind techs (`pumpjacks` /
  `rubber_mastication`) and can't be built at the 1836 start, so it did nothing. **Deleted it.**
  Replaced with a tech-triggered reward: `common/on_actions/eco_oilrubber_on_actions.txt` hooks
  `on_acquired_technology`; the first time *any* country in the world researches the unlocking
  tech, we gift that tech to the themed beneficiaries (**oil → OMA**, **rubber → BRZ + SIA**)
  via `events/eco_oilrubber_events.txt` (ecoor.1/ecoor.2), which seed up to 5 of the RGO
  (1 per best constructible state) with `eco_seed_spread_n`. Global-var guards = once per resource.
- **v2 champ/support/flavour table:** flavour now excludes wood/iron (Track-B), grain (generic),
  oil/rubber (tech-event), gold (dropped), meat (separate) — only start-buildable RGOs remain.
  Regenerated all 40 setups from `SELECT_ECOBOOST_FINAL_v2.csv` (521 seed calls).

## v0.6.0-dev (2026-06-15) — all 40 nations configured (champ/support/flavour)
Rolled the per-nation config out from PAN/PRU only to **all 40 target tags**, generated from
`hk-config/tools/SELECT_ECOBOOST_FINAL.csv` via `gen_ecoboost_configs.py`:
- **champ** = human-reviewed pick, throughput +200% for 20 yr (per-tag `eco_<TAG>_champ_tp_p1`).
- **support** = human pass1 picks, padded to ≥6 sensible buildable industries (≤6 kept for
  industrial GBR/PRU); seeded to 1×tier levels each.
- **flavour** = upstream basic-good inputs for the champ/support chains **plus every remaining
  buildable RGO/plantation** the nation isn't already championing/supporting (mines + cash
  crops), capped at 10. `wood`/`grain` excluded (the generic flavour already seeds +5 each).
- **fish dropped** for tags that can't build a fishing wharf (PAN/SOK/HUN/HYD/NEP/SHW/BAV).
- Generated files: `common/scripted_effects/eco_setup_generated.txt` (40 setups),
  `common/static_modifiers/eco_champ_tp_generated.txt` (40 throughput modifiers),
  `events/eco_events.txt` (eco.2 + eco.3 dispatch ladders for 40 tags). Hand PAN/PRU setups
  + their champ-tp modifiers removed (superseded). 586 building-seed calls total.

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
