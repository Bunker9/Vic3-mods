# MyDiploPlayMod — Changelog

## v0.6.5-dev (2026-06-13) — 3rd triage: faulty neighbour selector + dead-tag spam + 1846 stop
In-game (Oct 1839) PAN at peace declared on a gutted, non-adjacent SPA; log also showed
DAI → Ashanti. Root causes:
- **`any_neighbouring_country` is NOT a real Vic3 trigger** (vanilla has zero generic uses; only
  `any_neighbouring_country_has_same_movement_type_as_root`). The engine no-op'd the unknown
  trigger in the `limit`, so **no adjacency filtering happened** and `ordered_country` just took
  the globally weakest valid country. Fixed: real land-adjacency inside `mdp_valid_generic_target`
  via `any_scope_state = { any_neighbouring_state = { owner = scope:mdp_attacker } }`; removed the
  phantom trigger from the `ordered_country` limit and from (unused) `mdp_can_blob_now`.
- **942× "Invalid right side during comparison 'c'"** (`mdp_triggers.txt:10`): a `this = c:TAG`
  in the expand-tag list errors once that tag is **annexed mid-game**. Split into `mdp_is_expand_tag`
  (raw list, used only at game start where all 20 are live) and `mdp_is_expand_country`
  (`has_variable = mdp_expander`); `mdp_startup` now `set_variable = mdp_expander` on each live
  expander. Runtime never references a dead `c:TAG` again.
- **Stop date** (user): monthly chain now gated on `game_date < 1846.1.1` — the blob chain runs
  ~10 years then stops.
- Non-diplo this run: 36× `military_formation` untyped-trigger (naval mission types — not ours)
  + 1× vanilla `31_ship_transfer.txt:56`.

## v0.6.4-dev (2026-06-13) — restore user's curated day-1 wars (c6216fb), fix tokens
Reverted the script-regenerated `zz_mdp_wars.txt` back to the user's hand-curated version from
commit **c6216fb** — the correct country matchups with bad/GP-dragging wars commented out
(BIC's 3rd, PRU, PER's). Then corrected tokens:
- **Validated all 110 `STATE.region_state:TAG` refs** against 1836 ownership — **0 invalid**
  (every state is genuinely owned by its referenced tag at start). Matchups confirmed good.
- **War goals `conquer_state` → `return_state`** (`dp_conquer_state` → `dp_return_state`): the
  high-infamy token the user flagged. Verified **all 60 active war goals have a backing
  `add_claim`** in `zz_mdp_claims.txt` (0 missing), so return_state is valid.
- **`zz_mdp_wars.txt` is now hand-maintained**: header updated, and `gen_blob_plan.py` no longer
  writes it (still generates claims + pops). Restored `zz_mdp_claims.txt` + `zz_mdp_seed_pops.txt`
  from c6216fb too, to stay consistent with the curated war set.
- **Status: re-armed for a test run.**

## v0.6.3-dev (2026-06-13) — cap day-1 wars at 2 per expander
- Generator (`gen_blob_plan.py`): **`MAX_WARS_PER_EXPANDER = 2`** (user). Previously every CSV
  target became a simultaneous day-1 war (PAN had 7) → infamy explosion + the AI juggling fronts
  it can't win. Now each expander declares only its **first two** targets; the rest keep their
  claims/homeland/pops so the runtime chain (or manual play) can still take them.
  Day-1 plays dropped **71 → 35**. SOK → OYO+BEN. (Reorder the CSV to change which two.)
- **Removed BHW from PAN's targets**: Bahawalpur is BIC-owned, so attacking it would pull a great
  power into the war. PAN now → **SIN + KAL**.
- **Status: re-armed for a test run.**

