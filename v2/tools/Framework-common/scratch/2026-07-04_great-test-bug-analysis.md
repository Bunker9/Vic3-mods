# Manual analysis — GREAT_TEST.v3 + logs (2026-07-04)

Save: GREAT_TEST.v3 (1900s late-game). Framework read error.log+game.log+debug.log = 3968 err / 111 sigs.
Paths: G = testbook/v2/tools/Game-Victoria3 ; LD = <Documents>/Paradox Interactive/Victoria 3/logs
These are the queries the framework SHOULD run itself per-mod-feature (T108). Reproducible below.

## Q1 — log accounting (the "69K"): what is read vs not
```bash
grep -icE 'error|invalid|failed|wrong' "$LD/error.log"          # 3249 (READ)
cat "$LD"/error.[1-9].log | grep -icE 'error|invalid|failed'    # 2358 (ROTATED, NOT read by config_logtriage)
cat "$LD"/*.log | wc -l                                          # 88173 total lines (mostly info/debug)
```
FINDING: framework reads only current error.log; 69K = total log volume. config_logtriage [logs] could add error.[1-9].log.

## Q2 — top error signatures (the bug list)
```python
import csv; rows=list(csv.DictReader(open(rG+r"\log-CURR\_global\error_patterns.csv",encoding="utf-8")))
rows.sort(key=lambda r:int(r['count'] or 0),reverse=True)
for r in rows[:30]: print(r['count'], r['signature'][:105])
```
FINDING (top): 858 NAVAL_BATTLE invalid promote + 858 BATTLE_SHIPS_BREAKDOWN loc (VANILLA naval UI); 566 value-wrong-type
command_values.txt:373 (VANILLA); 483 Script system error + 459 Script location + 392 Invalid-right-side (MOD, see Q3);
131 range directive (vanilla); 24/21/17 scope errors -> 01_character_ideologies.txt (VANILLA).

## Q3 — attribute the 392x "Invalid right side during comparison 'c'"  (THE mod bug)
```bash
grep -iE -A1 "Invalid right side during comparison" "$LD/error.log" | grep -iE "Script location"
# 392  Script location: common/decisions/stdinnv_decisions.txt:41
sed -n '40,42p' mod1-inov/SteadyInnovMod/common/decisions/stdinnv_decisions.txt   # READ-ONLY
# 41: this = c:CHI   (inside AND = { this = c:CHI  is_country_type = recognized })
```
FINDING: SteadyInnovMod stdinnv_decisions.txt:41 malformed comparison, 392x. #1 mod bug. Verify is_country_type trigger + this scope.

## Q4 — mod-prefix attribution across error lines (shows the attribution GAP)
```bash
for p in mdp_ eco_ expmkt_ infratax_ nous_ zw_ stdinnv_ desi_ knip_; do echo "$p $(grep -icE "$p" "$LD/error.log")"; done
# only stdinnv_=392; all others 0  -> eco/pvtcap/expmkt errors are NOT token-tagged in the log (T108 needs feature reasoning, not grep)
```

## Q5 — PvtCapCtrl over-cap (save), verdict breakdown
```python
rows=list(csv.DictReader(open(rG+r"\save-CURR\PvtCapCtrlMod\aggr_census_overbuild.csv",encoding="utf-8")))
from collections import Counter; print(Counter(r['verdict'] for r in rows))
```
FINDING: 84 OVER_BY_*_ENGINE_OVERBUILD (0 mod-script-error). Biggest JAP Kanto food_industry 364/cap208 (+156), Kansai 361/166,
RUS Oryol 342/139. Cap prevents NEW build but does not demolish pre-existing/engine-overbuilt industry. eco-boosted JAP blows past cap.

## Q6 — GOODS PRICE diagnostic (T108 candidate: cheap-global + >25% over base)
```python
goods={r['goods_id']:(r['goods_name'],float(r['base_price'])) for r in csv.DictReader(open(rG+r"\save-CURR\goods_ids.csv"))}
for r in csv.DictReader(open(rG+r"\save-CURR\raw_market_goods.csv")):
    nm,base=goods[r['goods_id']]; cur=float(r['price_current']); pct=(cur-base)/base*100
    if pct>25 or pct<-25: print(nm, base, round(cur,1), f"{pct:+.0f}%")
```
FINDING: OVER +25% (shortage): Manowars +75%, Ironclads +75% (naval war), Radios +34%, Telephones +26%, Rubber +27%.
CHEAP <-25% (glut): Aeroplanes -72%, Merchant Marine -64%, Tanks -50%, Tobacco -27% (military-industrial overproduction; poss. eco over-seed).

## Q7 — feature liveness (persisted logic vars; fp=0 this run since fingerprints OFF)
```
aggr_save_matches rows: PvtCap 675 | eco 96 | stdinnv 40 | mdp 35 | expmkt 19 | knip 2 | desi 2 | nous 0 | InfraTax 0 | vt 0
```
FINDING: InfraTax + versiontest persist nothing (InfraTax trait doesn't persist a var = expected). fp=0 all (toggled off).

## SUMMARY OF MOD BUGS
1. SteadyInnovMod stdinnv_decisions.txt:41 - "Invalid right side comparison 'c'" x392 (HIGH).
2. PvtCapCtrl - 84 states over industry cap (engine-overbuild; cap leaky vs pre-existing), JAP heaviest.
3. EcoBoost/ExpMkt - RGO seeding overbuilds (Mindanao/Mysore/Tenasserim/Sunda/Rheinland/Ruhr/Kerman), minor.
4. Economy - military-goods glut (Aeroplanes/Tanks/Merchant Marine) vs warship+tech shortage.
Vanilla (ignore): naval-battle UI (1716), command_values (566), character_ideologies scope (38).

## Q8 — ACTINFO COVERAGE % (to_det_mod_feature token set vs CURR data)
Method (user): for each feature in to_det_mod_feature.csv, take its token SET; check if ANY token appears in any
CURR log/save output (haystack = save-CURR/raw_flags + log-CURR/raw_errors + raw_loglines + all per-mod
aggr_save_matches + aggr_log_matches). Feature covered iff >=1 token hit. actinfo% = covered/total.
```python
# tokens: [a-z][a-z0-9_]{4,} from evidence_set, has '_', len>=6, minus a stoplist; expand ()/*//
# hit = any(tok in haystack.lower())
```
FINDING: 10/25 = 40%. Per mod: PvtCap 1/1, MyDiplo 3/4, Kampai 2/3, SteadyInnov 2/3, Top40 1/3, Desi 1/5,
ExpMkt 0/1, InfraTax 0/1, NoUS 0/3, versiontest 0/1.
15 features have ZERO actinfo (invisible): all NoUS wars/warbonds, Desi unify/rebuild/treaties/warbonds, eco
picker + oil-rubber, ExpMkt, InfraTax, Kampai marine, mdp expander-wars, stdinnv AUS/HUN flavour.
ROOT CAUSE: fp is toggled OFF -> features that fingerprint into the save are invisible; only features with
persisting LOGIC vars (PvtCap cap, mdp war stamps, stdinnv status) or that ERRORED (stdinnv decision) show up.
The fp system EXISTS to raise this ~100%; with fp ON coverage jumps. Caveat: depends on to_det token-set
completeness (ExpMkt persisted 19 vars that did not map to a listed feature token -> refine the feature list).
