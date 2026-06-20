#!/usr/bin/env python3
r"""
gen_ecoboost_configs.py — turn SELECT_ECOBOOST_FINAL.csv into Top40EcoBoostMod configs.

Emits (all 40 tags), mirroring the proven hand-written PAN/PRU pattern:
  common/scripted_effects/eco_setup_generated.txt   — eco_setup_<TAG> (champ/support/flavour seed + modifiers + phase-2 trigger)
  common/static_modifiers/eco_champ_tp_generated.txt — eco_<TAG>_champ_tp_p1 (champ building throughput +200%, 20 yr)
  events/eco_events.txt                              — eco.2 dispatch (all 40), eco.3 phase-2 (all 40), eco.4 (verbatim)

champ N = 2*tier ; each support N = 1*tier ; each flavour = +1. grain -> the tag's primary
staple farm (wheat>rice>maize>millet>rye, from arable_rgo_by_nation.csv).

After running: remove the now-superseded hand eco_setup_PAN/PRU from eco_effects.txt and the
hand eco_PAN/PRU_champ_tp_p1 from eco_modifiers.txt (the generated files own all 40).

Usage: python gen_ecoboost_configs.py
"""
import os, csv

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(HERE, "..", "..", "mod1", "Top40EcoBoostMod")
EFFECTS_OUT = os.path.join(MOD, "common", "scripted_effects", "eco_setup_generated.txt")
MODS_OUT    = os.path.join(MOD, "common", "static_modifiers", "eco_champ_tp_generated.txt")
EVENTS_OUT  = os.path.join(MOD, "events", "eco_events.txt")
TARGET_OUT  = os.path.join(MOD, "common", "scripted_triggers", "eco_target_triggers.txt")
FLAVOUR_OUT = os.path.join(MOD, "common", "history", "buildings", "zz_eco_flavour.txt")

GOOD2BUILDING = {
    "fabric": "building_cotton_plantation", "dye": "building_dye_plantation",
    "opium": "building_opium_plantation", "silk": "building_silk_plantation",
    "tea": "building_tea_plantation", "tobacco": "building_tobacco_plantation",
    "coffee": "building_coffee_plantation", "sugar": "building_sugar_plantation",
    "fruit": "building_banana_plantation", "wine": "building_vineyard",
    "rubber": "building_rubber_plantation", "meat": "building_livestock_ranch",
    "fish": "building_fishing_wharf", "coal": "building_coal_mine",
    "iron": "building_iron_mine", "lead": "building_lead_mine",
    "sulfur": "building_sulfur_mine", "wood": "building_logging_camp",
    "oil": "building_oil_rig", "steel": "building_steel_mill",
    "tools": "building_tooling_workshop", "clothes": "building_textile_mill",
    "furniture": "building_furniture_manufactory", "paper": "building_paper_mill",
    "glass": "building_glassworks", "groceries": "building_food_industry",
    "engines": "building_motor_industry", "artillery": "building_artillery_foundry",
    "small_arms": "building_arms_industry", "ammunition": "building_munition_plant",
    "explosives": "building_explosives_factory", "fertilizer": "building_chemical_plant",
}
STAPLE_PRIORITY = ["wheat_farm", "rice_farm", "maize_farm", "millet_farm", "rye_farm"]

# champ good -> ONE champ throughput+wage modifier (defined in eco_modifiers.txt). 2026-06-16:
# the agrarian bucket was split per building-GROUP so a champ boosts ONLY its own group, all at
# +0.5 throughput. Categories: plant | log | ranch | fish | mine | ind.
CHAMP_CAT = {
    "coal": "mine", "sulfur": "mine", "iron": "mine", "lead": "mine",
    "steel": "ind", "furniture": "ind", "clothes": "ind", "paper": "ind",
    "wood": "log",
    "meat": "ranch", "grain": "ranch",
    "fish": "fish",
}  # everything else (tea/dye/tobacco/fabric/coffee/sugar/fruit/wine/opium/silk/rubber) -> plant


def champ_cat(good):
    return CHAMP_CAT.get(good, "plant")


def load_csv(name):
    path = name if os.path.isabs(name) else os.path.join(HERE, name)
    with open(path, encoding="utf-8") as f:
        return [r for r in csv.reader(f)]