## v0.6.2-dev (2026-06-13) — 2nd triage: trigger scopes, decentralized guard, day-1 return_state
Second in-game run. v0.6.1 fixes held (power_bloc + add_claim errors gone); this run exposed
trigger-name/scope bugs that were previously masked:
- **`has_state_religion` wrong scope** (383×): it's a POP trigger. The EGY guard now uses the
  country form `religion = rel:oriental_orthodox`. (This also cleared the cascading
  "Unknown trigger type: is_unrecognized / any_neighbouring_country" parse noise.)
- **Decentralized guard** (user): SOK and PAN are themselves *unrecognized*, so the old
  `is_unrecognized = no` filter left them no valid targets. Replaced with
  `NOT = { is_country_type = decentralized }` — allows unrecognized targets but never
  decentralized/primitive nations. Applies to **all** expanders.
- **"No diplo play in progress" guard** (user): added `is_active_in_diplomatic_play = no` to the
  monthly on_action + `mdp_can_blob_now`, so an expander only searches for a target when at peace
  AND not already maneuvering a play.
- **Day-1 history wars → `return_state`** (generator `gen_blob_plan.py`, regenerated): PAN never
  conquered Sindh because the day-1 `conquer_state` war white-peaced (high infamy / AI gives up).
  All 71 day-1 plays now use `dp_return_state` + `return_state`, reclaiming the states that
  `zz_mdp_claims.txt` already claims — low infamy, AI presses harder.
- Remaining: the 74× `31_ship_transfer.txt:56` errors are **vanilla** (backlog T28), not ours.
- **Status: re-armed for a third in-game test.**

## v0.6.1-dev (2026-06-13) — in-game triage: infamy + scope errors
First in-game run of the runtime chain. Wars fired, but expanders spiked infamy and got
clobbered by GPs, and the log flooded. Root causes + fixes:
- **`add_claim` ran in the wrong scope** (wrapped in `scope:mdp_attacker = {}` → country scope;
  error *"Wrong scope: country, expected state_region"*, 20×). So **claims/homeland were never
  granted at runtime** → every war goal cost full infamy. Fixed: `add_claim = scope:mdp_attacker`
  called directly in the `every_scope_state` (state) scope.
- **War goal switched `conquer_state` → `return_state`** (`dp_conquer_state` → `dp_return_state`):
  base infamy **2 vs 5**, and it reclaims the *claimed* states Step 3 grants — the lowest-infamy
  way to annex whole states (per user). Requires the claim, which we now set first.
- **`power_bloc` guard threw** *"target link 'power_bloc' returned an invalid object"* (215×) on
  bloc-less countries. Fixed: `exists = power_bloc` (idiomatic, error-free).
- **Infamy gate 75 → 30** in the monthly on_action + `mdp_can_blob_now` — well below the ~50
  "pariah" line, so an expander never queues a new war while already drawing GP attention.
