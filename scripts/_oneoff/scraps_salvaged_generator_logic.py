#!/usr/bin/env python3
r"""
scraps_salvaged_generator_logic.py — SALVAGE BIN (reference only, NOT run).

When a small generator (<150 lines of mod output) is retired in favour of hand-maintaining
its output file, the genuinely interesting derivation logic is parked here so the analysis /
vanilla-data cross-referencing isn't lost. These snippets are NOT wired to anything; they are
kept for reference so a future session can re-derive by hand or rebuild a generator if scope grows.

Each entry records: source generator, what it derived, its data sources, and the core logic.
Data sources named below live in hk-config/tools/ and are produced by anal_* scans — DO NOT DELETE.
"""

# =============================================================================
# 2026-06-16 — gen_eastafrica_shw_override.py  (RETIRED)
#   Output (now HAND-MAINTAINED):
#     mod1/Top40EcoBoostMod/common/history/buildings/zz_eco_starters_eastafrica.txt
#   Why retired: output is only ~2 buildings (ERITREA->EGY cotton, OROMIA->SHW cotton) because
#     only EGY and SHW from the 40-nation list own East-African states — not worth a generator.
#   Data sources (hk-config/tools/, from anal_* scans — keep): mod-nations.csv,
#     unused_rgo_by_state.csv, state_pops.csv
#   Salvaged logic: per East-African state, pick the BIGGEST-POP mod nation that owns it AND has
#     an unused RGO there, then seed a preferred good whose building matches an unused RGO.
# =============================================================================
EA_GOOD_BUILDING = {
    "grain": "wheat_farm", "fabric": "cotton_plantation", "fruit": "banana_plantation",
    "fish": "fishing_wharf", "wood": "logging_camp", "iron": "iron_mine", "coal": "coal_mine",
}
EA_STATES = {"STATE_OROMIA", "STATE_SOMALILAND", "STATE_GONDER", "STATE_ERITREA", "STATE_AMHARA"}


def _ea_pick(state, state_pops, unused_rgo, mods):
    """For one EA state: biggest-pop mod nation owning it w/ an unused RGO, plus a good to seed.
    state_pops: {state: {tag: pop}}  unused_rgo: {state: {tag: [rgo,...]}}  mods: {tag: name}"""
    candidates = state_pops.get(state, {})
    valid = {t: p for t, p in candidates.items() if t in unused_rgo.get(state, {})}
    if not valid:
        return None
    biggest_tag = max(valid, key=valid.get)
    rgo_list = unused_rgo[state][biggest_tag]
    for g in ["grain", "fabric", "fruit", "fish", "wood", "iron", "coal"]:
        if EA_GOOD_BUILDING.get(g) in rgo_list:
            return {"state": state, "tag": biggest_tag, "good": g}
    return {"state": state, "tag": biggest_tag, "good": "wood"}  # fallback


# =============================================================================
# 2026-06-16 - gen_blob_plan.py  (RETIRED - user: diplo files now hand-curated; generator froze
#   under T50 and conflicted with the human truce/claim/pop edits). Outputs are now HAND-WRITTEN:
#     MyDiploPlayMod/common/history/{diplomatic_plays/zz_mdp_wars, states/zz_mdp_claims,
#                                    pops/zz_mdp_seed_pops, diplomacy/zz_mdp_truces}.txt
#   Source data kept (DO NOT DELETE): tools/blob_targets.csv (the seed).
#   Salvaged below: the REUSABLE vanilla-game-data parsers + config buckets (the genuinely useful
#   "search into vanilla" work). The mod-specific war/claim/pop EMITTERS were dropped.
# =============================================================================
import re, glob, os as _os

def brace_block(text, start):
    """Return (block_text, end_index) for the {...} starting at the first '{' at/after start."""
    i = text.index("{", start); depth, j = 0, i
    while j < len(text):
        c = text[j]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return text[i+1:j], j
        j += 1
    return text[i+1:], len(text)

def load_cultures(GAME):
    """tag -> primary culture, from <game>/common/country_definitions/*.txt"""
    cult = {}; tagdef = re.compile(r"^([A-Z0-9_]{2,})\s*=\s*\{", re.M)
    for fp in glob.glob(_os.path.join(GAME, "common", "country_definitions", "*.txt")):
        t = open(fp, encoding="utf-8-sig", errors="replace").read()
        for m in tagdef.finditer(t):
            block, _ = brace_block(t, m.end()-1)
            cm = re.search(r"cultures\s*=\s*\{([^}]*)\}", block)
            if cm and cm.group(1).split(): cult[m.group(1)] = cm.group(1).split()[0]
    return cult

def load_ownership(GAME):
    """tag -> [STATE_X,...] owned at 1836, from <game>/common/history/states/*.txt"""
    owns = {}; state_re = re.compile(r"s:(STATE_[A-Z0-9_]+)\s*=\s*\{")
    owner_re = re.compile(r"country\s*=\s*c:([A-Z0-9_]+)")
    for fp in glob.glob(_os.path.join(GAME, "common", "history", "states", "*.txt")):
        t = open(fp, encoding="utf-8-sig", errors="replace").read(); pos = 0
        while True:
            m = state_re.search(t, pos)
            if not m: break
            block, end = brace_block(t, m.end()-1); pos = end+1
            for om in owner_re.finditer(block):
                owns.setdefault(om.group(1), [])
                if m.group(1) not in owns[om.group(1)]: owns[om.group(1)].append(m.group(1))
    return owns

# culture->default religion: same brace_block loop over <game>/common/cultures/*.txt, regex
#   r"religion\s*=\s*([a-z0-9_]+)" inside each culture block.

# Region buckets for "could these two expanders ever fight" truce filtering (same_region = sets intersect):
REGION = {"PRU":{"EUR"},"SAR":{"EUR"},"SWE":{"EUR"},"BIC":{"INDIA"},"PAN":{"INDIA"},"NEP":{"INDIA"},
    "DAI":{"SEASIA"},"SIA":{"SEASIA"},"DEI":{"SEASIA"},"OMA":{"MIDEAST"},"PER":{"MIDEAST"},"NEJ":{"MIDEAST"},
    "EGY":{"MIDEAST","AFRICA"},"MOR":{"AFRICA"},"SOK":{"AFRICA"},"SHW":{"AFRICA"},"SAF":{"AFRICA"},
    "MEX":{"AMERICAS"},"ARG":{"AMERICAS"},"BRZ":{"AMERICAS"},"CLM":{"AMERICAS"}}
EUROPEAN_CULTURES = {"british","dutch","north_german","south_german","north_italian","south_italian",
    "swedish","french","spanish","portuguese","danish","norwegian"}
RELIGION_OVERRIDE = {"OMA":"ibadi"}; EXTRA_SEED = {"PAN":[("hindu",3000)]}
MANUAL_TRUCES = [("OMA","NEJ"),("OMA","SHW"),("SHW","WTU")]
