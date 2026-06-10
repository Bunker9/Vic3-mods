# BDD — Top40EcoBoostMod (eco capped-placement)

Fill the **Y/N** column (your in-game observation). `Exp` = expected answer (don't edit);
the report asserts your answer vs Exp and flags mismatches. Re-run the master script + F5.

| # | Question | Exp | Y/N | Comment |
|---|----------|-----|-----|---------|
| 1 | Did every target nation (PAN, PRU) receive its champ / support / flavour buildings? | Y | Y |  |
| 2 | Did the champ good build to its cap (PAN cotton = 10, PRU steel = 14)? | Y | Y |  |
| 3 | Did the remainder stack into the single MOST-PRODUCTIVE state (≈9 in best + 1 elsewhere)? | Y |  Y|  |
| 4 | Were levels SPREAD across states (1 each) before the remainder, not all in one? | Y | Y |  |
| 5 | Did each support good build to 1×X (PAN = 5, PRU = 7)? | Y | Y |  |
| 6 | Did each flavour building build exactly 1 level? | Y | Y |  |
| 7 | Were buildings placed only where can_construct_building passed (no invalid placements)? | Y | Y |  |
| 8 | Did the Phase-1 modifiers (champ throughput, champ+support SoL, wage) load at the right scope? | Y | Y |  |
| 9 | At year 20, did the Phase-2 champ state modifier apply and persist to game end? | Y | Y |  |
| 10 | Are the eco state flags cleaned up (no leftover eco_*_here variables after setup)? | Y | Y |  |
| 11 | Was error.log free of eco-related errors (no Unknown effect / invalid scope)? | Y | Y |  |
