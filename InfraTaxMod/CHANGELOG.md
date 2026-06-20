# InfraTaxMod — Changelog

## v0.1.0 (2026-06-12) — initial
Global infrastructure / tax-capacity / bureaucracy boost, modelled on `3104377473`'s
state-trait approach (`state_trait_indus_valley` / `_indus_river`) but delivered as
**modifiers** instead of `map_data` traits — so no state_regions files are copied and
nothing drifts across game patches.

- **`infratax_state_boost`** (per-state, applied to **every state**): `state_infrastructure_add=20`,
  `state_infrastructure_mult=0.25`, `state_tax_capacity_add=10`, `state_tax_capacity_mult=0.5`
  (scaled down from the old mod's 1.0–2.0), `state_bureaucracy_population_base_cost_factor_mult=-0.25`.
  **Permanent + state-scoped → survives conquest** (PAN annexing SIN keeps SIN's boost; no timeout).
- **`infratax_country_boost`** (per-country): `country_bureaucracy_mult=0.25` (capacity side).

## map_data state buffs (ported from 3104377473)
arable_land / subsistence_building / capped_resources / resource are MAP DATA, not modifiers,
so they need `map_data/state_regions` files. `hk-config/tools/port_statedata.py` ports the old
mod's values onto CURRENT vanilla (mapping old→new tokens, e.g. `bg_logging`→`building_logging_camp`,
`building_subsistence_rice_paddies`→`building_subsistence_rice_farm`), max-merging so nothing is reduced.
- **Gated to USER-touched states** via fingerprints (no old-vanilla baseline available to diff):
  subsistence category change, `arable_land` ×100, or a capped/resource value ≡1 (mod 5). → 68 states, 12 files.
- Each ported state carries a `# [InfraTaxMod] ported from 3104377473 (signal: …) — …` marker so a
  future game-version re-merge is easy to find. Review list: `hk-config/tools/statedata_changes.csv`.
- Modded state_regions files replace vanilla by filename; only the 12 files with ≥1 change are shipped.

## Runtime flow
`on_game_started_after_lobby` → `every_state { add_modifier infratax_state_boost }` (permanent,
owner-change-safe) + `every_country { add_modifier infratax_country_boost }`. The map_data buffs are
static (loaded from the shipped state_regions files).

## Known limits / verify in-game
- Assumes `every_state` is valid at the on_action top scope (standard global iterator) — confirm no error.log.
- States colonised from terra incognita AFTER 1836 won't auto-receive the state boost (add an
  `on_colony_state_created`-style hook later if that matters).
