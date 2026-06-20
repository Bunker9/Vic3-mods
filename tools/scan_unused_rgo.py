#!/usr/bin/env python3
"""
scan_unused_rgo.py -- per-state UNUSED resource-gathering operations for the 40 Mod-1 tags.

For every state a nation owns, lists each RGO-type resource the state HAS potential for but
where the nation has built ZERO levels at 1836 -- i.e. latent extraction/agriculture the
nation could turn on as a "flavour" build later. Covers:
  - arable_resources  (plantations + farms: cotton/silk/tea/coffee/dye/tobacco/rice/...)
  - capped_resources  (mines + logging + whaling + fishing, with the state's level cap)
  - resource {}       (discoverable: oil rigs etc., with the deposit amount)

Reads (read-only) from the game install:
  map_data/state_regions/*.txt   -> per-state arable_land, arable_resources, capped_resources,
                                     resource{} (discoverable)
  common/history/states/*.txt    -> ownership: which tag owns each STATE_X
  common/history/buildings/*.txt -> what each tag has actually BUILT in each STATE_X
  localization/english/*states*.yml -> display names

"Owned by tag" = the tag has a create_state block for that state (incl. partial ownership).
"Built" = the tag's region_state in that state has >=1 level of that building. A state owned
but with NO buildings at all still appears (its whole RGO potential is "unused") -- those
empty-but-resource-rich states are the most interesting flavour candidates.

Outputs (hk-config/tools/):
  unused_rgo_by_state.csv   -- one row per (tag, state, unused_rgo):
       tag | country | state | rgo | kind | capacity | state_arable_land
     kind = plantation | farm | capped | discoverable. capacity = level cap (capped),
     deposit amount (discoverable), or "" for arable (the cap is the shared state arable_land,
     shown in its own column).
  unused_rgo_by_nation.csv  -- rollup per tag: distinct unused plantations / farms / capped /
     discoverable across all its states (quick "what could this nation add" scan).

Usage: python scan_unused_rgo.py [GAME_DIR]
"""
import os, re, sys, csv, glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
from _refpaths import game_path
DEFAULT_GAME = game_path()

# --- tokenizer/parser -------------------------------------------------------
_T = re.compile(r"""\s+|\#[^\n]*|(?P<op>\?=|<=|>=|==|=|<|>)|(?P<lb>\{)|(?P<rb>\})|(?P<qs>"[^"]*")|(?P<w>[^\s{}=<>#"]+)""", re.VERBOSE)
def tok(t): return [m.group() for m in _T.finditer(t) if m.lastgroup in ("op", "lb", "rb", "qs", "w")]
def parse_block(ts, i):
    items, n = [], len(ts)
    while i < n:
        t = ts[i]
        if t == "}":
            return items, i + 1
        nx = ts[i + 1] if i + 1 < n else None
        if nx in ("=", "?=", "==", "<", ">", "<=", ">="):
            k, j = t, i + 2
            if j < n and ts[j] == "{":
                v, k2 = parse_block(ts, j + 1)
            else:
                v, k2 = (ts[j] if j < n else None), j + 1
            items.append((k, v)); i = k2
        elif t == "{":
            v, k2 = parse_block(ts, i + 1); items.append((None, v)); i = k2
        else:
            items.append(t); i += 1
    return items, i
def parse_file(p):
    with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
        return parse_block(tok(f.read()), 0)[0]
def unq(v): return v.strip('"') if isinstance(v, str) else v
def kv(items, key):
    for it in items:
        if isinstance(it, tuple) and it[0] == key:
            return it[1]
    return None
def kv_all(items, key):
    return [it[1] for it in items if isinstance(it, tuple) and it[0] == key]
def to_int(v):
    try: return int(float(unq(v)))
    except Exception: return 0
def sum_levels(block):
    total = 0
    for it in block or []:
        if isinstance(it, tuple):
            k, v = it
            if k == "levels":
                try: total += int(float(unq(v)))
                except Exception: pass
            elif isinstance(v, list):
                total += sum_levels(v)
        elif isinstance(it, list):
            total += sum_levels(it)
    return total

def is_plantation(b): return b.endswith("_plantation") or b == "building_vineyard"
def is_farm(b): return b.endswith("_farm") or b == "building_livestock_ranch"

def load_loc(game, *globs):
    names = {}
    rx = re.compile(r'^\s*([A-Za-z0-9_]+)\s*:\s*\d*\s*"(.*)"\s*$')
    for gpat in globs:
        for fp in glob.glob(os.path.join(game, "localization", "english", gpat)):
            with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
                for line in f:
                    m = rx.match(line)
                    if m:
                        names.setdefault(m.group(1), m.group(2))
    return names


