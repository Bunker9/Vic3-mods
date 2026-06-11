#!/usr/bin/env python3
"""
scan_arable_rgo.py — per-nation arable plantations + RGO capacity for the 40 Mod-1 nations.

Reference for champ/support decisions: what cash crops a nation CAN grow, and what mineral/
resource RGOs (and how much) sit in its territory.

Reads (read-only) from the game install:
  map_data/state_regions/*.txt  -> per state: arable_land, arable_resources (plantations/farms),
                                    capped_resources (RGO buildings + level caps),
                                    resource{} blocks (discoverable: oil, etc.)
Nation ownership of states comes from tools/state_buildings.csv (the 40 nations' starting states).

Output: tools/arable_rgo_by_nation.csv
  tag, country, n_states, arable_land, plantations, staples, rgo_capped, rgo_discoverable
  - plantations  = distinct cash-crop plantations buildable (cotton/dye/silk/tea/opium/…)
  - staples      = distinct staple farms / ranch buildable (wheat/rye/rice/livestock/…)
  - rgo_capped   = "building:summed_cap" across owned states (coal/iron/lead/sulfur/logging/…)
  - rgo_discoverable = "building:summed_amount" (oil_rig, etc. — needs prospecting/tech)

Usage: python scan_arable_rgo.py [GAME_DIR]
"""
import os, re, sys, csv, glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
from _refpaths import game_path
DEFAULT_GAME = game_path()

_T = re.compile(r"""\s+|\#[^\n]*|(?P<op>\?=|<=|>=|==|=|<|>)|(?P<lb>\{)|(?P<rb>\})|(?P<qs>"[^"]*")|(?P<w>[^\s{}=<>#"]+)""", re.VERBOSE)
def tok(t): return [m.group() for m in _T.finditer(t) if m.lastgroup in ("op","lb","rb","qs","w")]
def parse_block(ts,i):
    items,n=[],len(ts)
    while i<n:
        t=ts[i]
        if t=="}": return items,i+1
        nx=ts[i+1] if i+1<n else None
        if nx in ("=","?=","==","<",">","<=",">="):
            k,j=t,i+2
            if j<n and ts[j]=="{": v,k2=parse_block(ts,j+1)
            else: v,k2=(ts[j] if j<n else None),j+1
            items.append((k,v)); i=k2
        elif t=="{":
            v,k2=parse_block(ts,i+1); items.append((None,v)); i=k2
        else: items.append(t); i+=1
    return items,i
def parse_file(p):
    with open(p,"r",encoding="utf-8-sig",errors="replace") as f: return parse_block(tok(f.read()),0)[0]
def unq(v): return v.strip('"') if isinstance(v,str) else v
def kv(items,key):
    for it in items:
        if isinstance(it,tuple) and it[0]==key: return it[1]
    return None
def kv_all(items,key): return [it[1] for it in items if isinstance(it,tuple) and it[0]==key]
def to_int(v):
    try: return int(float(unq(v)))
    except Exception: return 0

def is_plantation(b): return b.endswith("_plantation") or b=="building_vineyard"
def is_staple(b): return b.endswith("_farm") or b=="building_livestock_ranch"

def main():
    game=sys.argv[1] if len(sys.argv)>1 else DEFAULT_GAME
    if not os.path.isdir(game): sys.exit(f"Game dir not found: {game}")

    # nation -> states (STATE_ prefixed) from state_buildings.csv
    want={}; nat_states=defaultdict(set)
    with open(os.path.join(HERE,"mod-nations.csv"),encoding="utf-8") as f:
        for r in csv.DictReader(f): want[r["tag"]]=r["country"]
    with open(os.path.join(HERE,"state_buildings.csv"),encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["tag"] in want: nat_states[r["tag"]].add("STATE_"+r["state"])

    # state -> {arable, plantations, staples, capped{bld:cap}, disc{bld:amt}}
    states={}
    for fp in glob.glob(os.path.join(game,"map_data","state_regions","*.txt")):
        for it in parse_file(fp):
            if not (isinstance(it,tuple) and isinstance(it[1],list) and str(it[0]).startswith("STATE_")): continue
            body=it[1]
            arr=kv(body,"arable_resources")
            ar=[unq(x) for x in arr if isinstance(x,str)] if isinstance(arr,list) else []
            capped={}
            cap=kv(body,"capped_resources")
            if isinstance(cap,list):
                for sub in cap:
                    if isinstance(sub,tuple) and isinstance(sub[0],str) and sub[0].startswith("building_"):
                        capped[sub[0]]=to_int(sub[1])
            disc={}
            for rb in kv_all(body,"resource"):
                if isinstance(rb,list):
                    typ=unq(kv(rb,"type"))
                    amt=to_int(kv(rb,"undiscovered_amount")) + to_int(kv(rb,"discovered_amount"))
                    if typ: disc[typ]=disc.get(typ,0)+amt
            states[it[0]]={
                "arable":to_int(kv(body,"arable_land")),
                "plant":[b for b in ar if is_plantation(b)],
                "staple":[b for b in ar if is_staple(b)],
                "capped":capped,"disc":disc}

    out=os.path.join(HERE,"arable_rgo_by_nation.csv")
    cols=["tag","country","n_states","arable_land","plantations","staples","rgo_capped","rgo_discoverable"]
    def short(b): return b.replace("building_","")
    with open(out,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for t in want:
            arable=0; plant=set(); staple=set(); capped=defaultdict(int); disc=defaultdict(int); ns=0
            for st in nat_states.get(t,()):
                s=states.get(st)
                if not s: continue
                ns+=1; arable+=s["arable"]
                plant.update(s["plant"]); staple.update(s["staple"])
                for b,c in s["capped"].items(): capped[b]+=c
                for b,c in s["disc"].items(): disc[b]+=c
            w.writerow({
                "tag":t,"country":want[t],"n_states":ns,"arable_land":arable,
                "plantations":" ".join(sorted(short(b) for b in plant)),
                "staples":" ".join(sorted(short(b) for b in staple)),
                "rgo_capped":" ".join(f"{short(b)}:{capped[b]}" for b in sorted(capped)),
                "rgo_discoverable":" ".join(f"{short(b)}:{disc[b]}" for b in sorted(disc)),
            })
    print(f"-> {out}  ({len(want)} nations)")

if __name__=="__main__":
    main()