def load_dictcsv(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_unused_rgo():
    """state-level unused RGO slots -> {(tag, rgo_base): [(state, capacity), ...]} (highest cap = best)."""
    out = {}
    for r in load_dictcsv("unused_rgo_by_state.csv"):
        raw = r.get("capacity") or r.get("state_arable_land") or "0"
        try:
            cap = int(raw)
        except ValueError:
            cap = 0
        out.setdefault((r["tag"], r["rgo"]), []).append((r["state"], cap))
    return out


def _top_n(unused, tag, rgo_base, n):
    """The up-to-n highest-capacity states where `tag` has an unused `rgo_base` slot."""
    return [st for st, cap in sorted(unused.get((tag, rgo_base), []), key=lambda x: -x[1])[:n]
            if (tag, st) not in FLAVOUR_STATE_EXCLUDE]


# TODO (revisit, T-tiny-ownership): some states are owned only in a TINY sliver by the tag, so the
# state-level unused_rgo says "has slot" but the tag's PORTION can't build it -> "Failed creating
# backing building" assertion. Proper fix: detect tiny ownership (ownership-fraction data). For now,
# skip the known offenders. (DEI Sambas livestock_ranch + the logging/lead overbuilds are SUPPORT /
# generic-runtime, NOT in this file -> separate TODO for capacity-aware support seeding.)
FLAVOUR_STATE_EXCLUDE = {("RUS", "KARS")}


def grain_farm_by_tag():
    """Pick each tag's primary staple farm from arable_rgo_by_nation.csv."""
    out = {}
    for r in load_dictcsv("arable_rgo_by_nation.csv"):
        staples = r["staples"].split()
        chosen = next((s for s in STAPLE_PRIORITY if s in staples), "wheat_farm")
        out[r["tag"]] = f"building_{chosen}"
    return out


def building_for(good, tag, grain_map):
    if good == "grain":
        return grain_map.get(tag, "building_wheat_farm")
    b = GOOD2BUILDING.get(good)
    if not b:
        raise ValueError(f"no building mapping for good '{good}' (tag {tag})")
    return b


def read_table():
    rows = []
    with open(os.path.join(HERE, "SELECT_ECOBOOST_FINAL_v2.csv"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.startswith("tag,"):
                continue
            parts = [p.strip() for p in line.rstrip("\n").split(",")]
            if len(parts) < 6 or not parts[0]:
                continue
            rows.append({
                "tag": parts[0], "name": parts[1], "tier": int(parts[2]),
                "champ": parts[3], "support": parts[4].split(), "flavor": parts[5].split(),
            })
    return rows


def write_vic3(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")


def gen_effects(rows, grain_map):
    L = [
        "# =============================================================================",
        "# Top40EcoBoostMod - per-nation eco setup (GENERATED by gen_ecoboost_configs.py).",
        "# DO NOT HAND-EDIT - edit SELECT_ECOBOOST_FINAL_v2.csv and re-run.",
        "# eco_setup_<TAG> (day-1, eco.2): ONE champ-category throughput/wage modifier (20yr) + the",
        "#   global SoL/edu modifier (whole game) + first spread pulse. (FLAVOUR is no longer seeded",
        "#   here — it is build-once, so it moved to HISTORY: common/history/buildings/zz_eco_flavour.txt.)",
        "# eco_pulse_<TAG> (re-run yearly via eco.5): spread champ (N=tier/2) + support (N=tier/4)",
        "#   across states via eco_pulse_spread (covers newly-annexed states). No per-state modifiers.",
        "# =============================================================================",
        "",
        "# Set the runtime-safe flags at startup (all targets alive). var:eco_target -> the generic",
        "# eco_is_target_country check; var:eco_tag_<TAG> -> the per-tag eco.2/eco.5 dispatch. Uses",
        "# c:TAG ?= (scoping) so it never errors on a missing tag.",
        "eco_set_target_flags = {",
    ]
    for r in rows:
        L.append(f"\tc:{r['tag']} ?= {{ set_variable = eco_target  set_variable = eco_tag_{r['tag']} }}")
    L += ["}", ""]
    for r in rows:
        tag, tier = r["tag"], r["tier"]
        champ_b = building_for(r["champ"], tag, grain_map)
        cat = champ_cat(r["champ"])
        champ_n = max(1, tier // 2)
        sup_n = max(1, tier // 4)
        L.append(f"# ---- {r['name']} ({tag}): champ {r['champ']} [{cat}] N={champ_n}; "
                 f"support x{len(r['support'])} N={sup_n}; flavour x{len(r['flavor'])} ----")
        L.append(f"eco_setup_{tag} = {{")
        # FLAVOUR moved to history (zz_eco_flavour.txt) — build-once, so no day-1 event needed.
        L.append(f"\tadd_modifier = {{ name = eco_champ_tp_{cat} months = 240 }}")
        L.append("\tadd_modifier = { name = eco_sol_edu_global }")   # whole game (no months)
        L.append(f"\teco_pulse_{tag} = yes")                          # day-1 champ/support spread
        L.append("\tif = { limit = { is_player = yes } trigger_event = { id = eco.4 } }")
        L.append("\teco_cleanup_flags = yes")
        L.append("}")
        L.append(f"eco_pulse_{tag} = {{")
        L.append(f"\teco_pulse_spread = {{ B = {champ_b} N = {champ_n} TYPE = champ }}")
        for g in r["support"]:
            b = building_for(g, tag, grain_map)
            L.append(f"\teco_pulse_spread = {{ B = {b} N = {sup_n} TYPE = support }}")
        L.append("}")
        L.append("")
    return L


def gen_events(rows, grain_map):
    L = [
        "namespace = eco",
        "",
        "# =============================================================================",
        "# Top40EcoBoostMod - event pipeline. eco.2 (day-1 setup) + eco.5 (yearly pulse) dispatch",
        "# are GENERATED 40-tag if-ladders. DO NOT HAND-EDIT those blocks; edit the CSV + re-run.",
        "# eco.4 is static. (Yearly: on_yearly_pulse -> eco_yearly -> every target -> eco.5.)",
        "# =============================================================================",
        "",
        "# ---- per-nation build pass -------------------------------------------------",
        "eco.2 = {",
        "\ttype = country_event",
        "\thidden = yes",
        "",
        "\timmediate = {",
        "\t\teco_generic_flavour = yes   # wood/grain/food anti-death-spiral seed for EVERY target (ROOT set here)",
    ]
    for r in rows:
        L.append(f"\t\tif = {{ limit = {{ has_variable = eco_tag_{r['tag']} }} eco_setup_{r['tag']} = yes }}")
    L += [
        "\t}",
        "}",
        "",
        "# ---- yearly pulse: re-run the champ/support spread for all 40 (covers annexed states) -",
        "eco.5 = {",
        "\ttype = country_event",
        "\thidden = yes",
        "",
        "\timmediate = {",
    ]
    for r in rows:
        L.append(f"\t\tif = {{ limit = {{ has_variable = eco_tag_{r['tag']} }} eco_pulse_{r['tag']} = yes }}")
    L += [
        "\t}",
        "}",
        "",
        "# ---- player-only notification: the eco-seed has run ------------------------",
        "eco.4 = {",
        "\ttype = country_event",
        "",
        "\ttitle = eco.4.t",
        "\tdesc = eco.4.d",
        "",
        '\tevent_image = { video = "unspecific_world_fair" }',
        '\ticon = "gfx/interface/icons/event_icons/event_industry.dds"',
        "",
        "\tduration = 5",
        "",
        "\toption = {",
        "\t\tname = eco.4.a",
        "\t\tdefault_option = yes",
        "\t}",
        "}",
    ]
    return L


def gen_target_trigger(rows):
    """eco_is_target_country = has_variable eco_target (RUNTIME-SAFE). A raw `this = c:TAG` OR list
    errors "Invalid right side during comparison 'c'" once any tag is annexed (the yearly pulse
    hits dead tags). So eco_set_target_flags sets var:eco_target on every target at startup (via
    c:TAG ?=, safe), and this trigger just checks the flag — same pattern as mdp_is_expand_country."""
    return [
        "# =============================================================================",
        "# Top40EcoBoostMod - target-nation check (GENERATED). RUNTIME-SAFE: checks the flag set",
        "# by eco_set_target_flags at startup; never compares this = c:DEADTAG. DO NOT HAND-EDIT.",
        "# =============================================================================",
        "eco_is_target_country = {",
        "\thas_variable = eco_target",
        "}",
    ]


def gen_flavour_history(rows, grain_map, unused):
    """Build-once flavour RGOs as HISTORY (user design rule: history > day-1 event). Each flavour good
    -> the tag's highest-capacity state that HAS that RGO slot, so 'no slot' errors can't occur.
    Returns (lines, excluded); excluded = (tag, good, rgo_base) with no slot in any owned state."""
    L = [
        "# =============================================================================",
        "# Top40EcoBoostMod - per-nation FLAVOUR seeds (GENERATED by gen_ecoboost_configs.py).",
        "# DO NOT HAND-EDIT - edit SELECT_ECOBOOST_FINAL_v2.csv and re-run.",
        "# Build-once flavour RGOs placed at GAME SETUP via HISTORY (NOT a day-1 event - user design",
        "# rule). Each good goes in the tag's highest-capacity state that has the RGO slot",
        "# (unused_rgo_by_state.csv), so 'state has no RGO slot' errors can't occur; no-slot tuples are",
        "# SKIPPED (see the generator report).",
        "# =============================================================================",
        "BUILDINGS = {",
    ]
    excluded = []
    for r in rows:
        tag = r["tag"]
        by_state = {}  # state -> [building, ...] so multiple seeds in one state share ONE block
        # (1) per-nation FLAVOUR goods: +1 in the highest-capacity state that has the slot
        for g in r["flavor"]:
            b = building_for(g, tag, grain_map)
            rgo_base = b[len("building_"):] if b.startswith("building_") else b
            cands = [(st, cp) for st, cp in unused.get((tag, rgo_base), []) if (tag, st) not in FLAVOUR_STATE_EXCLUDE]
            if not cands:
                excluded.append((tag, g, rgo_base))
                continue
            state = max(cands, key=lambda x: x[1])[0]
            by_state.setdefault(state, []).append(b)
        # (2) GENERIC build-once seeds (wood + primary staple), moved from runtime eco_generic_flavour.
        # +1 in each of up to 5 highest-CAPACITY states that have the slot (matches the old N=5 spread),
        # capacity-aware so it can't overbuild (fixes the Macao/Friesland/Estremadura logging reductions).
        # Food-industry stays runtime (tech-gated — history can't check the tech).
        for st in _top_n(unused, tag, "logging_camp", 5):
            by_state.setdefault(st, []).append("building_logging_camp")
        staple_b = grain_map.get(tag, "building_wheat_farm")
        for st in _top_n(unused, tag, staple_b[len("building_"):], 5):
            by_state.setdefault(st, []).append(staple_b)
        # emit one block per (tag, state); dedup identical buildings
        for state, blds in by_state.items():
            L.append(f"\ts:STATE_{state} = {{")
            L.append(f"\t\tregion_state:{tag} = {{")
            for b in dict.fromkeys(blds):
                L += [
                    "\t\t\tcreate_building = {",
                    f'\t\t\t\tbuilding = "{b}"',
                    f'\t\t\t\tadd_ownership = {{ country = {{ country = "c:{tag}" levels = 1 }} }}',
                    "\t\t\t\treserves = 1",
                    "\t\t\t}",
                ]
            L.append("\t\t}")
            L.append("\t}")
    L.append("}")
    return L, excluded


def main():
    rows = read_table()
    grain_map = grain_farm_by_tag()

    write_vic3(EFFECTS_OUT, gen_effects(rows, grain_map))
    write_vic3(EVENTS_OUT, gen_events(rows, grain_map))
    write_vic3(TARGET_OUT, gen_target_trigger(rows))
    unused = load_unused_rgo()
    flav_lines, flav_excluded = gen_flavour_history(rows, grain_map, unused)
    write_vic3(FLAVOUR_OUT, flav_lines)
    # the 40 per-tag champ_tp modifiers are RETIRED (replaced by 3 hand-defined category
    # modifiers in eco_modifiers.txt); remove the stale generated file if present.
    stale = os.path.join(MOD, "common", "static_modifiers", "eco_champ_tp_generated.txt")
    if os.path.exists(stale):
        os.remove(stale)
        print("removed stale eco_champ_tp_generated.txt (now 3 hand modifiers + global SoL/edu)")

    # champ -> modifier map for human review (user ask, txt_files_list row 41)
    map_out = os.path.join(HERE, "eco_champ_modifier_map.csv")
    with open(map_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tag", "country", "tier", "champ_good", "champ_category", "modifier"])
        for r in rows:
            cat = champ_cat(r["champ"])
            w.writerow([r["tag"], r["name"], r["tier"], r["champ"], cat, f"eco_champ_tp_{cat}"])

    print(f"wrote eco_setup_generated.txt   ({len(rows)} eco_setup_<TAG> + eco_pulse_<TAG>)")
    print(f"wrote eco_events.txt            (eco.2 setup + eco.5 yearly-pulse dispatch + eco.4)")
    print(f"wrote eco_target_triggers.txt   (eco_is_target_country = {len(rows)} tags)")
    print(f"wrote eco_champ_modifier_map.csv ({len(rows)} tags -> champ good + modifier)")
    placed = sum(1 for ln in flav_lines if "create_building" in ln)
    print(f"wrote zz_eco_flavour.txt        ({placed} history seeds [flavour+wood+staple]; {len(flav_excluded)} flavour skipped no-slot)")
    if flav_excluded:
        print("  SKIPPED no-slot:", ", ".join(f"{t}:{g}" for t, g, _ in flav_excluded))
    from collections import Counter
    cats = Counter(champ_cat(r["champ"]) for r in rows)
    print(f"  champ categories: {dict(cats)}")
    for r in rows[:3]:
        print(f"  {r['tag']}: champ={r['champ']} [{champ_cat(r['champ'])}] N={max(1,r['tier']//2)} "
              f"support N={max(1,r['tier']//4)}")


if __name__ == "__main__":
    main()
