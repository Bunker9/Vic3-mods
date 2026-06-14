# BetterPopPromoMod — Changelog

## v0.1.1-dev (2026-06-14) — tiered tech/law gating + PRU/PAN/SOK test unlock + BIC promo test event

**Motivation (user):** as a human player you can beeline the techs/laws needed for the
v0.1.0 modifiers almost immediately, but the AI researches on its natural timeline — so a
flat, always-on grant would give the AI a wildly out-of-era GDP/SoL spike. Split the
mechanic into two tiers gated behind tech/law progress, and add fast paths for the
dev/exp test nations (PRU/PAN/SOK) plus a BIC-only promotion test event.

### Tiered rollout (`common/static_modifiers/bpp_modifiers.txt`, `bpp_triggers.txt`, `bpp_effects.txt`)
- **Tier 1** — unlocked by era_1 tech `academia` ("Unlocks University building"). Grants
  `bpp_qualifications_boost_t1` (state-scoped, half-strength): `state_pop_qualifications_mult
  = 0.25`, `state_literacy_growth_add = 0.0025`, `state_peasants_education_access_add = 0.15`.
- **Tier 2** — unlocked by era_2 tech `egalitarianism` OR already running `law_multicultural`.
  Replaces tier 1 with full-strength `bpp_qualifications_boost_t2`
  (`state_pop_qualifications_mult = 0.5`, `state_literacy_growth_add = 0.005`,
  `state_peasants_education_access_add = 0.30`) and adds the country-scoped
  `bpp_global_acceptance` (the `country_acceptance_no_shared_*_trait_add = 30` cultural-
  discrimination fix from v0.1.0).
- Per-country one-shot gating via `bpp_tier1_done` / `bpp_tier2_done` variables, checked
  yearly (`bpp_yearly_check`, fired by the new `bpp.2` hidden event via
  `on_yearly_pulse_country`) and once at game start (covers advanced starts that already
  have the tier-2 tech/law).

### Test-nation early unlock (`common/on_actions/bpp_on_actions.txt`)
At game start, PRU/PAN/SOK get `bpp_apply_tier2` immediately (bypassing the tech/law gate),
so the champ/support synergy from Top40EcoBoost can be tested without waiting decades for
research. The human player among them gets a one-time toast (`bpp.3`, "Reform Programs
Accelerated").

### New: BIC pop-promotion test event (`bpp.4`)
Hidden, BIC-only, fires every `on_yearly_pulse_country`. For each of BIC's 3 most populous
states, converts one lower-strata pop with ~8K-15K workforce (not already in the target
type) directly via `change_poptype`:
- one pop -> `bureaucrats`
- one pop -> `officers`
- one pop -> `academics`, only if the state `has_building = building_university`

This is a blunt, visible lever for observing how much faster promotion-driven GDP/SoL gains
show up once BIC's cultural-discrimination penalty is addressed — independent of (not
gated behind) the tier-1/2 mechanic above.

## v0.1.0-dev (2026-06-14) — initial scaffold: global acceptance + qualifications boost

**Motivation (user):** after a test run to the 1900s, pop promotion into higher strata
(clerks/bureaucrats/academics/officers/engineers) felt stuck — especially in nations like
BIC (East India), where ~100% of pops do not share the primary culture/religion.

**Root cause (verified `common/pop_types/bureaucrats.txt`, `academics.txt`, `officers.txt`,
`engineers.txt`):** the qualifications formula for promotion into these pop types is
`(literacy_rate - threshold) * factor`, then:
- ×1.5 / ×2.0 if the pop's `pop_acceptance >= acceptance_status_4 / 5` (60 / 80, see
  `common/script_values/event_values.txt`)
- ×0.1 ("QUALIFICATIONS_CULTURAL_DISCRIMINATION") if the state's cultural acceptance for
  that pop's culture is **below** `acceptance_status_4` (60)

So a nation whose pops share none of the ruling culture's heritage/language/tradition/
religion gets hit with the 0.1x penalty AND misses the 1.5x/2x bonus — promotion into
these strata is effectively frozen, regardless of literacy.

### New modifiers (`common/static_modifiers/bpp_modifiers.txt`)
- **`bpp_global_acceptance`** (country-scoped, permanent): `country_acceptance_no_shared_
  {heritage,language,tradition,religious}_trait_add = 30` each — verified vanilla tokens
  (`common/modifier_type_definitions/06_country_modifier_types.txt`), flat 0-100 acceptance
  points. Roughly double the best single vanilla law source (-25..+15 range across
  `00_church_and_state.txt` / `00_citizenship.txt`). For a pop sharing nothing with the
  primary culture this alone clears `acceptance_status_4` and, combined with almost any
  non-hostile law, `acceptance_status_5` — **no law change required**.
- **`bpp_qualifications_boost`** (state-scoped, permanent): direct accelerants on the
  literacy/qualifications pipeline that feeds every pop type's promotion roll —
  `state_pop_qualifications_mult = 0.5` (vanilla max single source 0.25),
  `state_literacy_growth_add = 0.005` (vanilla max single source 0.0005),
  `state_peasants_education_access_add = 0.30` (vanilla max 0.20, targets the
  "QUALIFICATIONS_FAVORED_TYPE" laborer/peasant pool that feeds clerk promotion).

### Application (`common/on_actions/bpp_on_actions.txt` + `common/scripted_effects/bpp_effects.txt`)
`on_game_started_after_lobby` -> `bpp_startup` -> every existing country gets
`bpp_global_acceptance`; every state of every country gets `bpp_qualifications_boost`.
Global, not limited to the 40 Top40EcoBoost target nations.

### Status
- **Scaffold only — NOT yet in-game tested.** Per user instruction, this branch
  (`dev/betterpoppromo`, separate worktree at `mod1-bpp/`) stays untested until the
  in-progress `dev/exp` (MyDiploPlayMod truces/Oman + Top40EcoBoost wage/edu) work is
  finished and merged.
- TODO: consider whether `bpp_qualifications_boost` should exclude un-incorporated /
  colonial subject states (would need `is_homeland`-style gating) vs. applying to all
  states uniformly as it does now.
- TODO: verify in-game that `every_country = { limit = { exists = this } ... }` correctly
  covers all alive countries (including unrecognized) without erroring on dead tags.
