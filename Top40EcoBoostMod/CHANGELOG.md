# Top40EcoBoostMod — Changelog & Process Flow

> Updated after every change set (per process). Newest on top.

## v0.2.3 — remainder actually builds (create_building level=, not add_building_level)  (2026-06-10)

**Bug from v0.2.2 test:** the remainder phase used `add_building_level`, which is **not a
real scripted effect** ("Unknown effect" ×15 in error.log) — so the bulk levels never got
built (Punjab cotton stayed at 2, not 10; the `eco_hit` marker logged anyway, so the census
falsely read 10/10). The saved-scope `while` also threw "invalid object" ×7 (stale
`scope:eco_best_state` on buildings with 0 constructible states).

**Fix (per CWTools script-docs):** `create_building` supports `level = <script_value>`, and
*"if a building already exists, level = max(scripted, existing)"*. So `eco_seed_capped` now:
1. counts constructible states **S** (country var),
2. computes the best state's level = `1 + (N − S)` when `N > S`, else `1`,
3. iterates states highest-gdp first: the **best (first) state is built to its full level in
   ONE `create_building { level = ROOT.var:eco_bestlevel }` call**; every other state gets
   `level = 1`; capped at N total levels.
No more `add_building_level`, `save_scope_as`, or remainder `while` over a saved scope →
both error classes gone. The best state emits one `ECO_PLACED` marker **per level** (small
`while` over a counter) so the triage census counts LEVELS, not states.

## v0.2.2 — capped placement (spread + remainder-to-best) + logger fix  (2026-06-10)

**The Punjab "only 2 cotton" fix.** v0.2.0 built 1 level per constructible state, so
Punjab got just 2 cotton (only 2 states could host it) instead of the intended cap.
New rule (`eco_seed_capped`, replaces `eco_seed_spread` + `eco_seed_one`):

