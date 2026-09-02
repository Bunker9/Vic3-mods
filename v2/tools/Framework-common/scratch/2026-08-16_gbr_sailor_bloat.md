# 2026-08-16 GBR "ghost servicemen" in naval administrations

Reported: GBR states show a huge population of which a large slice is servicemen in naval
administrations, not appearing in any building, with navy sailors adding up to it.

Save `DEBUG_GBR_SAILOR_BLOAT.v3` (1922, 317MB). Run:
`run-debug-master.py --all --save <that> --rerun`, then `run-saveparse.py` again after the config
change below. `config_game.toml` gained the missing `NavalCapMod` mod_location.

## Framework change made to answer this (config only, no new script)

`Framework-SaveParse/config_saveparse.toml`:
- `[managers.pops]` gained **`workplace`** - the building id a pop works in. This is the join that
  attributes employment to a building, and nothing before it could answer "who works where".
- `[managers.building_manager]` gained **`last_failed_hire_date`**.

Both are generic and now available to every mod.

## FIRST PASS WAS WRONG - recorded so it is not repeated

The first analysis said naval administration employs 900 soldiers per level and concluded the
~0.5M was "27,000 employed plus their dependents". That skipped the arithmetic the user then did:
30 levels x 1,000 = 30,000 max, which cannot produce 0.5M. The error was attributing a state-wide
dependency ratio to one building without ever summing the state's employment.

## The actual numbers, Wales (state 430), pops joined to buildings via `workplace`

Total pop 1,388,512. **Total employed workforce 132,272. Only 320 people have no workplace.**

| building | levels | workforce | dependents | dep/wf |
|---|---|---|---|---|
| naval_administration | 30 | 30,000 | 320,233 | 10.7 |
| construction_sector | 30 | 27,318 | 271,700 | 9.9 |
| government_administration | 13 | 19,500 | 157,561 | 8.1 |
| barrack | 14 | 14,000 | 142,807 | 10.2 |
| financial_district | 200 | 11,901 | 95,641 | 8.0 |
| army_logistics_center | 206 | 10,300 | 97,662 | 9.5 |
| manor_house | 44 | 5,143 | 38,197 | 7.4 |
| paper_mill | 17 | **27** | 236 | - |
| urban_center | 50 | **10** | 47 | - |
| subsistence_farm | 38 | **20** | 199 | - |

Naval administration employs **exactly 1,000 per level**, as the user said. The user's arithmetic
was right and the first pass was not.

## Two separate anomalies

### 1. Military is 44-61% of ALL employment in GBR home states

Wales: naval admin 30,000 + barrack 14,000 + conscription 3,000 + naval fort 500 + army logistics
10,300 = **57,800 of 132,272 jobs = 44%**.
Lancashire: naval admin 39,000 + barrack 24,415 + conscription 1,000 + naval fort 500 =
**64,915 of 104,274 = 62%**.

### 2. Dependents per worker is ~10 where the global figure is 3 to 4

The ratio is UNIFORM across every building in the state (naval admin 10.7, construction 9.9, gov
admin 8.1), so it is a STATE-level property, not caused by naval administration or by the soldier
pop type. Global dependents-per-worker by pop type: soldiers 4.04, officers 4.45, laborers 3.15,
peasants 3.00. Wales runs 9.5 and Lancashire 13.6 across all types.

Workforce share of population: Texas 24.2%, Ile-de-France 21.5%, Brandenburg 19.4%, Home Counties
17.7%, **Wales 9.5%, Lancashire 6.9%**. Median across 736 states 24.9%.

## The thing that looks like a real defect

Lancashire holds huge building capacity that employs almost nobody:

| building | levels | workforce employed |
|---|---|---|
| financial_district | 347 | **20** |
| manor_house | 59 | **20** |
| urban_center | 56 | **2** |
| textile_mill / steel_mill / arms_industry / paper_mill / motor_industry | 1-8 each | **0** |

