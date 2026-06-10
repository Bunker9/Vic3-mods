# MyDiploPlayMod — Changelog & Process Flow

> Updated after every change set (per process). Newest on top.

## v0.2.0 — lowest-infamy return_state war + setup claim + infamy-decay test modifier  (2026-06-10)

**War goal switched to the lowest-infamy full takeover.** Verified all war-goal infamy
in game files (`common/war_goal_types/`, defines):
- `return_state` base infamy **2** (requires a claim) — the cheapest take-a-state goal.
- `conquer_state` / `annex_country` base **5** (conquer_state is *invalid* if you hold a
  claim; annex_country gives no claim/homeland discount).
Sindh (c:SIN) owns exactly **one** state (STATE_SINDH), so a single `return_state` on it
is a **full annex of Sindh at base infamy 2**. Play type → `dp_return_state`.

**Claim ("core") granted at game SETUP**, not via event — `return_state` needs the claim
from turn 0. New `common/history/states/00_sindh_pan_claim.txt` appends (additive block,
no create_state) `add_claim = c:PAN` + `add_homeland = cu:panjabi` to STATE_SINDH. This
mirrors the old FI-Light mod's `add_claim = c:PAN`. The runtime event keeps the same grant
as a belt-and-suspenders fallback.

**Test modifier: 50/yr infamy decay on Punjab.** New `diplo_infamy_decay_test`
(`common/static_modifiers/`) with `country_infamy_decay_mult = 9` → base 5/yr × (1+9) =
**50 infamy/yr**. Added to c:PAN for **120 months (10 yr)** in `diplo_test.1`, so Punjab
sheds the war's infamy well inside the **10-year window in which all expander nations must
finish their wars**.

**Runtime flow**
```
game setup:
  history/states/00_sindh_pan_claim.txt  -> PAN claim + Punjabi homeland on STATE_SINDH
  history/diplomatic_plays/00_punjab_sindh_war.txt (war=yes)
      -> PAN return_state STATE_SINDH  (base infamy 2)   [+ SIN counter: conquer STATE_PUNJAB]
on_game_started_after_lobby:
  diplo_test_startup -> c:PAN trigger_event diplo_test.1
      -> add_modifier diplo_infamy_decay_test (120 mo, 50/yr decay)
      -> (fallback) re-assert PAN claim/homeland on Sindh states
```

**Open / verify in-game:** that the war starts as return_state (check infamy cost shown is
~2-tier, not 5), the claim is present at turn 0, the decay modifier reads 50/yr, and the
war is winnable within 10 years.

## v0.1.0 — initial Punjab→Sindh start-of-game war (conquer_state)  (2026-06-09/10)
- `dp_conquer_state` war at setup; claims granted via diplo_test.1 event. Superseded by v0.2.0.
