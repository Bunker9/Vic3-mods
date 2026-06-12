#!/usr/bin/env python3
r"""
port_statedata.py — carry the OLD mod (3104377473)'s map_data state buffs onto CURRENT
vanilla state_regions, for InfraTaxMod.

Why: arable_land / subsistence_building / capped_resources / resource are MAP DATA, not
modifiers — they can't be done via add_modifier, so they need state_regions files. The old
mod is on an older schema (bg_logging, building_subsistence_rice_paddies, …) whose tokens
were renamed in the current version, so we can't copy blocks verbatim. This:
  1) parses the old mod + current vanilla state_regions,
  2) maps old token names -> current ones,
  3) MAX-MERGES per state (the user's edits were buffs; never reduce vanilla, keep current
     resources the old version lacked, union resource types),
  4) writes ONLY the vanilla files that actually change into InfraTaxMod/map_data/state_regions/
     (full-file copies, since modded state_regions replace vanilla by filename),
  5) writes tools/statedata_changes.csv for review.

subsistence_building is categorical (the user deliberately switched starving states to a
better subsistence farm) → we take the old mod's mapped choice where it differs.

Usage:  python tools/port_statedata.py
"""
import os, re, csv, glob
from _refpaths import game_path

GAME = game_path()
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OLD  = os.path.join(REPO, "3104377473", "map_data", "state_regions")
VAN  = os.path.join(GAME, "map_data", "state_regions")
OUT  = os.path.join(REPO, "mod1", "InfraTaxMod", "map_data", "state_regions")

CAPPED_MAP = {
    "bg_coal_mining": "building_coal_mine", "bg_fishing": "building_fishing_wharf",
    "bg_gold_mining": "building_gold_mine", "bg_iron_mining": "building_iron_mine",
    "bg_lead_mining": "building_lead_mine", "bg_logging": "building_logging_camp",
    "bg_sulfur_mining": "building_sulfur_mine", "bg_whaling": "building_whaling_station",
}
RESOURCE_MAP = {
    "bg_gold_fields": "building_gold_field", "bg_gold_mining": "building_gold_mine",
    "bg_oil_extraction": "building_oil_rig", "bg_rubber": "building_rubber_plantation",
}
SUBSIST_MAP = {
    "building_subsistence_farms": "building_subsistence_farm",
    "building_subsistence_fishing_villages": "building_subsistence_fishing_village",
    "building_subsistence_orchards": "building_subsistence_orchard",
    "building_subsistence_pastures": "building_subsistence_pasture",
    "building_subsistence_rice_paddies": "building_subsistence_rice_farm",
}

# Manual per-state bumps (user 2026-06-12, not from the old mod). These count as USER-TOUCHED
# so they also get the infra/tax trait. e.g. Agra: ~1/4 pop starving -> ~1.5x arable (483 -> 725).
MANUAL_BUMP = {
    "STATE_AGRA": {"arable": 725},   # was 483; subsistence already rice_farm in vanilla
}

def read(p):
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        return f.read()

def brace_block(text, start):
    i = text.index("{", start); depth, j = 0, i
    while j < len(text):
        if text[j] == "{": depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], i, j
        j += 1
    return text[i + 1:], i, len(text)

STATE_RE = re.compile(r"(STATE_[A-Z0-9_]+)\s*=\s*\{")

def states_in(text):
    """yield (name, blockstart_brace_idx, blockend_idx, inner_text)."""
    pos = 0
    while True:
        m = STATE_RE.search(text, pos)
        if not m: break
        inner, bi, ei = brace_block(text, m.end() - 1)
        yield m.group(1), m.start(), ei, inner
        pos = ei + 1

def parse_capped(inner):
    m = re.search(r"capped_resources\s*=\s*\{", inner)
    if not m: return {}
    blk, _, _ = brace_block(inner, m.end() - 1)
    return {k: int(v) for k, v in re.findall(r"([a-z_]+)\s*=\s*(\d+)", blk)}

def parse_resources(inner):
    """list of dicts: {type, discovered, undiscovered} for each `resource = {}` (not capped_)."""
    out = []
    for m in re.finditer(r"(?<![a-z_])resource\s*=\s*\{", inner):
        blk, _, _ = brace_block(inner, m.end() - 1)
        t = re.search(r'type\s*=\s*"([^"]+)"', blk)
        d = re.search(r"(?<!un)discovered_amount\s*=\s*(\d+)", blk)   # not 'undiscovered_amount'
        u = re.search(r"undiscovered_amount\s*=\s*(\d+)", blk)
        if t:
            out.append({"type": t.group(1),
                        "discovered": int(d.group(1)) if d else 0,
                        "undiscovered": int(u.group(1)) if u else 0})
    return out

