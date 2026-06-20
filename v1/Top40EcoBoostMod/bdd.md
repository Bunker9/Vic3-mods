# BDD — Top40EcoBoostMod

One Y/N question **per feature**. Fill the **Y/N** column with your in-game observation;
`Exp` = expected answer (the report asserts Answer == Exp). Build label is in the section
header (auto-read from the versiontest stamp). Picks: `hk-config/tools/SELECT_ECOBOOST_FINAL_v2.csv`.
Cross-check builds in the **Timeline** tab (Year | Country | Building | Type | Levels).

| # | Feature | Question | Exp | Y/N | Comment |
|---|---------|----------|-----|-----|---------|
| 1 | 40-tag rollout | Did ALL 40 target nations receive eco buildings (champ + support + flavour)? | Y | | Timeline tab, filter each tag |
| 2 | Champ + support | Did each nation's champ good and its locked support goods get built? | Y | | spot-check PAN fabric / PRU steel |
| 3 | Flavour RGOs | Did flavour RGOs/plantations build day-1 (cap 10; wood/iron/grain/oil/rubber/gold/meat excluded)? | Y | | flavour rows in Timeline |
| 4 | Yearly pulse | On each Jan-01 does the pulse re-spread champ/support across states (incl. newly-annexed)? | Y | | eco.5; rows in later years |
| 5 | Cap-aware build | Does the pulse build ONLY up to a state's max cap (then the next-best state), never over-capacity? | Y | | no state.cpp "can only support N" |
| 6 | Throughput modifiers | Do the 3 category modifiers (agri/mine/ind) give +50% throughput + wage for the first 20 years? | Y | | building tooltip |
| 7 | Global SoL/edu | Do all 40 get the flat +4 SoL / +0.25 education modifier for the whole game? | Y | | eco_sol_edu_global |
| 8 | Oil tech event | When the world researches **pumpjacks**, does OMA get the tech + up to 5 oil_rigs (once)? | Y | | ecoor.1 |
| 9 | Rubber tech event | When the world researches **rubber_mastication**, do BRZ + SIA get the tech + rubber_plantations (once)? | Y | | ecoor.2 |
| 10 | Track-B starters | Are wood/iron starter RGOs seeded day-1 with NO over-capacity (0-cap states excluded)? | Y | | zz_eco_starters |
| 11 | Runtime-safe dispatch | Does the yearly pulse run for all targets with NO "Invalid right side … 'c'" errors after annexations? | Y | | flag dispatch, not this=c:TAG |
| 12 | Clean log | Is error.log free of eco.* / eco_pulse / eco_startup errors (no invalid scope/effect)? | Y | | |
