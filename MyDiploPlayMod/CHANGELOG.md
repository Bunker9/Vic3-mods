# MyDiploPlayMod — Changelog

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