def parse_scalar(inner, key):
    m = re.search(key + r"\s*=\s*(\d+)", inner)
    return int(m.group(1)) if m else None

def parse_subsist(inner):
    m = re.search(r'subsistence_building\s*=\s*"([^"]+)"', inner)
    return m.group(1) if m else None

def main():
    # ---- old mod desired values (mapped to current tokens) -----------------
    old = {}  # state -> dict
    for fp in glob.glob(os.path.join(OLD, "*.txt")):
        t = read(fp)
        for name, _, _, inner in states_in(t):
            cap = {CAPPED_MAP.get(k, k): v for k, v in parse_capped(inner).items()}
            res = []
            for r in parse_resources(inner):
                r = dict(r); r["type"] = RESOURCE_MAP.get(r["type"], r["type"]); res.append(r)
            sub = parse_subsist(inner)
            old[name] = {
                "arable": parse_scalar(inner, "arable_land"),
                "subsist": SUBSIST_MAP.get(sub, sub) if sub else None,
                "capped": cap,
                "resource": res,
            }

    os.makedirs(OUT, exist_ok=True)
    changes = []  # rows for review csv
    files_written = 0

    for fp in sorted(glob.glob(os.path.join(VAN, "*.txt"))):
        fname = os.path.basename(fp)
        t = read(fp)
        edits = []  # (start, end, new_block_text)
        for name, bs, be, inner in states_in(t):
            block = t[bs:be + 1]
            # LAND states only — sea/ocean regions (99_seas.txt) have no arable_land/subsistence.
            is_land = parse_scalar(inner, "arable_land") is not None or parse_subsist(inner) is not None
            o = old.get(name)
            manual = MANUAL_BUMP.get(name) if is_land else None
            van_arable = parse_scalar(inner, "arable_land")
            van_sub = parse_subsist(inner)
            van_cap = parse_capped(inner)
            van_res = parse_resources(inner)

            # USER-FINGERPRINT GATE: without old base-game vanilla we can't tell the user's edits
            # from vanilla's version drift, so treat a state as USER-TOUCHED only if its old values
            # carry a tell-tale signature: (a) subsistence category change, (b) arable_land a round
            # multiple of 100, (c) a capped/resource value ≡ 1 (mod 5), ≥6, above vanilla.
            def mark5(v, base): return v % 5 == 1 and v >= 6 and v > base
            sig = []
            if o and is_land:
                if o["subsist"] and van_sub and o["subsist"] != van_sub:
                    sig.append("subsistence")
                if o["arable"] is not None and o["arable"] % 100 == 0 and o["arable"] != (van_arable or 0):
                    sig.append("arable_x100")
                if any(mark5(v, van_cap.get(k, 0)) for k, v in o["capped"].items()):
                    sig.append("capped_5x+1")
                if any(mark5(max(r["discovered"], r["undiscovered"]), 0) for r in o["resource"]):
                    sig.append("resource_5x+1")

            # Trait + buffs apply ONLY to user-touched (tweaked / manually-bumped) states — the
            # user wants the Developed Region trait on the big/tax-troubled states they care about,
            # NOT the whole map. (TODO: a pop>1.5M gate would be the more principled selector.)
            new_block = block
            if is_land and (sig or manual):
                new_block = inject_trait(block)
                sigstr = "|".join(sig + (["manual"] if manual else []))
                local = []
                def rec(field, van, new):
                    changes.append((fname, name, sigstr, field, van, new))
                    local.append((field, van, new))

                # arable_land: max of vanilla, old-mod (if sig), manual bump
                targets = []
                if sig and o and o["arable"] is not None and van_arable is not None and o["arable"] > van_arable:
                    targets.append(o["arable"])
                if manual and "arable" in manual and (van_arable is None or manual["arable"] > van_arable):
                    targets.append(manual["arable"])
                if targets:
                    at = max(targets)
                    new_block = re.sub(r"arable_land\s*=\s*\d+", f"arable_land = {at}", new_block, count=1)
                    rec("arable_land", van_arable, at)

                # subsistence / capped / resource: only the old-mod port (sig states)
                if sig and o:
                    if o["subsist"] and van_sub and o["subsist"] != van_sub:
                        new_block = re.sub(r'subsistence_building\s*=\s*"[^"]+"',
                                           f'subsistence_building = "{o["subsist"]}"', new_block, count=1)
                        rec("subsistence_building", van_sub, o["subsist"])
                    merged_cap = dict(van_cap)
                    for k, v in o["capped"].items():
                        if v > merged_cap.get(k, 0):
                            merged_cap[k] = v
                            rec("capped:" + k, van_cap.get(k, 0), v)
                    if merged_cap != van_cap:
                        new_block = replace_capped(new_block, merged_cap)
                    res_by_type = {r["type"]: dict(r) for r in van_res}
                    res_changed = False
                    for r in o["resource"]:
                        cur = res_by_type.get(r["type"])
                        if cur is None:
                            res_by_type[r["type"]] = dict(r); res_changed = True
                            rec("resource+:" + r["type"], 0, r["undiscovered"] or r["discovered"])
                        else:
                            for fld in ("discovered", "undiscovered"):
                                if r[fld] > cur[fld]:
                                    cur[fld] = r[fld]; res_changed = True
                                    rec(f"resource:{r['type']}.{fld}", "", r[fld])
                    if res_changed:
                        new_block = replace_resources(new_block, list(res_by_type.values()))

                if local:
                    summary = "; ".join(f"{fld} {v}->{n}" for fld, v, n in local)
                    comment = (f"# [InfraTaxMod] state buffs (signal: {sigstr}) — {summary}\n"
                               f"# Re-verify against vanilla on game-version bumps (regen: tools/port_statedata.py)\n")
                    new_block = comment + new_block

            if new_block != block:                   # only user-touched land states change
                edits.append((bs, be + 1, new_block))

        if edits:
            edits.sort(reverse=True)
            for bs, be, nb in edits:
                t = t[:bs] + nb + t[be:]
            with open(os.path.join(OUT, fname), "w", encoding="utf-8-sig", newline="\n") as f:
                f.write(t)
            files_written += 1

    with open(os.path.join(HERE, "statedata_changes.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["file", "state", "signal", "field", "vanilla", "new"]); w.writerows(changes)

    states_changed = len({(c[0], c[1]) for c in changes})
    print(f"files written: {files_written}   states changed: {states_changed}   field-edits: {len(changes)}")
    print(f"review: hk-config/tools/statedata_changes.csv")

TRAIT = '"state_trait_infratax"'

def inject_trait(block):
    """Add state_trait_infratax to the state's traits list (the global infra/tax/bureaucracy
    trait). Appends to an existing `traits = {}` or inserts one before arable_land."""
    m = re.search(r"traits\s*=\s*\{([^}]*)\}", block)
    if m:
        if "state_trait_infratax" in m.group(1):
            return block
        toks = m.group(1).split() + [TRAIT]
        return block[:m.start()] + "traits = { " + " ".join(toks) + " }" + block[m.end():]
    if re.search(r"\n[ \t]*arable_land\s*=", block):
        return re.sub(r"(\n)([ \t]*arable_land\s*=)", r"\1    traits = { " + TRAIT + r" }\1\2", block, count=1)
    return re.sub(r"\}\s*$", "    traits = { " + TRAIT + " }\n}", block, count=1)

def fmt_capped(d):
    lines = "\n".join(f"        {k} = {v}" for k, v in d.items())
    return "capped_resources = {\n" + lines + "\n    }"

def fmt_resources(res):
    out = []
    for r in res:
        body = [f'        type = "{r["type"]}"']
        if r.get("discovered"):   body.append(f"        discovered_amount = {r['discovered']}")
        if r.get("undiscovered"): body.append(f"        undiscovered_amount = {r['undiscovered']}")
        out.append("resource = {\n" + "\n".join(body) + "\n    }")
    return out

def replace_capped(block, merged):
    m = re.search(r"capped_resources\s*=\s*\{", block)
    if not m:  # vanilla had none → insert before final brace
        return re.sub(r"\}\s*$", "    " + fmt_capped(merged) + "\n}", block, count=1)
    _, bi, ei = brace_block(block, m.end() - 1)
    return block[:m.start()] + fmt_capped(merged) + block[ei + 1:]

def replace_resources(block, res):
    # remove every existing `resource = {}` (singular), then insert the merged set
    out = block; spans = []
    for m in re.finditer(r"(?<![a-z_])resource\s*=\s*\{", out):
        _, bi, ei = brace_block(out, m.end() - 1)
        spans.append((m.start(), ei + 1))
    for s, e in reversed(spans):
        out = out[:s] + out[e:]
    blocks = fmt_resources(res)
    if not blocks:
        return out
    ins = "    " + "\n    ".join(blocks) + "\n"
    return re.sub(r"\}\s*$", ins + "}", out, count=1)

if __name__ == "__main__":
    main()
