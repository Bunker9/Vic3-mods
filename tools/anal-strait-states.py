"""anal-strait-states.py - every vanilla STRAIT, with the state region either side.

READ-ONLY. Reads the game path from config/refpaths.json.

Sources:
  common/strait_definitions/strait_definitions.txt  first/second_land_endpoint per strait
  map_data/state_regions/*.txt                      provinces = { "xHEX" ... } per STATE_ key
  tools/data_state_region_pop.csv                   day-1 owner tags per state region

Output: tools/data_strait_states.csv
"""

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HK = HERE.parent

PROV_RE = re.compile(r'"(x[0-9A-Fa-f]{6})"')
STATE_RE = re.compile(r'^(STATE_[A-Z0-9_]+)\s*=\s*\{', re.M)


def game_path():
    cfg = json.loads((HK / "config" / "refpaths.json").read_text(encoding="utf-8-sig"))
    p = Path(cfg["game_files_path"])
    if not p.is_dir():
        sys.exit(f"game_files_path not a directory: {p}")
    return p


def province_to_state(game):
    """Map every province hex to its STATE_ key."""
    out = {}
    folder = game / "map_data" / "state_regions"
    for f in sorted(folder.glob("*.txt")):
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        marks = [(m.start(), m.group(1)) for m in STATE_RE.finditer(text)]
        for i, (pos, state) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            block = text[pos:end]
            # only the provinces = { ... } list, not city/port/farm singles
            pm = re.search(r"provinces\s*=\s*\{(.*?)\}", block, re.S)
            if not pm:
                continue
            for hexid in PROV_RE.findall(pm.group(1)):
                out[hexid.upper().replace("X", "x", 1)] = state
    return out


def province_to_tag(game):
    """Map every owned province hex to the tag owning it at 1836 (history/states)."""
    out = {}
    folder = game / "common" / "history" / "states"
    for f in sorted(folder.glob("*.txt")):
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        # Anchor on each `country = c:TAG`, then take its own owned_provinces list.
        # owned_provinces spans multiple lines, so read to the matching brace, not to
        # the first newline-brace (that silently truncated AWS/JAP endpoints).
        for cm in re.finditer(r"country\s*=\s*c:([A-Z0-9]{3})", text):
            pm = re.compile(r"owned_provinces\s*=\s*\{").search(text, cm.end())
            if not pm:
                continue
            close = text.find("}", pm.end())
            if close == -1:
                continue
            for hexid in re.findall(r'"?(x[0-9A-Fa-f]{6})"?', text[pm.end():close]):
                # LAST create_state wins: a province listed twice (Melilla xA0B0C0
                # under both MOR and SPA) belongs to the later block.
                out[norm(hexid)] = cm.group(1)
    return out


def existing_forts(game):
    """(STATE_, TAG) pairs that ALREADY hold a naval fortification in vanilla history."""
    out = set()
    folder = game / "common" / "history" / "buildings"
    state_re = re.compile(r"s:(STATE_[A-Z0-9_]+)\s*=\s*\{")
    rs_re = re.compile(r"region_state:([A-Z0-9]{3})\s*=\s*\{")
    for f in sorted(folder.glob("*.txt")):
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        for m in re.finditer(r'building\s*=\s*"?building_naval_fortification"?', text):
            # nearest preceding s:STATE_ and region_state: headers
            st = None
            for sm in state_re.finditer(text, 0, m.start()):
                st = sm.group(1)
            tag = None
            for rm in rs_re.finditer(text, 0, m.start()):
                tag = rm.group(1)
            if st and tag:
                out.add((st, tag))
    return out


def owners_by_state():
    src = HERE / "data_state_region_pop.csv"
    if not src.exists():
        return {}
    out = {}
    with src.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            out[row["state_region"]] = row.get("owner_tags", "")
    return out


def norm(p):
    p = p.strip().strip('"')
    if not p:
        return ""
    if not p.startswith("x") and not p.startswith("X"):
        p = "x" + p
    return "x" + p[1:].upper()


def main():
    game = game_path()
    p2s = province_to_state(game)
    p2s = {norm(k): v for k, v in p2s.items()}
    p2t = province_to_tag(game)
    owners = owners_by_state()
    forts = existing_forts(game)

    src = game / "common" / "strait_definitions" / "strait_definitions.txt"
    text = src.read_text(encoding="utf-8-sig", errors="replace")
    marks = [(m.start(), m.group(1))
             for m in re.finditer(r"^([a-z0-9_]+)\s*=\s*\{", text, re.M)]
    rows = []
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        block = text[pos:end]

        def field(key):
            m = re.search(key + r"\s*=\s*(x?[0-9A-Fa-f]{6})", block)
            return norm(m.group(1)) if m else ""

        a, b = field("first_land_endpoint"), field("second_land_endpoint")
        tm = re.search(r"type\s*=\s*(\w+)", block)
        sa, sb = p2s.get(a, "?"), p2s.get(b, "?")
        rows.append(
            {
                "strait_id": name,
                "kind": tm.group(1) if tm else "",
                "from_state": sa,
                "from_tag": p2t.get(a, "?"),
                "from_has_fort": "YES" if (sa, p2t.get(a)) in forts else "",
                "to_state": sb,
                "to_tag": p2t.get(b, "?"),
                "to_has_fort": "YES" if (sb, p2t.get(b)) in forts else "",
                "from_owners": owners.get(sa, ""),
                "to_owners": owners.get(sb, ""),
                "endpoints": f"{a}|{b}",
            }
        )

    out = HERE / "data_strait_states.csv"
    cols = ["strait_id", "kind",
            "from_state", "from_tag", "from_has_fort",
            "to_state", "to_tag", "to_has_fort",
            "from_owners", "to_owners", "endpoints"]
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    states = sorted({r["from_state"] for r in rows} | {r["to_state"] for r in rows} | set())
    states = [s for s in states if s != "?"]
    print(f"straits: {len(rows)}   distinct strait states: {len(states)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
