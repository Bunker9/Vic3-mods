# 2026-08-17 - workforce ratio re-check on DEBUG1.v3

Follow-up to `2026-08-16_gbr_sailor_bloat.md`. Question from the user: after the dependent /
workforce ratio fix, is any state still below a 20% workforce share of population?

## Source
Save `DEBUG1.v3` (242 MB, written 2026-08-17 09:43), parsed by Framework-SaveParse Set 1:

```
python Framework-SaveParse/run-save-parse.py --save ".../save games/DEBUG1.v3" --rerun
```
Pool: 146,750 pop rows, 899 states, 15,304 buildings, 193 countries.

## Query
Per state, ratio = sum(pops.workforce) / (sum(pops.workforce) + sum(pops.dependents)),
grouped on `raw_pops.location`, owner tag joined from `aggr_employment.csv` (state_id, owner_tag,
state_region).

## Result - 10 of 899 states below 20%

| ratio | pop | workforce | owner | state region |
|---|---|---|---|---|
| 13.89% | 29,257 | 4,063 | MON | STATE_MONTENEGRO (split 16777869) |
| 14.02% | 29,124 | 4,084 | MON | STATE_MONTENEGRO (split 16777846) |
| 14.29% | 7 | 1 | (none) | STATE_EAST_SAHARA (split 372) |
| 15.82% | 346,518 | 54,824 | PAN | STATE_NORTHERN_BALUCHISTAN |
| 16.89% | 82,760 | 13,981 | MOR | STATE_EAST_SAHARA |
| 18.63% | 674,229 | 125,620 | PLT | STATE_SANTA_FE |
| 19.04% | 631,160 | 120,146 | MOR | STATE_ORAN |
| 19.37% | 666,191 | 129,039 | PLT | STATE_TUCUMAN |
| 19.40% | 1,553,590 | 301,470 | SPA | STATE_ARAGON |
| 19.86% | 598,271 | 118,794 | PLT | STATE_CORRIENTES |

Distribution: 0-15% = 3 states, 15-20% = 7, 20-25% = 293, 25-30% = 503, 30%+ = 93.
Median 26.29%, min 13.89%, max 48.08%.

## The old offenders are gone
GBR (35 states) now runs min 24.27% / median 29.88% / max 31.52%.

| state | 2026-08-16 save | DEBUG1.v3 |
|---|---|---|
| STATE_WALES | 9.5% | 24.27% |
| STATE_LANCASHIRE | 6.9% | 25.62% |
| STATE_HOME_COUNTIES | 17.7% | 27.73% |

## Reading
No state carries the old 3x dependent skew. The 10 remaining sub-20% states are small or
peripheral (two Montenegro splits, a 7-pop Saharan rump, Moroccan desert, Plata interior) and sit
just under the line rather than at a fraction of it. Nothing here reproduces the Wales/Lancashire
pattern.

NOT measured: why the surviving 10 sit low. No dependents-per-worker breakdown was run for them.
