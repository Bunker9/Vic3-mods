# BDD — MyDiploPlayMod (Punjab → Sindh start-of-game war)

Fill the **Y/N** column. `Exp` = expected answer (don't edit); the report asserts it.

| # | Question | Exp | Y/N | Comment |
|---|----------|-----|-----|---------|
| 1 | Does PAN start ALREADY AT WAR with SIN at game start (no maneuvering phase)? | Y | Y |  |
| 2 | Is PAN's war goal `return_state` (the lowest-infamy take-a-state goal, base 2)? | Y | Y |  |
| 3 | Does PAN hold a CLAIM on STATE_SINDH from turn 0 (static state-history grant applied)? | Y | Y |  |
| 4 | Did PAN win and annex the whole of Sindh? | Y | Y |  |
| 5 | Was the infamy gained from the annex negligible (low, not a coalition trigger)? | Y | Y |  |
| 6 | Does the 50/yr infamy-decay test modifier read correctly on PAN for 10 years? | Y | Y |  |
| 7 | Did the war resolve within the first 10 years (expander-war window)? | Y | Y |  |
| 8 | Was the EIC/BIC NOT dragged in (Sindh was independent, not a subject)? | Y | Y |  |
