#!/usr/bin/env python3
r"""
gen_blob_plan.py — MyDiploPlayMod data-gen + history emitter.

The 2026-06-12 redo: last build declared conquest wars at RUNTIME (on_action), which
(a) gave every expander huge day-1 infamy and (b) only war-goaled the target's CAPITAL,
so conquests came in partial + unincorporated and the AI white-peaced. The fix moves the
whole thing into HISTORY (no runtime infamy) and makes conquest STICK:

  1) history/diplomatic_plays — ONE day-1 conquest war per expander (its FIRST target),
     with a conquer_state war goal for EVERY state that target owns (not just the capital).
  2) history/states          — for every state of EVERY listed target: add_homeland for the
     expander's primary culture + add_claim for the expander (low-infamy, incorporates).
  3) history/pops            — seed a small primary-culture pop (SEED_POP) in each target
     state so the conquered land isn't 100% foreign.

The remaining targets (beyond the first) get their claims/homeland/pops here so a later
SEQUENTIAL, event-driven war chain (declared only while at peace — TODO) incorporates them
cleanly. We deliberately do NOT day-1 war every target at once (that was the chaos).

Inputs:  tools/blob_targets.csv  (expander,targets  — targets pipe-separated, first = day-1)
Reads:   <game>/common/country_definitions/*  (primary culture)
         <game>/common/history/states/*       (who owns which state at 1836)
Outputs: tools/blob_plan.csv  (review)  +  the three history files under MyDiploPlayMod/.

Usage:  python tools/gen_blob_plan.py
"""
import os, re, csv, glob
from _refpaths import game_path

GAME = game_path()
HERE = os.path.dirname(os.path.abspath(__file__))                       # hk-config/tools
REPO = os.path.dirname(os.path.dirname(HERE))                           # victoria-3-mod
MOD  = os.path.join(REPO, "mod1", "MyDiploPlayMod")
SEED_POP = 10000

# Extra seed pops beyond the primary culture+religion (expander -> [(religion, size), ...]).
# e.g. Punjab seeds Sikh (primary) AND Hindu Punjabis (user 2026-06-12).
EXTRA_SEED = {
    "PAN": [("hindu", 3000)],
}

# Religion of the expander's RULING/identity group, used for its primary seed pop. Base is
# the culture's default (heritage) religion — correct for most (panjabi -> sikh). Override the
# exceptions where the rulers' faith differs from the culture default (Oman's bedouin are
# ibadi, not the bedouin default sunni). NOT the demographic majority (West Punjab is Muslim,
# but the seed should be the Sikh Khalsa identity the user wants).
RELIGION_OVERRIDE = {
    "OMA": "ibadi",
}

def read(p):
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        return f.read()

def brace_block(text, start):
    """Return (block_text, end_index) for the {...} beginning at the first '{' at/after start."""
    i = text.index("{", start)
    depth, j = 0, i
    while j < len(text):
        c = text[j]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j
        j += 1
    return text[i + 1:], len(text)

# ---- 1) primary culture per tag -------------------------------------------
def load_cultures():
    cult = {}
    tagdef = re.compile(r"^([A-Z0-9_]{2,})\s*=\s*\{", re.M)
    for fp in glob.glob(os.path.join(GAME, "common", "country_definitions", "*.txt")):
        t = read(fp)
        for m in tagdef.finditer(t):
            tag = m.group(1)
            block, _ = brace_block(t, m.end() - 1)
            cm = re.search(r"cultures\s*=\s*\{([^}]*)\}", block)
            if cm:
                names = cm.group(1).split()
                if names:
                    cult[tag] = names[0]
    return cult

# ---- 1b) default religion per culture (common/cultures) --------------------
def load_culture_religion():
    """culture -> default religion, e.g. panjabi -> sikh, bedouin -> ibadi."""
    rel = {}
    culdef = re.compile(r"^([a-z][a-z0-9_]*)\s*=\s*\{", re.M)
    for fp in glob.glob(os.path.join(GAME, "common", "cultures", "*.txt")):
        t = read(fp)
        for m in culdef.finditer(t):
            block, _ = brace_block(t, m.end() - 1)
            rm = re.search(r"\breligion\s*=\s*([a-z0-9_]+)", block)
            if rm:
                rel[m.group(1)] = rm.group(1)
    return rel

# ---- 2) which states each tag owns at game start ---------------------------
def load_ownership():
    """tag -> [STATE_X, ...] from create_state country = c:TAG inside each s:STATE block."""
    owns = {}
    state_re = re.compile(r"s:(STATE_[A-Z0-9_]+)\s*=\s*\{")
    owner_re = re.compile(r"country\s*=\s*c:([A-Z0-9_]+)")
    for fp in glob.glob(os.path.join(GAME, "common", "history", "states", "*.txt")):
        t = read(fp)
        pos = 0
        while True:
            m = state_re.search(t, pos)
            if not m: break
            block, end = brace_block(t, m.end() - 1)
            pos = end + 1
            state = m.group(1)
            for om in owner_re.finditer(block):
                owns.setdefault(om.group(1), [])
                if state not in owns[om.group(1)]:
                    owns[om.group(1)].append(state)
    return owns

