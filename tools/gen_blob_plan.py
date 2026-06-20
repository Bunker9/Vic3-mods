#!/usr/bin/env python3
r"""
gen_blob_plan.py — MyDiploPlayMod data-gen + history emitter.

!!! FROZEN 2026-06-15 — DO NOT RUN until reconciled (TODO T50). Human commit 771515f
    HAND-EDITED the outputs this script owns: added CHT+KAB<->PAN 24mo truces (zz_mdp_truces),
    trimmed add_homeland from BIC/PRU claimed states + removed SWE Madras/Pegu/W.Indies claims
    (zz_mdp_claims). Re-running this WILL overwrite those human-approved changes. Bake them into
    the generator (region map / blob_targets) FIRST, then run. !!!


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

# European expander cultures are NOT seeded into far-off conquered states (user 2026-06-16):
# a British/Dutch/Swedish/German/Italian pop in a distant Asian/African state makes no sense.
# (The output file zz_mdp_seed_pops.txt was hand-scrubbed of these on 2026-06-16 because this
# generator is frozen for T50; this set keeps them out once it is reconciled + re-run.)
EUROPEAN_CULTURES = {
    "british", "dutch", "north_german", "south_german", "north_italian", "south_italian",
    "swedish", "french", "spanish", "portuguese", "danish", "norwegian",
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
    # Cap day-1 wars at 2 per expander: more simultaneous wars = infamy explosion + the AI
    # juggling fronts it can't win. The remaining targets keep their claims/homeland/pops
    # (granted below) so the runtime chain — or later manual play — can still take them.
    MAX_WARS_PER_EXPANDER = 2
    dp = [HDR, "DIPLOMATIC_PLAYS = {\n"]
    for e, d in by_exp.items():
        wars_emitted = 0
        for t, info in d["targets"].items():
            if not info["states"]:
                continue
            if wars_emitted >= MAX_WARS_PER_EXPANDER:
                break
            wars_emitted += 1
            # target_state must be a STATE (region_state), not a state_region — the defender
            # owns it, so s:STATE.region_state:<target_tag> (mirrors vanilla 00_ladakh_war).
            # return_state (not conquer_state): base infamy 2 vs 5, and it reclaims a
            # CLAIMED state — STATES below grants add_claim on every target state, so the
            # day-1 war qualifies as a low-infamy reclaim (stops the conquer_state white-peace).
            dp.append(f"\tc:{e} ?= {{\n\t\tcreate_diplomatic_play = {{\n")
            dp.append(f"\t\t\ttarget_state = s:{info['states'][0]}.region_state:{t}\n\t\t\twar = yes\n\t\t\ttype = dp_return_state\n")
            for i, st in enumerate(info["states"]):
                pd = "\n\t\t\t\tprimary_demand = yes" if i == 0 else ""
                dp.append(f"\t\t\tadd_war_goal = {{\n\t\t\t\tholder = c:{e}\n\t\t\t\ttype = return_state\n\t\t\t\ttarget_state = s:{st}.region_state:{t}{pd}\n\t\t\t}}\n")
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
        if cu in EUROPEAN_CULTURES: continue   # user 2026-06-16: no european pops in far-off states
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

    # ---- diplomacy: all-pairs truce among expand tags ----------------------
    # 2026-06-14 (user): expanders should ignore each other's blob-chain wars. Vanilla
    # create_bidirectional_truce (verified: common/history/diplomacy/00_truces.txt) sets
    # up a truce at game start; mdp_valid_generic_target then excludes any has_truce_with
    # the attacker, so expanders never target — and are weighted against joining wars
    # against — each other. months = 120 matches the 10-yr blob-chain window (1846 stop /
    # mdp_infamy_decay).
    TRUCE_MONTHS = 120
    # 2026-06-15 (user): the all-pairs matrix produced NONSENSE truces between expanders on
    # DIFFERENT CONTINENTS (PAN-PRU, OMA-BRZ, CLM-DEI) that can never reach each other. Only
    # emit a truce when both tags share a REGION bucket (i.e. could plausibly become land-
    # adjacent and fight via the blob chain). A tag may sit in two buckets (e.g. EGY bridges
    # the Middle East and Africa). This is what stops the real wars (OMA/PER, BIC/PAN) without
    # cluttering saves with impossible-war truces.
    REGION = {
        "PRU": {"EUR"}, "SAR": {"EUR"}, "SWE": {"EUR"},
        "BIC": {"INDIA"}, "PAN": {"INDIA"}, "NEP": {"INDIA"},
        "DAI": {"SEASIA"}, "SIA": {"SEASIA"}, "DEI": {"SEASIA"},
        "OMA": {"MIDEAST"}, "PER": {"MIDEAST"}, "NEJ": {"MIDEAST"},
        "EGY": {"MIDEAST", "AFRICA"},
        "MOR": {"AFRICA"}, "SOK": {"AFRICA"}, "SHW": {"AFRICA"}, "SAF": {"AFRICA"},
        "MEX": {"AMERICAS"}, "ARG": {"AMERICAS"}, "BRZ": {"AMERICAS"}, "CLM": {"AMERICAS"},
    }
    def same_region(a, b):
        return bool(REGION.get(a, set()) & REGION.get(b, set()))

    # Manual truce pairs (real adjacency the region buckets don't capture — across-water
    # neighbours whose wars stalemate or who keep getting dragged together):
    #   OMA<->NEJ : Nejd border is impassable desert wasteland (war never resolves).
    #   OMA<->SHW : Arabia faces the Horn across the Gulf of Aden; kept fighting in testing
    #               despite the OMA Arabian-mainland filter, so pin a start truce.
    #   SHW<->WTU : Shewa kept getting dragged into an odd event-claim war with Witu (Kenya)
    #               after taking Somalia (user 2026-06-16).
    MANUAL_TRUCES = [("OMA", "NEJ"), ("OMA", "SHW"), ("SHW", "WTU")]
    tags = sorted(by_exp.keys())
    dipl = [HDR, "DIPLOMACY = {\n"]
    emitted = set()
    for i, a in enumerate(tags):
        for b in tags[i + 1:]:
            if not same_region(a, b):
                continue   # skip cross-continent impossible-war truces
            dipl.append(f"\tc:{a} ?= {{\n\t\tcreate_bidirectional_truce = {{\n\t\t\tcountry = c:{b}\n\t\t\tmonths = {TRUCE_MONTHS}\n\t\t}}\n\t}}\n")
            emitted.add(frozenset((a, b)))
    for a, b in MANUAL_TRUCES:
        if frozenset((a, b)) in emitted:
            continue
        dipl.append(f"\tc:{a} ?= {{\n\t\tcreate_bidirectional_truce = {{\n\t\t\tcountry = c:{b}\n\t\t\tmonths = {TRUCE_MONTHS}\n\t\t}}\n\t}}\n")
    dipl.append("}\n")

    # NOTE: zz_mdp_wars.txt is NO LONGER written here — it is hand-maintained (the user's
    # curated day-1 war set). Only claims + pops are generated. To re-enable, restore the
    # write_bom(...zz_mdp_wars.txt..., dp) call below.
    _ = dp  # built above but intentionally not written
    f2 = write_bom(os.path.join("common", "history", "states", "zz_mdp_claims.txt"), stx)
    f3 = write_bom(os.path.join("common", "history", "pops", "zz_mdp_seed_pops.txt"), pp)
    f4 = write_bom(os.path.join("common", "history", "diplomacy", "zz_mdp_truces.txt"), dipl)

    # ---- report ------------------------------------------------------------
    missing = sorted({t for e, c, t, dd, s in plan if s == "(NO STATES FOUND)"})
    nocult = sorted({e for e in by_exp if not by_exp[e]["culture"]})
    print(f"expanders: {len(by_exp)}   plan rows: {len(plan)}")
    print( "  (zz_mdp_wars.txt SKIPPED — hand-maintained)")
    print(f"wrote: {os.path.relpath(f2, REPO)}")
    print(f"       {os.path.relpath(f3, REPO)}")
    print(f"       {os.path.relpath(f4, REPO)}")
    print(f"       {os.path.relpath(os.path.join(HERE,'blob_plan.csv'), REPO)}")
    if missing: print(f"WARNING — targets with no states found (tag wrong / absent at 1836): {', '.join(missing)}")
    if nocult:  print(f"WARNING — expanders with no primary culture resolved: {', '.join(nocult)}")

if __name__ == "__main__":
    main()
