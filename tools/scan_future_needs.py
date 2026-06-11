#!/usr/bin/env python3
"""
scan_future_needs.py — build a reusable "future needs" table for the Mod 1 nations.

Replaces ad-hoc journal scanning with ONE pattern-based, multi-source extractor that
identifies, per nation, the buildings it should build to satisfy its content:
  - journal_entries / decisions  -> buildings referenced (+ level hints)
  - company_types                -> building_types + extension_building_types a chartered
                                    company uses, and the prestige good it can unlock
  - prestige_goods               -> prestige good -> base good (the high-value variant)
And the upstream supply chain each needed building requires (its input goods), so you can
see what ELSE must be built for a company/journal target to flourish.

ATTRIBUTION (pattern-based, no re-derivation each run):
  - filename keyword  (00_companies_germany.txt / *ottoman* / *india* -> tag)   [FILE_HINTS]
  - scope tags in the entry: c:TAG, can_form_nation=TAG                          [+ FORMABLE]
  - company preferred_headquarters = { STATE_X } -> owner tag via state_buildings.csv
Formables map to their Mod-1 source (GER->PRU, ITA->SAR, ...), so e.g. a German company
HQ'd in a not-yet-owned state still lands on Prussia.

Outputs:
  tools/future_needs.csv            one row per (nation, source-entry, building)
  tools/future_needs_by_nation.csv  aggregated distinct buildings/prestige per nation

Usage: python scan_future_needs.py [GAME_DIR]
"""
import os, re, sys, csv, glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game"

# ---- tokenizer / parser ----------------------------------------------------
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

# ---- string-token collectors (recursive) -----------------------------------
def collect_strings(node, pred, out):
    if isinstance(node,str):
        s=unq(node)
        if pred(s): out.add(s)
    elif isinstance(node,list):
        for it in node:
            if isinstance(it,tuple): collect_strings(it[1],pred,out)
            else: collect_strings(it,pred,out)
META={"building_type","building_group","building_levels","building_owner","building_employment","building_size","building_types"}
def is_building(s): return s.startswith("building_") and s not in META
def is_prestige(s): return s.startswith("prestige_good_")

def collect_tags(node, out):
    """c:TAG and can_form_nation=TAG anywhere in a block."""
    if isinstance(node,str):
        s=unq(node)
        if s.startswith("c:"): out.add(s.split(":",1)[1])
    elif isinstance(node,list):
        for it in node:
            if isinstance(it,tuple):
                if it[0]=="can_form_nation" and isinstance(it[1],str): out.add(unq(it[1]))
                collect_tags(it[1],out)
            else: collect_tags(it,out)

# ---- maps -------------------------------------------------------------------
FORMABLE={"GER":"PRU","ITA":"SAR","SCA":"SWE","ETH":"SHW","GCO":"CLM","GBR":"GBR"}
FILE_HINTS={
    "russia":"RUS","hokkaido":"JAP","meiji":"JAP","japan":"JAP","sick_man":"TUR","ottoman":"TUR",
    "turkey":"TUR","amazonas":"BRZ","coffee_and_milk":"BRZ","cristo_redentor":"BRZ","brazil":"BRZ",
    "philippines":"PHI","manila":"PHI","iberian":"SPA","spanish":"SPA","atocha":"SPA","sagrada":"SPA",
    "spain":"SPA","portugal":"POR","pena":"POR","national_awakening_monument":"PRU","kaiserforum":"PRU",
    "grunderzeit":"PRU","germany":"PRU","german":"PRU","greece":"GRE","austria":"AUS","austria_hungary":"AUS",
    "egypt":"EGY","punjab":"PAN","sikh":"PAN","persia":"PER","mexico":"MEX","korea":"KOR","sokoto":"SOK",
    "ethiopia":"SHW","morocco":"MOR","siam":"SIA","nepal":"NEP","burma":"BUR","colombia":"CLM",
    "argentina":"ARG","sweden":"SWE","scandinav":"SWE","netherlands":"NET","dutch":"DEI","east_indies":"DEI",
    "east_india":"BIC","british_dictates":"BIC","victoria_terminus":"BIC","india_railway":"BIC","raj":"BIC",
    "india":"BIC","hyderabad":"HYD","belgium":"BEL","bavaria":"BAV","oman":"OMA","china":"CHI","france":"FRA",
}

def load_nations():
    want={}
    with open(os.path.join(HERE,"mod-nations.csv"),encoding="utf-8") as f:
        for r in csv.DictReader(f): want[r["tag"]]=r["country"]
    return want

