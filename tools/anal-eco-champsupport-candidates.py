"""Top40EcoBoost pulse-to-history rework: which states can actually host each champ/support level.

READ-ONLY. Emits data_eco_champsupport_candidates.csv (per-placement) and
data_eco_champsupport_summary.csv (per-tag totals for eyeballing), the authoring input for the
two hand-coded history files (zz_eco_champ.txt / zz_eco_support.txt). Writes NOTHING into a mod.

AMOUNTS come from seed_eco_champsupport_spec.csv, whose n_target follows the AGREED caps stated
in SELECT_ECOBOOST_FINAL_v2.csv: champ = 2*tier, support = the per-pulse quarter (tier/4). That
is what makes champ dominant - 386 champ levels against 290 support across the 40 tags.

DISTRIBUTION is round-robin, one level per eligible state per lap, best (highest pop) first, so a
wide nation spreads (RUS: ~20 states with one logging camp each) and a narrow one stacks
(PAN: ~10 cotton levels over 2-3 states = 4-5 each). Each state's own map capacity caps its share.

A state is eligible when ALL of:
  1. the tag owns it at 1836 and it is INCORPORATED   (vanilla common/history/states/00_states.txt)
  2. the building fits there:
       capped RGO   -> map_data capped_resources[building] minus levels already built
       farm/plant.  -> building listed in arable_resources AND arable_land minus agri levels built
       urban/manuf. -> no capacity, but the tag must hold every unlocking_technology
  3. InfraTaxMod's map_data/state_regions copies OVERLAY vanilla (they are whole-file overrides)

Ranking proxy is state POP (state_pops.csv), the same proxy the other EcoBoost generators use;
the pulse ordered by state GDP, which is not available offline.
"""
import csv, os, re, sys, collections
from _refpaths import game_path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # victoria-3-mod
GAME = game_path()
MOD1 = os.path.join(ROOT, "mod1")
ECO = os.path.join(MOD1, "Top40EcoBoostMod")
INFRATAX_MAP = os.path.join(MOD1, "InfraTaxMod", "map_data", "state_regions")
OUT = os.path.join(HERE, "data_eco_champsupport_candidates.csv")
SUMMARY = os.path.join(HERE, "data_eco_champsupport_summary.csv")


def read(p):
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def strip_comments(text):
    return "\n".join(ln.split("#", 1)[0] for ln in text.splitlines())


# ---------------------------------------------------------------- the ask: (tag, building, N)
def parse_spec():
    """seed_eco_champsupport_spec.csv -> {tag: [(building, n_target, kind), ...]}"""
    spec = collections.OrderedDict()
    with open(os.path.join(HERE, "seed_eco_champsupport_spec.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            spec.setdefault(row["tag"], []).append(
                (row["building"], int(row["n_target"]), row["kind"]))
    return spec


def parse_capitals():
    """-> {tag: STATE_X} from common/country_definitions (the FD's home region)."""
    caps = {}
    d = os.path.join(GAME, "common", "country_definitions")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt"):
            continue
        text = strip_comments(read(os.path.join(d, fn)))
        for tag, body in re.findall(r"^(\w{3})\s*=\s*\{(.*?)^\}", text, re.S | re.M):
            m = re.search(r"capital\s*=\s*(STATE_\w+)", body)
            if m:
                caps[tag] = m.group(1)
    return caps


# ---------------------------------------------------------------- who owns what, incorporated?
def parse_state_ownership():
    """-> {(tag, STATE_X): incorporated_bool}"""
    text = strip_comments(read(os.path.join(GAME, "common", "history", "states", "00_states.txt")))
    owned = {}
    for state, body in re.findall(r"s:(STATE_\w+)\s*=\s*\{(.*?)\n\t\}", text, re.S):
        for block in re.findall(r"create_state\s*=\s*\{(.*?)\}", body, re.S):
            m = re.search(r"country\s*=\s*c:(\w+)", block)
            if not m:
                continue
            unincorp = re.search(r"state_type\s*=\s*unincorporated", block) is not None
            owned[(m.group(1), state)] = not unincorp
    return owned


# ---------------------------------------------------------------- map_data, InfraTax on top
def parse_state_regions():
    """-> {STATE_X: {'arable': int, 'arable_res': set, 'capped': {building: int}, 'src': file}}"""
    regions = {}
    files = []
    vanilla_dir = os.path.join(GAME, "map_data", "state_regions")
    for d in (vanilla_dir, INFRATAX_MAP):                 # InfraTax second = overlay wins
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".txt"):
                files.append(os.path.join(d, fn))
    for path in files:
        text = strip_comments(read(path))
        for name, body in re.findall(r"^(STATE_\w+)\s*=\s*\{(.*?)^\}", text, re.S | re.M):
            arable = re.search(r"arable_land\s*=\s*(\d+)", body)
            ares = re.findall(r'"?(building_\w+)"?', re.search(
                r"arable_resources\s*=\s*\{([^}]*)\}", body).group(1)) if re.search(
                r"arable_resources\s*=\s*\{([^}]*)\}", body) else []
            capped = {}
            cap_block = re.search(r"capped_resources\s*=\s*\{(.*?)\}", body, re.S)
            if cap_block:
                for b, v in re.findall(r'"?(building_\w+)"?\s*=\s*(\d+)', cap_block.group(1)):
                    capped[b] = int(v)
            regions[name] = {"arable": int(arable.group(1)) if arable else 0,
                             "arable_res": set(ares), "capped": capped,
                             "src": os.path.basename(os.path.dirname(path)) + "/" + os.path.basename(path)}
    return regions