- Build a **target N levels** of a building, distributed: **1 level in each constructible
  state, highest-GDP first**, then **any remainder (N > #states) dumped into the single
  most-productive state**. Totals exactly N in both regimes:
  - `N <= #states`: 1 level in the **top-N states only** (cap respected, no overflow).
  - `N >  #states`: 1 level in every state **+ (N−#states) extra in the best state**.
- Caps wired from X (mod-nations.csv): **champ = 2·X, support = 1·X each, flavour = 1**.
  PAN X=5 → cotton 10 / each support 5 / flavour 1. PRU X=7 → steel 14 / each support 7.
- Mechanics verified vs game files: `add_building_level = { building level=1 }` grows the
  best state; `while = { limit = { var:eco_placed < N } }` loops the remainder;
  `ordered_scope_state order_by=gdp` is highest-first (vanilla coup picks top-GDP state at
  `position=0`); `save_scope_as`/`scope:` + `exists = scope:` guard the loop.

**Logger fixed (real bug, not a CWTools false positive).** v0.2.0's
`debug_log = eco_log_<type>` used `[ROOT.GetName]`/`[SCOPE.GetName]` data functions, which
**do not resolve in debug_log** → "Failed converting statement" spam (~75 error.log lines)
and blank output. Removed those loc keys. Now: `debug_log = $B$` (building name header,
works) + `debug_log = eco_hit_<type>` (clean static "ECO_PLACED" marker, countable) +
`debug_log_scopes = yes` (state identity). No data functions → no error spam.

**Triage tooling.** New `sanity-check\triage-vic3-logs.ps1` parses debug.log + error.log
into a build census (placed-vs-expected-cap per building) and a benign-filtered real-error
list, saved to `sanity-check\reports\triage_<stamp>.md`. (Folder convention: `sanity-check\`
= test scripts + post-test reports; `tools\` = mod-design data analysis + housekeeping.)

**Files:** `eco_effects.txt` rewritten (eco_seed_capped + updated PAN/PRU config +
cleanup of `eco_best_here`/`eco_placed`); `eco_l_english.yml` (−3 log keys, +3 eco_hit
markers); all eco script `.txt` re-stamped UTF-8 BOM (4 had regressed to no-BOM).

## v0.2.1 — CWTools error fixes  (2026-06-10)

Fixed the validation errors flagged in VS Code:
- **Modifiers moved to the correct folder.** `add_modifier` resolves named modifiers from
  `common/static_modifiers/`, NOT `common/modifiers/` (the latter is not a loaded Vic3 dir,
  empty in vanilla). Moved `eco_modifiers.txt` → `common/static_modifiers/`. This clears the
  *"Expected value of type modifier_container"* errors on `eco_PAN/PRU_champ_tp_p1`,
  `eco_PAN/PRU_sol_p1`, and `eco_champ_state_p2`. All modifier TOKENS were already valid
  (each verified against game files: `building_<x>_throughput_add`, `building_group_bg_*_
  standard_of_living_add`, `state_standard_of_living_add`, `building_minimum_wage_mult`).
- **Phase-2 champ modifier now lasts to END OF GAME.** `eco.3` adds `eco_champ_state_p2`
  with NO `months` duration (was `months = 240` → would have expired at yr 40). Per intent,
  P2 runs from yr 20 to game end. Comments corrected in events + static_modifiers.

Accepted as CWTools **false positives** (game `error.log` is the authority):
- loc keys `eco_log_champ/support/flavour` "uses command ROOT/SCOPE ... data type None" —
  a loc key used only via `debug_log` has no inferable scope; data functions resolve at
  runtime. **Verify name-resolution during the in-game test pass.**
- `B`/`TYPE` "unexpected" in `eco_seed_spread` — CWTools does not validate custom
  scripted-effect parameters; `$B$`/`$TYPE$` substitution is correct Paradox syntax.

## v0.2.0 — generic eco engine (PAN + PRU), build-all-at-once  (2026-06-10)

**What the mod now is**
- A **target list** of nations (`eco_is_target_country`, v1 = **Punjab `c:PAN`**, **Prussia `c:PRU`**),
  each with a hard-coded config effect `eco_setup_<TAG>`.
- A **common tech grant**: every target nation gets **line_infantry + artillery + gunsmithing** at game
  start (so they can field line infantry + cannon artillery, and build artillery foundries).
- A **common build pass** that, per nation, places champ/support/flavour buildings, **SPREAD** across
  states (no concentration), gated by **`can_construct_building`** (won't place where invalid). States are
  temporarily flagged (`eco_champ_here`/`eco_support_here`/`eco_flavour_here`) and the flags are cleaned up
  at the end of the run.
- **Modifiers**: champ throughput **+200%** (building-type specific, 20 yr) + champ/support **SoL +2**
  (Phase 1, 20 yr, building-GROUP level) → champ **SoL +5** (Phase 2, from yr 20). All carry an `icon`.
- A **debug log** of everything placed (country → state, per type) via `debug_log` → the debug log file
  (not error.log). Lets you verify visually which states got what.

**Config table (the "what")** — `good(count)`; v1 builds *spread*, approximating counts:

| tag | champ | support | flavour |
|-----|-------|---------|---------|
| PAN | cotton_plantation | opium_plantation · sugar_plantation · tea_plantation · textile_mill | artillery_foundry · paper_mill · coffee_plantation · tooling_workshop · iron_mine · logging_camp |
| PRU | steel_mill | explosives_factory · chemical_plant · motor_industry | — |

**Files**
- `common/scripted_triggers/eco_target_triggers.txt` — the target list.
- `common/scripted_effects/eco_effects.txt` — generic effects + `eco_setup_PAN/PRU`.
- `events/eco_events.txt` — `eco.2` (build), `eco.3` (phase-2 swap).
- `common/on_actions/eco_on_actions.txt` — startup: grant techs + dispatch builds.
- `common/modifiers/eco_modifiers.txt` — the 6 modifiers (icons + tokens).
- `localization/english/eco_l_english.yml` — modifier names + log lines (UTF-8 BOM).
- **Removed** the old Punjab-only `punjab_ecoboost_*` files (superseded).

**Runtime process flow**
```
on_game_started_after_lobby
  └─ eco_startup (on_action)
       ├─ every target country: eco_grant_military_techs        (line_infantry, artillery, gunsmithing)
       └─ every target country: trigger_event eco.2
                                   └─ eco_setup_<TAG>
                                        ├─ eco_seed_spread (champ)   ─┐ flag state → create_building(1/state) → debug_log
                                        ├─ eco_seed_spread (support) ─┤  gated by can_construct_building
                                        ├─ eco_seed_one    (flavour) ─┘ best state, build 1, additive
                                        ├─ add_modifier champ_tp_p1 (240mo) + sol_p1 (240mo)
                                        ├─ trigger_event eco.3  (years=20)
                                        └─ eco_cleanup_flags
   ... year 20 ...
   eco.3 → add_modifier champ_sol_p2   (group-level)
```

**Known v1 simplifications / open items**
- **Counts approximated:** champ/support build **1 level per constructible state** (spread for coverage),
  not the precise `cap−start` count. Exact counts + 5-yr phasing + per-tick state recompute = **v2 TODO**.
- **Phase-2 champ SoL is GROUP-level** (no per-building-type SoL token exists) → it also touches the
  support siblings. **Open design call:** keep group-level / drop P2 SoL / make P2 throughput-only.
- **Needs an in-game test pass** (clear logs → launch as a country → read debug log + error.log). Several
  tokens are best-effort (`this = c:PAN` compare, `debug_log [SCOPE.GetName]`, `order_by = gdp`,
  `set_variable` on state) — error.log will confirm.

**Reference:** starting building counts (to tell our seed / AI builds apart from the 1836 original) live in
`tools/state_buildings.csv`. Design rationale in `roadmap/champ-support-picks.md`.
