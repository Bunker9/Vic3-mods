# ExpFightMod — Changelog

## v0.5.0-dev (2026-06-12) — feedback rework
Reworked `expfight_warboost` per in-game feedback ("couldn't see modifiers work"):
- **Flat** edge instead of invisible mults: `unit_offense_add = 10`, `unit_defense_add = 50`.
- **Mobility**: `military_formation_army_movement_speed_mult = 3` + `mobilization_speed_mult = 3` (~4×) — get to the front fast.
- **Armed forces in power & happy**: `interest_group_ig_armed_forces_pol_str_mult = 0.5` + `..._approval_add = 30` so the war bonuses actually stay in effect.
- Kept: morale/org recovery, `country_military_goods_cost_mult = -0.5` (cheap upkeep), no naval.

## Runtime flow
`on_game_started_after_lobby` → for every expand tag: grant `army_reserves` + `general_staff` techs, then `add_modifier expfight_warboost` for 60 months (5 yr).

## v0.x (prior)
Initial scaffold: 5-yr war footing + barracks-doctrine tech grant.