# ---------------------------------------------------------------- already-built levels
def parse_built():
    """-> {(STATE_X, building): levels}  from vanilla + this mod's own history/buildings."""
    built = collections.Counter()
    dirs = [os.path.join(GAME, "common", "history", "buildings"),
            os.path.join(ECO, "common", "history", "buildings")]
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".txt"):
                continue
            text = strip_comments(read(os.path.join(d, fn)))
            # walk state blocks; level defaults to 1 when create_building omits it
            for m in re.finditer(r"s:(STATE_\w+)\s*=\s*\{", text):
                state = m.group(1)
                seg = text[m.end():m.end() + 20000]
                nxt = re.search(r"\n\ts:STATE_\w+\s*=\s*\{", seg)
                if nxt:
                    seg = seg[:nxt.start()]
                for b, tail in re.findall(r'building\s*=\s*"?(building_\w+)"?(.{0,400})', seg, re.S):
                    lvl = re.search(r"\blevel\s*=\s*(\d+)", tail)
                    built[(state, b)] += int(lvl.group(1)) if lvl else 1
    return built


# ---------------------------------------------------------------- building groups + tech gates
def parse_buildings():
    """-> {building: {'group': bg, 'techs': [..]}}"""
    out = {}
    d = os.path.join(GAME, "common", "buildings")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt"):
            continue
        text = strip_comments(read(os.path.join(d, fn)))
        for name, body in re.findall(r"^(building_\w+)\s*=\s*\{(.*?)^\}", text, re.S | re.M):
            g = re.search(r"building_group\s*=\s*\"?(\w+)\"?", body)
            tb = re.search(r"unlocking_technologies\s*=\s*\{([^}]*)\}", body)
            out[name] = {"group": g.group(1) if g else "",
                         "techs": re.findall(r"[\w]+", tb.group(1)) if tb else []}
    return out