def load_state_owner():
    """STATE_X -> owner tag (only the 40 nations' starting states)."""
    m={}
    p=os.path.join(HERE,"state_buildings.csv")
    if os.path.exists(p):
        with open(p,encoding="utf-8") as f:
            for r in csv.DictReader(f):
                m["STATE_"+r["state"]]=r["tag"]; m[r["state"]]=r["tag"]
    return m

def load_prestige_base(game):
    """prestige_good_x -> base good."""
    m={}
    for fp in glob.glob(os.path.join(game,"common","prestige_goods","*.txt")):
        for it in parse_file(fp):
            if isinstance(it,tuple) and isinstance(it[1],list) and str(it[0]).startswith("prestige_good_"):
                bg=kv(it[1],"base_good")
                if bg: m[it[0]]=unq(bg)
    return m

def build_building_inputs(game):
    """building -> (output_goods set, input_goods set) via building->pmg->pm chain."""
    # pm -> inputs/outputs
    pm_in,pm_out=defaultdict(set),defaultdict(set)
    for fp in glob.glob(os.path.join(game,"common","production_methods","*.txt")):
        for it in parse_file(fp):
            if isinstance(it,tuple) and isinstance(it[1],list) and str(it[0]).startswith("pm_"):
                goods=set()
                def walk(n,which):
                    if isinstance(n,list):
                        for x in n:
                            if isinstance(x,tuple):
                                k,v=x
                                mm=re.match(r"goods_(input|output)_([a-z_]+)_add",str(k))
                                if mm: (pm_in if mm.group(1)=="input" else pm_out)[it[0]].add(mm.group(2))
                                walk(v,which)
                            else: walk(x,which)
                walk(it[1],None)
    # pmg -> pms
    pmg_pms=defaultdict(list)
    for fp in glob.glob(os.path.join(game,"common","production_method_groups","*.txt")):
        for it in parse_file(fp):
            if isinstance(it,tuple) and isinstance(it[1],list) and str(it[0]).startswith("pmg_"):
                pms=kv(it[1],"production_methods")
                if isinstance(pms,list): pmg_pms[it[0]]=[x for x in pms if isinstance(x,str)]
    # building -> pmgs
    out=defaultdict(lambda:(set(),set()))
    for fp in glob.glob(os.path.join(game,"common","buildings","*.txt")):
        for it in parse_file(fp):
            if isinstance(it,tuple) and isinstance(it[1],list) and str(it[0]).startswith("building_"):
                pmgs=kv(it[1],"production_method_groups")
                ins,outs=set(),set()
                if isinstance(pmgs,list):
                    for g in pmgs:
                        for pm in pmg_pms.get(g,[]):
                            ins|=pm_in.get(pm,set()); outs|=pm_out.get(pm,set())
                out[it[0]]=(outs,ins)
    return out