At Wales's observed FD rate (200 levels -> 11,901 workers) a 347-level FD should employ ~34,000.
Lancashire's pop TYPES that staff private industry are gone: **laborers workforce 65, shopkeepers
26, peasants 20** in a 1,519,298-pop state, against Ile-de-France's 217,823 laborers. The soldier
bloc is 780,855 of Lancashire's population, 51%.

The engine states the reason itself in the building block:
`failed_hires={ { workplace=... qualifying_workforce=0 reasons=1 ... } }`.

## Verdict

- Naval administration is not over-hiring. 1,000 per level, exactly as documented.
- The naval admin LEVEL COUNT is still high: GBR 865 levels over 30 states against 136 over 7 in
  vanilla day-1 history. NavalCapMod's cap is binding (5 states at exactly 60, 5 ports at exactly
  20 = `law_professional_navy`'s profile), so the mod is the brake, not the cause, but 60 per state
  across 30 states permits 1,800 levels.
- The bloat the user is seeing is that military employment is 44-62% of all jobs in these states
  and each of those workers carries ~10 dependents, so the military bloc becomes half the state
  population while private industry has no pop types left to hire.
- NOT YET EXPLAINED, and not guessed at: why dependents-per-worker is 3x normal in exactly these
  states. Next step is to extract the `failed_hires` sub-block (qualifying_workforce, reasons) so
  the engine's own refusal code can be read per building.
- No log evidence of a mod fault. 9,063 error lines, top signatures all vanilla (spline strips
  6,595, NAVAL_BATTLE promote 652, command_values.txt 614); the only mod file named anywhere is
  `stdinnv_modifier_types.txt`, once.

## actinfo

1. T221 stands: the naval admin ladder in `nvc_navy_model_caps.txt` allows too much in aggregate.
2. T223 (new): extract `failed_hires` so "why can this building not hire" is a framework output.
3. Open for the user: whether GBR's home states having half their jobs in the military is the
   intended outcome of the mod set or a symptom to chase further.

---

# Pass 2 - cross-tab and the law/modifier audit

Framework additions to make this answerable (config only): `[managers.laws]` -> `raw_laws.csv`
(law, country, active, activation_date), plus `workplace` on pops from pass 1.

## Workforce cross-tab, six states (workforce, levels in brackets)

| bucket | GBR Wales | GBR Lancashire | GBR HomeCounties | USA Texas | FRA IleDeFrance | GER Brandenburg |
|---|---|---|---|---|---|---|
| Urban centre | 10 (50) | 2 (56) | 1,342,076 (1969) | 948,270 (255) | 216,893 (102) | 246,480 (142) |
| Agro | 55 (4) | 4 (4) | 379 (7) | 609,540 (221) | 84,000 (30) | 896 (3) |
| Plantations | 0 | 0 | 0 | 652,500 (117) | 0 | 0 |
| Subsistence | 20 (38) | 20 (42) | 226 (36) | 481,204 (175) | 40 (14) | 50 (49) |
| Light industry | 118 (23) | 0 | 60,047 (22) | 131,580 (91) | 88,770 (37) | 138,586 (70) |
| Heavy industry | 57 (2) | 43 (2) | 79,020 (30) | 158,399 (75) | 154,500 (47) | 45,196 (16) |
| Mining | 50 (2) | 0 | 123 (2) | 312,791 (128) | 0 | 14,400 (8) |
| Financial district | 11,901 (200) | 20 (347) | 499,488 (4995) | 53,981 (540) | 10,500 (105) | 60,600 (606) |
| Manor house | 5,143 (44) | 20 (59) | 111,900 (746) | 91,050 (607) | 5,850 (39) | 47,250 (315) |
| Construction | 27,318 (30) | 7,988 (30) | 30,000 (30) | 18,033 (30) | 3,000 (3) | 21,000 (21) |
| Infra rail/port | 5,300 (5) | 17,400 (29) | 45,300 (43) | 150,943 (151) | 7,700 (7) | 9,000 (9) |
| **MIL naval admin** | **30,000 (30)** | **39,000 (39)** | **60,000 (60)** | **60,000 (60)** | **1,000 (1)** | **1,000 (1)** |
| **MIL barracks** | 14,000 (14) | 24,415 (27) | 23,886 (24) | 1,000 (1) | 2,000 (2) | 56,000 (56) |
| **MIL conscription** | 3,000 (3) | 1,000 (1) | 50,000 (50) | 47,847 (50) | 0 | 0 |
| **MIL logistics** | 10,300 (206) | 0 | 15,500 (311) | 0 | 13,250 (265) | 9,750 (195) |
| **GOV admin** | 19,500 (13) | 13,500 (9) | 15,000 (10) | 15,000 (10) | 54,000 (36) | 42,000 (28) |
| TOTAL WORKFORCE | 132,303 | 104,274 | 3,312,866 | 4,142,486 | 783,521 | 784,952 |
| TOTAL POP | 1,388,512 | 1,519,298 | 18,764,850 | 17,114,091 | 3,637,777 | 4,051,984 |
| **WORKFORCE RATIO** | **9.5%** | **6.9%** | **17.7%** | **24.2%** | **21.5%** | **19.4%** |