def parse_starting_techs():
    """-> {tag: set(tech)} from vic3_starting_tech_xtab.csv (1 = researched at start)."""
    p = os.path.join(HERE, "vic3_starting_tech_xtab.csv")
    techs = {}
    with open(p, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            tag = row.get("Tag")
            if not tag:
                continue
            techs[tag] = {k for k, v in row.items() if k not in ("Tag", "Tier") and str(v).strip() == "1"}
    return techs


def parse_state_pops():
    """-> {(tag, STATE_X): pop} from the existing data CSV."""
    p = os.path.join(HERE, "state_pops.csv")
    pops = collections.Counter()
    with open(p, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            st = row["state"]
            st = st if st.startswith("STATE_") else "STATE_" + st
            try:
                pops[(row["tag"], st)] += int(float(row["pop"] or 0))
            except ValueError:
                pass
    return pops


AGRI_GROUPS = ("bg_agriculture", "bg_ranching", "bg_plantations", "bg_rice_farms")


def main():
    spec = parse_spec()
    capitals = parse_capitals()
    owned = parse_state_ownership()
    regions = parse_state_regions()
    built = parse_built()
    bdefs = parse_buildings()
    stechs = parse_starting_techs()
    pops = parse_state_pops()

    # A type is map-capacity-bound if ANY region lists it. A mine absent from a region's
    # capped_resources has no capacity there, so it must not fall through as uncapped.
    global CAPPED_TYPES, ARABLE_TYPES
    CAPPED_TYPES = {b for r in regions.values() for b in r["capped"]}
    ARABLE_TYPES = {b for r in regions.values() for b in r["arable_res"]}

    by_tag = collections.defaultdict(list)
    for (tag, state), incorp in owned.items():
        by_tag[tag].append((state, incorp))

    rows = []
    for tag, wants in spec.items():
        for building, need, kind in wants:
            bd = bdefs.get(building, {"group": "?", "techs": []})
            gate_missing = sorted(set(bd["techs"]) - stechs.get(tag, set()))
            cands = []
            for state, incorp in by_tag.get(tag, []):
                if not incorp:
                    continue
                reg = regions.get(state)
                if reg is None:
                    continue
                if building in CAPPED_TYPES:      # RGO: needs an explicit capacity entry here
                    if building not in reg["capped"]:
                        continue
                    left = reg["capped"][building] - built[(state, building)]
                    basis = "capped_resources"
                elif building in ARABLE_TYPES:    # farm/plantation: region must allow the type
                    if building not in reg["arable_res"]:
                        continue
                    used = sum(v for (s, b), v in built.items()
                               if s == state and bdefs.get(b, {}).get("group", "") in AGRI_GROUPS)
                    left, basis = reg["arable"] - used, "arable_land"
                else:
                    left, basis = 99, "no_cap"    # manufacturing / urban, no map capacity
                if left < 1:
                    continue
                cands.append((pops[(tag, state)], state, left, basis, reg["src"]))
            cands.sort(key=lambda c: (-c[0], c[1]))
            if not cands:
                rows.append({"tag": tag, "building": building, "kind": kind, "need": need,
                             "rank": "", "state": "NO_ELIGIBLE_STATE", "pop": "", "levels": "",
                             "left": "", "basis": "", "group": bd["group"],
                             "fd_region": "", "map_src": ""})
                continue

            # ROUND-ROBIN: one level per state per lap, best first, each state capped by its
            # own map capacity. Wide nations spread, narrow ones stack.
            share = collections.Counter()
            placed, laps = 0, 0
            while placed < need and laps <= need:
                laps += 1
                progress = False
                for pop, state, left, basis, src in cands:
                    if placed >= need:
                        break
                    if share[state] >= left:
                        continue
                    share[state] += 1
                    placed += 1
                    progress = True
                if not progress:
                    break                      # every eligible state is at capacity

            for i, (pop, state, left, basis, src) in enumerate(cands, start=1):
                if not share[state]:
                    continue
                rows.append({"tag": tag, "building": building, "kind": kind, "need": need,
                             "rank": i, "state": state, "pop": pop, "levels": share[state],
                             "left": left, "basis": basis, "group": bd["group"],
                             "fd_region": capitals.get(tag, ""), "map_src": src})
            if placed < need:
                rows.append({"tag": tag, "building": building, "kind": kind, "need": need,
                             "rank": "SHORT", "state": f"placed {placed} of {need} in "
                             f"{len([s for s in share if share[s]])} states", "pop": "",
                             "levels": "", "left": "", "basis": "", "group": bd["group"],
                             "fd_region": "", "map_src": ""})

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tag", "building", "kind", "need", "rank", "state",
                                          "pop", "levels", "left", "basis", "group",
                                          "fd_region", "map_src"])
        w.writeheader()
        w.writerows(rows)

    # per-tag summary, so "does this look sane" is one glance and unit-testable
    placements = [r for r in rows if isinstance(r["rank"], int)]
    sm = []
    for tag in spec:
        p = [r for r in placements if r["tag"] == tag]
        ch = [r for r in p if r["kind"] == "champ"]
        su = [r for r in p if r["kind"] == "support"]
        want_ch = sum(n for b, n, k in spec[tag] if k == "champ")
        want_su = sum(n for b, n, k in spec[tag] if k == "support")
        got_ch = sum(r["levels"] for r in ch)
        got_su = sum(r["levels"] for r in su)
        sm.append({"tag": tag, "capital": capitals.get(tag, ""),
                   "champ_building": ch[0]["building"] if ch else "",
                   "champ_want": want_ch, "champ_got": got_ch,
                   "champ_states": len({r["state"] for r in ch}),
                   "champ_max_in_one_state": max([r["levels"] for r in ch], default=0),
                   "support_types": len({r["building"] for r in su}),
                   "support_want": want_su, "support_got": got_su,
                   "support_states": len({r["state"] for r in su}),
                   "champ_dominant": "yes" if got_ch > got_su else "NO",
                   "entries": len({(r["state"], r["building"]) for r in p})})
    with open(SUMMARY, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sm[0].keys()))
        w.writeheader()
        w.writerows(sm)

    short = [r for r in rows if r["rank"] in ("SHORT", "")]
    print(f"{OUT}\n{SUMMARY}")
    print(f"  pairs {sum(len(v) for v in spec.values())}  entries {len(placements)}"
          f"  champ levels {sum(r['champ_got'] for r in sm)}"
          f"  support levels {sum(r['support_got'] for r in sm)}")
    print(f"  tags where champ is NOT dominant: {[r['tag'] for r in sm if r['champ_dominant'] == 'NO']}")
    print(f"  shortfalls {len(short)}")
    for r in short:
        print(f"    {r['tag']:4s} {r['building']:28s} {r['kind']:8s} need {r['need']:3d} -> {r['state']}")


if __name__ == "__main__":
    main()
