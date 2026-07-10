# 2026-07-09 — stdinnv_unrecognized holders in the save, population-filtered

**Goal (user):** for the SteadyInnov on_action -> history conversion, pick the `stdinnv_unrecognized`
seed list = unrecognized nations with population > 3M (drop the many tiny unrecognized tags).

**Inputs (framework SaveParse outputs, `Game-Victoria3/save-CURR/`):**
- `SteadyInnovMod/aggr_save_matches.csv` — which country ids carry each stdinnv modifier
  (`fp`, `doc_path = country_manager.database.<ID>.timed_modifiers...`).
- `raw_countries.csv` — `id -> definition(tag), country_type`.
- `raw_state_census.csv` — `state_id -> owner_tag` (dedup first row per state).
- `raw_pops.csv` — `location(=state_id), workforce, dependents`; pop size = workforce + dependents.

**Reproducible query** (run from `Game-Victoria3/save-CURR/`):
```python
import csv,re,collections
st2tag={}
for r in csv.DictReader(open('raw_state_census.csv',encoding='utf-8')): st2tag.setdefault(r['state_id'],r['owner_tag'])
pop=collections.Counter()
for r in csv.DictReader(open('raw_pops.csv',encoding='utf-8')):
    t=st2tag.get(r['location'])
    if t: pop[t]+=int(r['workforce'])+int(r['dependents'])
cid={int(r['id']):(r['definition'],r['country_type']) for r in csv.DictReader(open('raw_countries.csv',encoding='utf-8'))}
unrec=set()
for r in csv.DictReader(open('SteadyInnovMod/aggr_save_matches.csv',encoding='utf-8')):
    if r['fp']=='stdinnv_unrecognized':
        m=re.search(r'database\.(\d+)',r['doc_path']);  unrec.add(int(m.group(1))) if m else None
rows=sorted(((cid[i][0],cid[i][1],pop.get(cid[i][0],0)) for i in unrec),key=lambda x:-x[2])
```

**Findings:**
- Save carries **13** `stdinnv_unrecognized` holders and **22** `stdinnv_subject` holders (the latter
  confirms the on_action `is_subject = yes` OVER-APPLICATION: ION MOL SER HDJ KOR TIB PHI CUB CAN UBD BIC
  PCO MKT IQU BCE LIB SAF TRI SIL PLY TAS DEI — subjects worldwide, not just India/China).
- Unrecognized holders, population-sorted: SOK 50.9M, SIA 20.5M, BUR 20.0M, MAD 4.4M | BUG 2.0M, RWD 1.1M,
  BRD 0.76M, HAW 0.61M, BNY 0.51M, ANK 0.51M, KRG 0.16M, TGI 0.06M, AGC 0.01M.
- **> 3M => SOK, SIA, BUR, MAD.**

**CAVEAT (important for the seed):** this is a MID/LATE save, not day-1. Major day-1 unrecognized nations
are ABSENT because the aggressive mods (Desi/MyDiploPlay) conquered them, or they are subjects: Persia,
Afghanistan, Morocco, Dai Nam, Nepal, Punjab (conquered) and Korea/Tibet (subjects -> got stdinnv_subject).
So the save-derived list undercounts a day-1 history seed. A complete day-1 seed needs the 1836 unrecognized
+ pop set (vanilla-derived) or an EARLY save, not this one. Decision deferred to user.