Government-funded buildings hire at the SAME rate in every state - naval admin 1,000/level and
government administration 1,500/level in all six. The variance is entirely in the private sector.

Wales and Lancashire have no private economy left: urban centre 50 and 56 levels employing 10 and
2 people, zero plantations, zero light industry in Lancashire, subsistence 38 and 42 levels
employing 20 each. Texas by contrast has 1.74M of its 4.14M workforce in subsistence + agro +
plantations.

## Law audit - the women's-suffrage sign-error hypothesis is DISPROVED

`state_working_adult_ratio_add` is the only law-borne token that moves the workforce share. Base
`working_adult_ratio = 0.25` for every pop type except aristocrats 0.2 and slaves 0.5
(`common/pop_types/*.txt`; soldiers use the default, so pop composition does not move it).

Values, `common/laws/02_rights_of_women.txt` + `02_welfare.txt`:
law_women_in_the_fields +0.3 / law_women_own_property +0.05 / law_women_in_the_workplace +0.1 /
law_womens_suffrage +0.15 / law_old_age_pension -0.01. `law_no_womens_rights` carries none.

Active laws from the save (`raw_laws.csv`, active=yes):

| | women's law | welfare law | total add | theoretical ratio | observed |
|---|---|---|---|---|---|
| GBR | women_own_property +0.05 | poor_laws 0 | **+0.05** | 0.30 | 17.7 / 9.5 / 6.9% |
| USA | **no_womens_rights 0** | no_social_security 0 | 0 | 0.25 | **24.2%** |
| GER | women_own_property +0.05 | no_social_security 0 | +0.05 | 0.30 | 19.4% |
| FRA | women_own_property +0.05 | old_age_pension -0.01 | +0.04 | 0.29 | 21.5% |

GBR has the joint-HIGHEST theoretical ratio and the worst observed. The only country that hits its
theoretical value is the one with the worst women's law. No sign error, and no mod file mentions
any of these laws (`grep law_poor_laws|law_combination_acts|law_charitable_health_system|
law_women_own_property|law_religious_schools|law_no_womens_rights mod1/` = zero matches).

## Modifier audit - what GBR ACTUALLY carries in the save

From `raw_flags.csv` (kind=modifier) joined on `country_manager.database.1` and the state ids:

- GBR country: `eco_sol_edu_global` (Top40Eco, permanent), `stdinnv_gp1_drain`, `stdinnv_gp1_welfare`
  (SteadyInnov, 48mo) + 8 vanilla ones.
- Wales / Lancashire / Home Counties states: `stdinnv_gp1_sol_state` only.
- Texas: `nous_migrant_magnet`. Ile-de-France: vanilla only.

None of them touches `state_working_adult_ratio_add` or any employee/employment token. Ruled out by
name and by file: `stdinnv_fighting_addiction`, the only mod modifier carrying
`building_minimum_incorporated_subsistence_employment_add = -0.4`, goes to **CHI for 8 years**
(`stdinnv_countries.txt:39`), never GBR.

