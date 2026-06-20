# In-game observations — Top40EcoBoostMod

Run 1 day as **PAN** (then optionally a Phase-2-length game). The **Timeline** tab now shows
every placement as a clean table (Year | Country | Building | Type | Levels) with a country
filter + pagination — use it instead of grepping debug.log. (Build label is in the header above.)

## What to watch, and when
| When | What to check | BDD# |
|------|---------------|------|
| Day 1, as PAN | champ fabric stacked in best Punjab state; support goods built; flavour RGOs +1 each. | 1, 2, 3 |
| Day 1, modifiers | 3 category throughput modifiers (+50% + wage, 20yr) + global +4 SoL / +0.25 edu (whole game). | 6, 7 |
| Each Jan-01 | pulse re-spreads champ/support to states (incl. newly-annexed), cap-aware — no over-build. | 4, 5 |
| When world gets **pumpjacks** | OMA gains the tech + up to 5 oil_rigs (once). | 8 |
| When world gets **rubber_mastication** | BRZ + SIA gain tech + rubber_plantations (once). | 9 |
| Whole run | error.log free of eco.* errors; no "Invalid right side … 'c'" after annexations. | 11, 12 |

## Marker contract (how the Timeline table is built)
Each placement logs: `$B$` building-name header → `eco_hit_<type>` (→ "ECO_PLACED champ|support|flavour")
→ `debug_log_scopes = yes` (Root = country, This = state). A build that errors instead shows in the
Log tab "Likely OURS" table (state.cpp = wrong history entry; building_manager.cpp = runtime over-build).

## Latest triage (update each run)
- Prior run: flavour 138/239, but 16 tags showed ZERO builds — traced to the dead-tag dispatch bug,
  now fixed via flag dispatch (`has_variable`). **T62: confirm all 40 fire this run.**
- Track-B over-capacity (T51): crude EXCLUDE of 0-cap states in place; proper capacity re-scan pending.
- **T52: port flavour to history** once a clean run confirms which builds + states.

## Human final thoughts
_(your overall read on whether the feature is delivered)_
