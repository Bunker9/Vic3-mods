# BDD — MyDiploPlayMod

One Y/N question **per feature**. Fill the **Y/N** column with your in-game observation;
`Exp` = expected answer (the report asserts Answer == Exp). Build label is shown in the
section header (auto-read from the versiontest stamp in debug.log).

| # | Feature | Question | Exp | Y/N | Comment |
|---|---------|----------|-----|-----|---------|
| 1 | Day-1 history war | Does PAN start ALREADY AT WAR with SIN at game start, goal `return_state`? | Y | | diplomatic-play panel |
| 2 | Day-1 claim | Does PAN hold a claim on STATE_SINDH from turn 0? | Y | | PAN → claims |
| 3 | Monthly blob (mdp.1) | Do active expanders (MEX/BRZ/CLM…) keep starting monthly wars through ~1846? | Y | | war log grows |
| 4 | Soft-remove | Are BIC/PRU/EGY/SAR/SWE limited to their day-1 war only (no monthly follow-ups)? | Y | | mdp.1 sealed for them |
| 5 | Subject annex (mdp.3) | In 1846–1851 do DAI/BUR/SIA/PAN start a `dp_annex_subject` play on their weakest subject? | Y | | only when at peace |
| 6 | Annex window closes | After 1851.12.31, does mdp.3 stop firing (no new subject annexations)? | Y | | window guard |
| 7 | Split infamy decay | Does the long-set (SEA + PAN/SOK/SHW/SAF/ARG/BRZ) show ~10yr decay, others ~3yr? | Y | | modifier tooltip |
| 8 | create_pop removed | Are there NO injected pops and NO `create_pop [Missing culture]` errors? | Y | | logic dropped entirely |
| 9 | Region truces | Are same-region truces present (OMA-PER, BIC-PAN, OMA-SHW) and cross-continent ones absent? | Y | | diplomacy → truces |
| 10 | SIA/DAI restraint | Does SIA STAY OUT of DAI's annex war on its subject CAM? | Y | | T64 — truce only so far; may be N |
| 11 | Clean log | Is error.log free of mdp.* / diplomacy-history errors (claims/homelands wrapped in state_region)? | Y | | |