### The one lever where GBR is an outlier and it is ours

`state_dependent_wage_mult` stack:

| | vanilla law | mod adds | total |
|---|---|---|---|
| GBR | child_labor_allowed 0.30 | eco_sol_edu_global +0.20 (**plus a `_add` of 0.20**), stdinnv_gp1_sol_state +0.10 | **0.60 + 0.20 add** |
| USA | child_labor_allowed 0.30 | none | 0.30 |
| FRA | child_labor 0.30 + old_age_pension 0.20 | none | 0.50 |
| GER | child_labor_allowed 0.30 | none | 0.30 |

GBR carries double the USA's dependent wage, and all of the excess is mod-added.
`state_dependent_wage_add` is used by NO vanilla law, amendment or modifier anywhere - only
`eco_modifiers.txt:62` and `stdinnv_modifiers.txt:43`. Whether a higher dependent wage raises the
dependent COUNT is an in-game test, not a claim: remove `eco_sol_edu_global` from GBR
(`zz_eco_modifiers.txt:15`) and re-check the Wales workforce ratio.

## What this rules in and out

- OUT: women's suffrage / welfare law sign error. GBR's law stack is better than the USA's.
- OUT: any mod employee_mult or subsistence modifier on GBR. None is applied to it.
- OUT: naval administration over-hiring. 1,000/level everywhere, identical across all six states.
- IN, measurable: GBR's private sector in Wales and Lancashire employs almost nobody while its
  military and government buildings are at full rate, so military is 44% and 62% of all jobs there.
- IN, testable: GBR is the only one of the four carrying mod-added `state_dependent_wage` on top of
  the vanilla law, at double the USA's total.

---

# Pass 3 - state-modifier sweep, and the statistic that actually explains it

## 1. The complete lever inventory (not just laws)

`grep -hoE "^(state|country|building|building_group)_[a-z_]*(workforce|working_adult|dependent|
employment|employee|migration|mortality)[a-z_]*" common/modifier_type_definitions/*.txt` returns
the full universe. Exactly ONE token moves the workforce/population split:
**`state_working_adult_ratio_add`**. Everything else is employee_mult (how many staff a building
needs), mortality, or migration.

Every source of `state_working_adult_ratio_add` in the entire game:

| source | value |
|---|---|
| law_women_in_the_fields | +0.30 |
| law_womens_suffrage | +0.15 |
| law_women_in_the_workplace | +0.10 |
| law_women_own_property | +0.05 |
| trade-union IG traits (x2) | +0.05 |
| agitators_2_modifiers | +0.05 |
| law_old_age_pension | **-0.01** |

That is the whole list. Nothing in vanilla, and nothing in any of our mods (`grep working_adult
mod1/` = zero matches), can push a state BELOW the 0.25 base. The "a modifier is dragging the
ratio down" hypothesis is therefore ruled out by inventory, not by argument.

## 2. Modifiers actually attached to GBR states in the save

`raw_flags.csv` kind=modifier, joined on `states.database.<id>` for every GBR-owned state:
only SIX distinct modifiers exist across all of GBR, and Wales / Lancashire / Home Counties carry
`stdinnv_gp1_sol_state` alone (SoL +1, `state_dependent_wage_mult` +0.1). The other five are
`recently_liberated_state`, `skyscraper_site`, `state_oil_pipeline`, `rubber_production_modifier`,
`lacking_industrial_safety_regulations`, each on 1-3 states. Checked every one of them plus all 11
GBR country modifiers against the lever list: **none carries a workforce, employee, mortality or
migration token** except `rubber_production_modifier` (migration pull +0.5, one state) and
`lacking_industrial_safety_regulations` (mortality, one state).

## 3. What our mods DO add to these states - real, but not the cause

`InfraTaxMod/common/state_traits/infratax_traits.txt` INJECTs negative `employee_mult` into vanilla
state traits, and `map_data/state_regions/00_west_europe.txt` also ADDS traits to states that did
not have them:

