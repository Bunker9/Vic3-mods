# ExpFightMod — Changelog

## v0.5.0-dev (2026-06-12) — feedback rework
Reworked `expfight_warboost` per in-game feedback ("couldn't see modifiers work"):
- **Flat** edge instead of invisible mults: `unit_offense_add = 10`, `unit_defense_add = 50`.
- **Mobility**: `military_formation_army_movement_speed_mult = 3` + `mobilization_speed_mult = 3` (~4×) — get to the front fast.
- **Armed forces in power & happy**: `interest_group_ig_armed_forces_pol_str_mult = 0.5` + `..._approval_add = 30` so the war bonuses actually stay in effect.
- Kept: morale/org recovery, `country_military_goods_cost_mult = -0.5` (cheap upkeep), no naval.

## v0.6.0-dev (2026-06-12) — per-tag war-footing duration
**13 long-war expanders** get the war footing for **120 months (10 yr)** instead of 60 — they
have many neighbours to conquer (trigger `expfight_is_long_war_country`):
PAN, DEI, SOK, SAR, SWE, DAI, NEP, CLM, ARG, SIA, MOR, OMA, SHW.
The 5-yr set is the strong powers: BIC, PRU, MEX, BRZ, PER, EGY, SAF.

## Runtime flow
`on_game_started_after_lobby` → for every expand tag: grant `army_reserves` + `general_staff`
techs, then `add_modifier expfight_warboost` for 120 months (SOK/OMA/SHW) else 60 months.

## v0.x (prior)
Initial scaffold: 5-yr war footing + barracks-doctrine tech grant.