def main():
    cult = load_cultures()
    crel = load_culture_religion()
    owns = load_ownership()

    plan = []  # rows: expander, expander_culture, target, day1, state
    with open(os.path.join(HERE, "blob_targets.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            exp = row["expander"].strip()
            targets = [x.strip() for x in row["targets"].split("|") if x.strip()]
            exp_cul = cult.get(exp, "")
            for idx, tgt in enumerate(targets):
                states = owns.get(tgt, [])
                if not states:
                    plan.append((exp, exp_cul, tgt, idx == 0, "(NO STATES FOUND)"))
                for st in states:
                    plan.append((exp, exp_cul, tgt, idx == 0, st))

    # ---- review CSV --------------------------------------------------------
    with open(os.path.join(HERE, "blob_plan.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["expander", "expander_culture", "target", "day1_war", "state"])
        w.writerows([(e, c, t, "yes" if d else "", s) for (e, c, t, d, s) in plan])

    # group helpers
    by_exp = {}
    for e, c, t, d, s in plan:
        by_exp.setdefault(e, {"culture": c, "targets": {}})
        by_exp[e]["targets"].setdefault(t, {"day1": d, "states": []})
        if s != "(NO STATES FOUND)":
            by_exp[e]["targets"][t]["states"].append(s)

    HDR = "# AUTO-GENERATED by hk-config/tools/gen_blob_plan.py — do not hand-edit.\n"

    # ---- diplomatic_plays: ONE day-1 war per CURATED TARGET (user 2026-06-12: an expander
    #      goes to war with ALL its listed targets at once, e.g. PAN vs SIN+BHW+KAL+KAN+HER+
    #      KUN+KAF). History start = no infamy; every war goals the target's FULL state set.
    dp = [HDR, "DIPLOMATIC_PLAYS = {\n"]
    for e, d in by_exp.items():
        for t, info in d["targets"].items():
            if not info["states"]:
                continue
            # target_state must be a STATE (region_state), not a state_region — the defender
            # owns it, so s:STATE.region_state:<target_tag> (mirrors vanilla 00_ladakh_war).
            dp.append(f"\tc:{e} ?= {{\n\t\tcreate_diplomatic_play = {{\n")
            dp.append(f"\t\t\ttarget_state = s:{info['states'][0]}.region_state:{t}\n\t\t\twar = yes\n\t\t\ttype = dp_conquer_state\n")
            for i, st in enumerate(info["states"]):
                pd = "\n\t\t\t\tprimary_demand = yes" if i == 0 else ""
                dp.append(f"\t\t\tadd_war_goal = {{\n\t\t\t\tholder = c:{e}\n\t\t\t\ttype = conquer_state\n\t\t\t\ttarget_state = s:{st}.region_state:{t}{pd}\n\t\t\t}}\n")
            dp.append("\t\t}\n\t}\n")
    dp.append("}\n")

    # ---- states: homeland + claim for every target state -------------------
    stx = [HDR, "STATES = {\n"]
    seen = {}
    for e, d in by_exp.items():
        cu = d["culture"]
        for t, info in d["targets"].items():
            for st in info["states"]:
                seen.setdefault(st, []).append((cu, e))
    for st, grants in seen.items():
        stx.append(f"\ts:{st} = {{\n")
        done = set()
        for cu, e in grants:
            if cu and ("h", cu) not in done:
                stx.append(f"\t\tadd_homeland = cu:{cu}\n"); done.add(("h", cu))
            if ("c", e) not in done:
                stx.append(f"\t\tadd_claim = c:{e}\n"); done.add(("c", e))
        stx.append("\t}\n")
    stx.append("}\n")

    # ---- pops: seed expander culture+religion in each target state ---------
    # region_state is the TARGET that owns it at start (the state may be split — emit per owner).
    # Primary pop = expander culture at its culture's default religion; EXTRA_SEED adds more
    # (e.g. PAN gets a second panjabi/hindu pop).
    pp = [HDR, "POPS = {\n"]
    for e, d in by_exp.items():
        cu = d["culture"]
        if not cu: continue
        rl = RELIGION_OVERRIDE.get(e) or crel.get(cu, "")   # rulers' religion, else culture default
        relline = f" religion = {rl}" if rl else ""
        seeds = [(relline, SEED_POP)] + [(f" religion = {r}", n) for (r, n) in EXTRA_SEED.get(e, [])]
        for t, info in d["targets"].items():
            for st in info["states"]:
                pp.append(f"\ts:{st} = {{\n\t\tregion_state:{t} = {{\n")
                for rline, size in seeds:
                    pp.append(f"\t\t\tcreate_pop = {{ culture = {cu}{rline} size = {size} }}\n")
                pp.append("\t\t}\n\t}\n")
    pp.append("}\n")

    def write_bom(relpath, lines):
        full = os.path.join(MOD, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8-sig", newline="\n") as f:
            f.write("".join(lines))
        return full

    f1 = write_bom(os.path.join("common", "history", "diplomatic_plays", "zz_mdp_wars.txt"), dp)
    f2 = write_bom(os.path.join("common", "history", "states", "zz_mdp_claims.txt"), stx)
    f3 = write_bom(os.path.join("common", "history", "pops", "zz_mdp_seed_pops.txt"), pp)

    # ---- report ------------------------------------------------------------
    missing = sorted({t for e, c, t, dd, s in plan if s == "(NO STATES FOUND)"})
    nocult = sorted({e for e in by_exp if not by_exp[e]["culture"]})
    print(f"expanders: {len(by_exp)}   plan rows: {len(plan)}")
    print(f"wrote: {os.path.relpath(f1, REPO)}")
    print(f"       {os.path.relpath(f2, REPO)}")
    print(f"       {os.path.relpath(f3, REPO)}")
    print(f"       {os.path.relpath(os.path.join(HERE,'blob_plan.csv'), REPO)}")
    if missing: print(f"WARNING — targets with no states found (tag wrong / absent at 1836): {', '.join(missing)}")
    if nocult:  print(f"WARNING — expanders with no primary culture resolved: {', '.join(nocult)}")

if __name__ == "__main__":
    main()