| state | trait | our modifier | vanilla had the trait? |
|---|---|---|---|
| Wales | state_trait_south_wales_valleys | bg_manufacturing_employee_mult **-0.2** | yes, we injected the modifier |
| Lancashire | state_trait_black_country | bg_mining_employee_mult **-0.4** | **NO - added by the mod** |
| Yorkshire | south_yorkshire_coalfield + black_country | -0.2 manufacturing, -0.4 mining | trait added |
| Midlands, East Anglia, Lowlands | black_country | -0.4 mining | **trait added by the mod** |
| Home Counties | state_trait_london_docklands | bg_ship_construction_employee_mult **-0.5** | yes, injected |

Also `state_trait_infratax_cheat` (bg_manufacturing -0.4, bg_service -0.2, bg_extraction -0.2) on
20 states and `state_trait_infratax_ext_cheat` on 19, worldwide.

These genuinely cut employment in those building groups by 20-50%, and they are ours. They are NOT
sufficient: they cannot produce a 99% shortfall (Wales urban centre 50 levels employing 10), and
`bg_service` is not even affected in Wales.

## 4. The statistic that does explain it

Across all 736 states over 200k pop, correlation between MILITARY POP SHARE (soldiers + officers,
workforce + dependents, as a share of state population) and WORKFORCE RATIO:

**r = -0.558**

| military pop share | states | mean workforce ratio |
|---|---|---|
| 0-10% | 661 | **25.4%** |
| 10-20% | 44 | 21.1% |
| 20-30% | 14 | 21.5% |
| 30-40% | 5 | 15.4% |
| 40-60% | 5 | 15.9% |
| 60%+ | 7 | **8.5%** |

The default 25% is exactly what a state with a normal-sized garrison reports. The ratio falls
monotonically with military share. Wales (34% military pop, 9.5%) and Lancashire (51%, 6.9%) sit
where the curve says they should.

Military buildings hire a FIXED 1,000 per level regardless of state population, so the bloc's
families are dependents who never enter the labour market. A state whose population is majority
military therefore reports a collapsed workforce ratio - no modifier required.

## Conclusion

- No modifier, vanilla or modded, is reducing GBR's workforce ratio. The lever does not exist in a
  negative form beyond -0.01.
- The driver is the SIZE of the military establishment, which is where the mod set does bear on it:
  GBR holds 865 naval administration levels against 136 in vanilla day-1 history, and NavalCapMod's
  60-per-state ceiling lets every coastal state reach a Home-Counties-sized base (T221).
- Our negative `employee_mult` traits on the British states are a real, separate, second-order drag
  worth reviewing on their own merits, but they are not what produced 9.5%.

---

# Pass 4 - the in-game pop, and why 8.3% is not a naval problem at all

## The screenshot reconciles exactly with the save

In-game pop id **15693** IS the save id. From `raw_pops.csv`:
`type=soldiers workforce=20260 dependents=222053 location=430 workplace=122 culture=287
wealth=15 num_literate=16209`, and building 122 = `building_naval_administration` (30 levels).
The panel reads 20.2K / 222K / 8.3%. Same pop.

The panel also states the target: **"Over time this ratio will approach 30.0%: base value for
Servicemen 25.0%, +5% from Great Britain, +5% from Propertied Women in Great Britain"** - which is
`WORKING_ADULT_RATIO_BASE = 0.25` plus `law_women_own_property` +0.05, exactly the pass-2 calc.
The game agrees with the law audit.

GBR-wide from the same panel: Servicemen 9.69M population, 1.24M workforce, 8.44M dependents.

## 8.3% IS THE WHOLE STATE, NOT THE SERVICEMEN

Workforce ratio per pop type (save, four states):