- **Killed ~338 debug-log loc-parse errors**: stripped `[Data.Function]` brackets from all
  `debug_log` strings (they don't resolve here — same lesson as Top40); rely on
  `debug_log_scopes = yes` for identities.
- Untouched & confirmed clean in the run: `ordered_country`, `create_diplomatic_play`,
  `add_war_goal`, `create_pop`. (Note: the 74× `31_ship_transfer.txt:56` errors are **vanilla**, backlog T28.)
- **Status: re-armed for a second in-game test.**

## v0.6.0-dev (2026-06-12) — runtime blob chain re-enabled + scope fixes
Rebuilt and re-armed the monthly generic conquest chain (`mdp.1` → `mdp_try_next_war`),
plus the new target-filter conditions discovered going in depth:
- **Target filter (`mdp_valid_generic_target`)**: now also excludes anyone **in a power bloc**
  (member OR leader, via `mdp_is_in_power_bloc`) — stops PRU/SWE/SAR dragging a GP into the war
  through `call_to_arms`. EGY additionally never targets **Oriental Orthodox / Ethiopian-culture**
  countries (`mdp_egy_forbidden_target`: oriental_orthodox, amhara/oromo/tigrinya/somali).
- **Target pick fixed**: `random_country` (ignored `order_by`) → **`ordered_country … position = 0`**
  so it actually picks the *weakest* (lowest-prestige) valid neighbour.
- **Effect syntax fixed**: `add_claim` / `add_homeland` switched from invalid `{ target = }` /
  `{ culture = }` block forms to the direct form; `create_pop` now sets `religion`.
- **Play fixed**: `dp_conquest` → **`dp_conquer_state`**; secondary (non-capital) war goals are now
  added in the `random_diplomatic_play` scope (can't loop `add_war_goal` inside `create_diplomatic_play`).
- Attacker pre-flight (`mdp_can_blob_now`) + on_action gate: `infamy < 75`, at peace, has a valid target.
- **Status: not yet in-game tested** — armed on dev/exp for this test run.

## v0.5.0-dev (2026-06-12) — full redo (infamy / partial-conquest / white-peace)
**Root causes:** wars were declared at **runtime** in the on_action → every expander got
huge day-1 infamy; war goals targeted only the **capital** state → partial, unincorporated
conquests that white-peaced (Punjab took only Kandahar; Morocco/Oman white-peaced).

New design — everything that makes conquest stick is now in **history**, auto-generated:
- **`hk-config/tools/gen_blob_plan.py`** reads `blob_targets.csv` + game files (state
  ownership, primary cultures) and emits:
  - `common/history/diplomatic_plays/zz_mdp_wars.txt` — ONE day-1 conquest war per expander
    (its first target), with a `conquer_state` war goal for **every** state that target owns.
  - `common/history/states/zz_mdp_claims.txt` — `add_homeland` (expander culture) + `add_claim`
    on every state of **every** listed target → low-infamy, fully-incorporated conquest.
  - `common/history/pops/zz_mdp_seed_pops.txt` — seeds a 10 000 primary-culture+religion pop in
    each target state so conquered land isn't 100% foreign. Religion = the rulers' faith
    (culture default, e.g. panjabi→sikh; `RELIGION_OVERRIDE` for exceptions like OMA→ibadi).
    `EXTRA_SEED` adds more (Punjab also gets 3 000 panjabi/hindu).
- History start = **no runtime infamy**. `mdp_infamy_decay` (10 yr) still granted via on_action.
- Removed the old runtime `mdp_declare_war` effect.

### Generic event-driven blob chain (replaces the old "war target order")
- **Day-1 history wars now cover ALL curated targets at once** (e.g. PAN vs SIN+BHW+KAL+KAN+
  HER+KUN+KAF), not just the first — 71 wars across 20 expanders.
- **`on_monthly_pulse_country` → `mdp.1` → `mdp_try_next_war`**: while an expander is at peace,
  it picks its **nearest weakest recognised neighbour** (not an expander/GP/GP-subject;
  `mdp_valid_generic_target`), gives itself **claim + homeland + 10k seed pop on every state**
  of that target at runtime, then declares a **full-state conquest war** (capital = primary
  demand; remaining states added via the vanilla `random_diplomatic_play` goal-loop pattern).
- One war at a time (gated on `is_at_war = no`); `infamy < 75` guard + `mdp_infamy_decay`
  keep it from coalition suicide. No hard year-stop — it naturally halts when no valid
  recognised neighbour remains (i.e. it borders only GPs/expanders).

### Known limits / TODO (verify in-game)
- Runtime primitives assumed valid but UNTESTED: `ordered_neighbouring_country` + `order_by =
  army_size`, runtime `add_homeland`, `scope:mdp_tgt.capital`, `infamy` comparison. Triage error.log.
- `blob_targets.csv` is the prior hand list — not auto-derived from map adjacency/strength.
- Generic seed pops use culture-DEFAULT religion (no override map at runtime, unlike history).

## Runtime flow
Game start: history applies the day-1 wars + claims + homeland + seed pops; on_action grants
`mdp_infamy_decay` to every expand tag for 120 months.

## Regenerate
`python hk-config/tools/gen_blob_plan.py` (writes the three history files + `blob_plan.csv`).