def main():
    game = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GAME
    if not os.path.isdir(game):
        sys.exit(f"Game dir not found: {game}")

    want = {}
    with open(os.path.join(HERE, "mod-nations.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            want[r["tag"]] = r["country"]

    state_names = load_loc(game, "*state_regions*l_english.yml", "*states*l_english.yml")

    # --- state -> potential ---------------------------------------------------
    pot = {}
    for fp in glob.glob(os.path.join(game, "map_data", "state_regions", "*.txt")):
        for it in parse_file(fp):
            if not (isinstance(it, tuple) and isinstance(it[1], list) and str(it[0]).startswith("STATE_")):
                continue
            body = it[1]
            arr = kv(body, "arable_resources")
            arable = [unq(x) for x in arr if isinstance(x, str)] if isinstance(arr, list) else []
            capped = {}
            cap = kv(body, "capped_resources")
            if isinstance(cap, list):
                for sub in cap:
                    if isinstance(sub, tuple) and isinstance(sub[0], str) and sub[0].startswith("building_"):
                        capped[sub[0]] = to_int(sub[1])
            disc = {}
            for rb in kv_all(body, "resource"):
                if isinstance(rb, list):
                    typ = unq(kv(rb, "type"))
                    amt = to_int(kv(rb, "undiscovered_amount")) + to_int(kv(rb, "discovered_amount"))
                    if typ:
                        disc[typ] = disc.get(typ, 0) + amt
            pot[it[0]] = {"arable_land": to_int(kv(body, "arable_land")),
                          "arable": arable, "capped": capped, "disc": disc}

    # --- ownership: tag -> set(STATE_X) --------------------------------------
    # history/states may or may not wrap entries in a STATES block -> tolerate both.
    owns = defaultdict(set)
    for fp in glob.glob(os.path.join(game, "common", "history", "states", "*.txt")):
        top = parse_file(fp)
        entries = kv(top, "STATES")
        entries = entries if isinstance(entries, list) else top
        for it in entries:
            if not (isinstance(it, tuple) and isinstance(it[0], str)):
                continue
            key = it[0]                       # "s:STATE_X" (wrapped) or "STATE_X"
            state = key.split(":", 1)[1] if key.startswith("s:") else key
            if not state.startswith("STATE_"):
                continue
            for cs in kv_all(it[1], "create_state"):
                c = unq(kv(cs, "country"))
                if c and c.startswith("c:"):
                    owns[c[2:]].add(state)

    # --- built: (tag, STATE_X) -> set(building) ------------------------------
    built = defaultdict(set)
    for fp in glob.glob(os.path.join(game, "common", "history", "buildings", "*.txt")):
        for it in kv(parse_file(fp), "BUILDINGS") or []:
            if not (isinstance(it, tuple) and isinstance(it[0], str) and it[0].startswith("s:")):
                continue
            state = it[0].split(":", 1)[1]
            for sub in it[1] or []:
                if not (isinstance(sub, tuple) and isinstance(sub[0], str) and sub[0].startswith("region_state:")):
                    continue
                tag = sub[0].split(":", 1)[1]
                for cb in kv_all(sub[1], "create_building"):
                    b = unq(kv(cb, "building"))
                    if b and sum_levels(cb) > 0:
                        built[(tag, state)].add(b)

    # --- diff ----------------------------------------------------------------
    detail = []
    roll = defaultdict(lambda: {"plantation": set(), "farm": set(), "capped": set(), "discoverable": set()})
    def short(b): return b.replace("building_", "")
    for tag in want:
        for state in sorted(owns.get(tag, ())):
            p = pot.get(state)
            if not p:
                continue
            have = built.get((tag, state), set())
            disp = state_names.get(state, state.replace("STATE_", ""))
            for b in p["arable"]:
                if b in have:
                    continue
                kind = "plantation" if is_plantation(b) else ("farm" if is_farm(b) else "arable")
                detail.append((tag, want[tag], disp, short(b), kind, "", p["arable_land"]))
                roll[tag][kind if kind in roll[tag] else "farm"].add(short(b))
            for b, capn in p["capped"].items():
                if b in have:
                    continue
                detail.append((tag, want[tag], disp, short(b), "capped", capn, p["arable_land"]))
                roll[tag]["capped"].add(short(b))
            for b, amt in p["disc"].items():
                if b in have:
                    continue
                detail.append((tag, want[tag], disp, short(b), "discoverable", amt, p["arable_land"]))
                roll[tag]["discoverable"].add(short(b))

    detail.sort(key=lambda r: (r[1], r[2], r[4], r[3]))
    d_out = os.path.join(HERE, "unused_rgo_by_state.csv")
    with open(d_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tag", "country", "state", "rgo", "kind", "capacity", "state_arable_land"])
        w.writerows(detail)

    n_out = os.path.join(HERE, "unused_rgo_by_nation.csv")
    with open(n_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tag", "country", "n_states", "unused_plantations", "unused_farms",
                    "unused_capped", "unused_discoverable"])
        for tag in sorted(want, key=lambda t: want[t]):
            r = roll[tag]
            w.writerow([tag, want[tag], len(owns.get(tag, ())),
                        " ".join(sorted(r["plantation"])), " ".join(sorted(r["farm"])),
                        " ".join(sorted(r["capped"])), " ".join(sorted(r["discoverable"]))])

    print(f"Wrote {os.path.basename(d_out)} ({len(detail)} unused-RGO rows)")
    print(f"Wrote {os.path.basename(n_out)} ({len(want)} nations)")


if __name__ == "__main__":
    main()