| pop type | Wales | Lancashire | HomeCounties | Texas |
|---|---|---|---|---|
| soldiers | 8.5% | 6.9% | 16.6% | 23.1% |
| officers | 10.2% | 7.0% | 19.5% | 21.9% |
| laborers | 9.0% | 10.0% | 18.2% | 24.2% |
| machinists | 8.6% | 6.9% | 16.1% | 23.8% |
| clerks | 8.8% | 7.2% | 15.7% | 24.4% |
| bureaucrats | 12.7% | 6.1% | 18.7% | 23.3% |
| shopkeepers | 8.6% | 10.4% | 18.2% | 24.3% |
| clergymen | 12.0% | 7.5% | 20.2% | 23.7% |
| capitalists | 16.1% | 19.2% | 20.7% | 23.7% |
| peasants | 9.1% | 18.0% | 17.9% | 25.6% |
| **STATE** | **9.5%** | **6.9%** | **17.7%** | **24.2%** |

Every profession in Wales sits at 8-12% and in Lancashire at 6-10%. A clergyman is as depressed as
a serviceman. The naval administration has nothing to do with the ratio - pop 15693 is simply at
the Wales-wide level. Texas sits at its own 25% target; all three GBR states are far under their
30% target, worst in Wales and Lancashire.

## History 1836-1922 is NOT obtainable from the saves on disk

Save headers: `DEBUG_GBR_SAILOR_BLOAT.v3` starts **SAV0100**, every other save (incl.
`great britain_1859_08_09.v3` and `great britain_1922_06_30.v3`) starts **SAV0105**. The 0 vs 5
flag is uncompressed vs compressed. Proven, not inferred: running SaveParse on the 1859 save
completed but wrote **0-byte** `raw_*.csv` - the parser reads plaintext only.

The in-game population graph for this pop also reads "No historical data", so the game is not
holding a series either. To get a time series, save in the same uncompressed/debug mode at
intervals during a run; then the framework can parse each one and the series is a join.

## Answer to "can the rate of increase be forced"

`common/defines/00_defines.txt`:
```
WORKING_ADULT_RATIO_BASE = 0.25          # Base ratio of working adults to dependents
WORKING_ADULT_RATIO_SKEW_MAXIMUM = 2.0   # When the ratio of working adults to dependents is
                                         # skewed, it tends to correct itself, this value clamps
                                         # the maximum effect of this
```
`WORKING_ADULT_RATIO_SKEW_MAXIMUM` is the knob for the SPEED of self-correction. Raising it lets a
badly skewed state recover faster. It is a plain define override, the same partial-NEconomy pattern
`PvtCapCtrlMod/common/defines/zw_cpc_defines.txt` already uses. Engine-global, all countries.

The second lever raises the TARGET rather than the speed: `state_working_adult_ratio_add` on a
state modifier or state trait (base 0.25 -> 0.30 today via the women's law). A bigger gap pulls
harder as well as ending higher.

## The migration hypothesis has a named mod driver - test it

`NoUSChickenMod/common/static_modifiers/nous_warbonds_modifier.txt`:
```
nous_migrant_magnet = {           # permanent, no duration, on STATE_TEXAS + STATE_CALIFORNIA
    state_migration_pull_add = 30
    state_migration_pull_mult = 1
    building_group_bg_manufacturing_throughput_add = 0.1
}
```
Its own comment says "extreme migration magnets. TUNABLE." Texas carries it in the save, and Texas
is the one state of the four sitting at its theoretical maximum ratio while the GBR home states are
at a third of theirs. GBR runs `law_migration_controls`.

Whether Vic3 migration moves working adults preferentially and leaves dependents behind is NOT
asserted here - that is the test: remove `nous_migrant_magnet` (or drop the pull to a fraction) and
re-run, then compare Wales's per-type ratios. It is the only mod modifier in the save touching
migration for a major destination.

## actinfo update

- T224 (new): decide whether `nous_migrant_magnet` at +30 flat / +100% pull, permanent, is intended.
- T225 (new): consider a `WORKING_ADULT_RATIO_SKEW_MAXIMUM` override if states are to recover faster.
- T226 (new): to get pop history, take periodic UNCOMPRESSED saves; the framework cannot read
  compressed ones, and it should say so instead of writing empty CSVs.