# ---- main -------------------------------------------------------------------
def main():
    game=sys.argv[1] if len(sys.argv)>1 else DEFAULT_GAME
    if not os.path.isdir(game): sys.exit(f"Game dir not found: {game}")
    want=load_nations(); owner=load_state_owner(); pbase=load_prestige_base(game)
    print("Building input-chain map (buildings->pm->goods)…")
    binputs=build_building_inputs(game)

    def file_nation(fname):
        low=fname.lower()
        for sub,tag in FILE_HINTS.items():
            if sub in low and tag in want: return tag
        return None
    def tags_to_nations(tags):
        out=set()
        for t in tags:
            if t in want: out.add(t)
            elif t in FORMABLE and FORMABLE[t] in want: out.add(FORMABLE[t])
        return out

    rows=[]   # tag,country,source,source_key,flavored,building,good,prestige_good,prestige_base,level_hint,input_goods,attribution,file

    def emit(nation, source, key, fname, flavored, buildings, prestige, hints, attribution):
        for b in sorted(buildings):
            outs,ins=binputs.get(b,(set(),set()))
            rows.append({
                "tag":nation,"country":want[nation],"source":source,"source_key":key,
                "flavored":"yes" if flavored else "",
                "building":b.replace("building_",""),
                "good":" ".join(sorted(outs)),
                "prestige_good":"","prestige_base":"",
                "level_hint":" ".join(sorted(hints,key=lambda x:(len(x),x)))[:40],
                "input_goods":" ".join(sorted(ins)),
                "attribution":attribution,"file":fname})
        for pg in sorted(prestige):
            rows.append({
                "tag":nation,"country":want[nation],"source":source,"source_key":key,
                "flavored":"yes" if flavored else "",
                "building":"","good":"","prestige_good":pg.replace("prestige_good_",""),
                "prestige_base":pbase.get(pg,""),"level_hint":"","input_goods":"",
                "attribution":attribution,"file":fname})

    # --- companies ---
    for fp in glob.glob(os.path.join(game,"common","company_types","*.txt")):
        fn=os.path.basename(fp)
        for it in parse_file(fp):
            if not (isinstance(it,tuple) and isinstance(it[1],list) and str(it[0]).startswith("company_")): continue
            body=it[1]
            flavored = kv(body,"flavored_company")=="yes"
            blds=set()
            for blk in ("building_types","extension_building_types"):
                v=kv(body,blk)
                if isinstance(v,list): collect_strings(v,is_building,blds)
            prestige=set()
            for blk in ("possible_prestige_goods","extension_building_types","building_types"):
                v=kv(body,blk)
                if isinstance(v,list): collect_strings(v,is_prestige,prestige)
            # attribution
            nats=set(); attribs=set()
            hq=kv(body,"preferred_headquarters")
            hq_states=[x for x in hq if isinstance(x,str)] if isinstance(hq,list) else []
            for st in hq_states:
                t=owner.get(st)
                if t in want: nats.add(t); attribs.add("hq")
            fn_t=file_nation(fn)
            if fn_t: nats.add(fn_t); attribs.add("file")
            tg=set(); collect_tags(body,tg)
            for t in tags_to_nations(tg): nats.add(t); attribs.add("tag")
            for nat in nats:
                emit(nat,"company",it[0],fn,flavored,blds,prestige,set(),"+".join(sorted(attribs)))

    # --- journals + decisions ---
    for src,sub in (("journal","journal_entries"),("decision","decisions")):
        for fp in glob.glob(os.path.join(game,"common",sub,"*.txt")):
            fn=os.path.basename(fp)
            for it in parse_file(fp):
                if not (isinstance(it,tuple) and isinstance(it[1],list)): continue
                blds=set(); collect_strings(it[1],is_building,blds)
                if not blds: continue
                tg=set(); collect_tags(it[1],tg)
                nats=tags_to_nations(tg); attribs=set()
                if nats: attribs.add("tag")
                fn_t=file_nation(fn)
                if fn_t: nats.add(fn_t); attribs.add("file")
                if not nats: continue
                hints=set()
                collect_strings(it[1],lambda s: s.isdigit(),hints)  # crude numeric hints
                for nat in nats:
                    emit(nat,src,it[0],fn,False,blds,set(),set(),"+".join(sorted(attribs)))

    # --- write detailed ---
    cols=["tag","country","source","source_key","flavored","building","good","prestige_good",
          "prestige_base","level_hint","input_goods","attribution","file"]
    out1=os.path.join(HERE,"future_needs.csv")
    rows.sort(key=lambda r:(r["country"],r["source"],r["source_key"],r["building"]))
    with open(out1,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)

    # --- aggregate by nation ---
    agg=defaultdict(lambda:{"buildings":set(),"prestige":set(),"flavored":set(),"sources":set()})
    for r in rows:
        a=agg[r["tag"]]
        if r["building"]: a["buildings"].add(r["building"])
        if r["prestige_good"]: a["prestige"].add(r["prestige_good"]+(f"({r['prestige_base']})" if r["prestige_base"] else ""))
        if r["flavored"]: a["flavored"].add(r["source_key"])
        a["sources"].add((r["source"],r["source_key"]))
    out2=os.path.join(HERE,"future_needs_by_nation.csv")
    with open(out2,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["tag","country","n_sources","n_buildings","buildings_needed","prestige_goods","flavored_companies"])
        for t in want:
            a=agg.get(t)
            if not a: w.writerow([t,want[t],0,0,"","",""]); continue
            w.writerow([t,want[t],len(a["sources"]),len(a["buildings"]),
                        " ".join(sorted(a["buildings"]))," ".join(sorted(a["prestige"]))," ".join(sorted(a["flavored"]))])

    print(f"{len(rows)} need-rows -> {out1}")
    print(f"per-nation summary -> {out2}")
    cov=sum(1 for t in want if agg.get(t))
    print(f"nations with >=1 need: {cov}/{len(want)}")

if __name__=="__main__":
    main()
