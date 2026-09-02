#!/usr/bin/env python3
"""
anal-naval-caps-vs-history.py - do any nations START over NavalCapMod's per state caps?

Reads (READ-ONLY) from the Victoria 3 install:
  common/history/buildings/*.txt   -> create_building blocks: state, building, levels
  common/history/countries/*.txt   -> activate_law = law_type:law_<navy model law>
  common/laws/00_navy_model.txt    -> the law group's member order (first = default law)

A country that never activates a Navy Model law runs the group's DEFAULT, which is the
first law defined in the group file (law_merchant_navy). That is why almost no country
carries an explicit activate_law for this group.

Output: tools/data_naval_caps_vs_history.csv, one row per (tag, state, building):
  tag | state | building | levels | navy_law | law_source | cap | over_by

`levels` = the sum of every levels= inside the create_building block (all ownership
shares), i.e. the physical level standing in that state at 1836.

Usage: python anal-naval-caps-vs-history.py [GAME_DIR]
"""
import os, re, sys, csv, glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _refpaths import game_path

# NavalCapMod per state caps - keep in step with
# mod1/NavalCapMod/common/laws/nvc_navy_model_caps.txt
CAPS = {
    "law_merchant_navy":     {"building_port": 50, "building_naval_administration": 20},
    "law_jeune_ecole":       {"building_port": 30, "building_naval_administration": 50},
    "law_professional_navy": {"building_port": 20, "building_naval_administration": 60},
    "law_diplomatic_navy":   {"building_port": 40, "building_naval_administration": 30},
}
WATCHED = ("building_port", "building_naval_administration")


def default_navy_law(game):
    """First law defined in 00_navy_model.txt = the law group's default."""
    path = os.path.join(game, "common", "laws", "00_navy_model.txt")
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            m = re.match(r"^(law_\w+)\s*=\s*\{", line)
            if m:
                return m.group(1)
    raise SystemExit("could not read the navy model law group")


def country_navy_laws(game):
    """tag -> explicitly activated navy model law, from history/countries."""
    out = {}
    # country blocks are written `c:FRA ?= {` - the ?= operator must be allowed for
    tag_pat = re.compile(r"c:([A-Z]{3})\s*\??=\s*\{")
    pat = re.compile(r"activate_law\s*=\s*law_type:(law_\w+)")
    for path in glob.glob(os.path.join(game, "common", "history", "countries", "*.txt")):
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
        for m in pat.finditer(text):
            law = m.group(1)
            if law not in CAPS:
                continue
            tags = tag_pat.findall(text[:m.start()])
            if tags:
                out[tags[-1]] = law
    return out


def block_end(text, brace_idx):
    """index just past the } matching the { at brace_idx."""
    depth, i = 0, brace_idx
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def history_naval_buildings(game):
    """(tag, state, building) -> summed levels, PER STATE, from history/buildings.

    Shape is BUILDINGS={ s:STATE_X={ region_state:TAG={ create_building={..} } } },
    so the owner is the region_state tag, NOT the add_ownership country (which can be
    a financial district in another country).
    """
    rows = defaultdict(int)
    st_pat = re.compile(r"s:(STATE_\w+)\s*\??=\s*\{")
    rs_pat = re.compile(r"region_state:([A-Z]{3})\s*\??=\s*\{")
    cb_pat = re.compile(r"create_building\s*\??=\s*\{")
    for path in glob.glob(os.path.join(game, "common", "history", "buildings", "*.txt")):
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
        for sm in st_pat.finditer(text):
            state = sm.group(1)
            s_end = block_end(text, text.index("{", sm.end() - 1))
            for rm in rs_pat.finditer(text, sm.end(), s_end):
                tag = rm.group(1)
                r_end = block_end(text, text.index("{", rm.end() - 1))
                for cm in cb_pat.finditer(text, rm.end(), r_end):
                    body = text[cm.end() - 1:block_end(text, cm.end() - 1)]
                    bm = re.search(r'building\s*=\s*"?(building_\w+)"?', body)
                    if not bm or bm.group(1) not in WATCHED:
                        continue
                    levels = sum(int(x) for x in re.findall(r"levels\s*=\s*(\d+)", body))
                    lvl = re.search(r"\blevel\s*=\s*(\d+)", body)
                    if lvl:
                        levels = max(levels, int(lvl.group(1)))
                    rows[(tag, state, bm.group(1))] += levels
    return rows


def main():
    game = sys.argv[1] if len(sys.argv) > 1 else game_path()
    default_law = default_navy_law(game)
    explicit = country_navy_laws(game)
    built = history_naval_buildings(game)

    out = []
    for (tag, state, building), levels in sorted(built.items()):
        law = explicit.get(tag, default_law)
        cap = CAPS[law][building]
        out.append({
            "tag": tag, "state": state, "building": building, "levels": levels,
            "navy_law": law,
            "law_source": "history" if tag in explicit else "group default",
            "cap": cap, "over_by": max(0, levels - cap),
        })

    dest = os.path.join(HERE, "data_naval_caps_vs_history.csv")
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    over = [r for r in out if r["over_by"] > 0]
    ten = [r for r in out if r["levels"] > 10]
    print(f"default navy law: {default_law}   explicit in history: {len(explicit)} countries")
    print(f"{len(out)} rows -> {dest}")
    for label, rows in (("OVER CAP", over), ("above 10 levels", ten)):
        print(f"\n--- {label}: {len(rows)} ---")
        for r in sorted(rows, key=lambda r: -r["levels"])[:40]:
            print(f"  {r['tag']} {r['state']:28} {r['building']:30} "
                  f"lvl {r['levels']:3}  {r['navy_law']:22} cap {r['cap']:3} "
                  f"over_by {r['over_by']}")
    for building in WATCHED:
        lv = [r["levels"] for r in out if r["building"] == building]
        if lv:
            print(f"\n{building}: {len(lv)} states, max {max(lv)}, total {sum(lv)}")


if __name__ == "__main__":
    main()
