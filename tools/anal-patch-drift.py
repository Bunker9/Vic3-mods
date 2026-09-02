#!/usr/bin/env python3
"""
anal-patch-drift.py - score every mod override against the CURRENT vanilla install.

Ceremony 9 (game patch / release change review). READ-ONLY: reads the Victoria 3 install
and the mod1 worktree, writes one CSV. It never edits a mod file.

Two override surfaces are checked, because a patch breaks them in different ways:

  map_data/state_regions/*.txt   WHOLE-FILE overrides. Merge directives do not work in
                                 map_data, so our file replaces vanilla's by filename and
                                 NOTHING of vanilla in that file survives. Every patch edit
                                 to it is silently reverted.
  common/history/**              ADDITIVE. Nothing overrides; every file applies. The risks
                                 are dangling references, over-cap, and duplicate seeding.

Stages
  1 LAYERS      group install files by mtime; each distinct cluster is a patch layer.
  2 SURFACE     which layer files we override by filename, or reference from history.
  3 STRUCTURE   per state: key added/removed/renamed, id, hex provinces, impassable,
                prime_land, anchors (city/port/farm/mine/wood/naval_exit_id), field-name set.
  4 VALUES      economy fields, cross-checked against our own in-file delta comments
                (`# [Mod] ... - capped:building_coal_mine 0->36`), which record the vanilla
                value at copy time. A comment whose left side no longer matches vanilla is
                the drift signal.
  5 HISTORY     every STATE_/hex/building_/pm_/pop_type/culture/religion token resolves;
                seeded levels vs capped_resources; same state+building seeded by two mods.

Severity is advisory, not a verdict:
  MECHANICAL  no balance judgement (stale delta comment, a base value we never meant to
              change, a vanilla key our copy dropped).
  BALANCE     fixing it moves a gameplay number, or it needs an in-game observation.

Output: tools/data_patch_drift.csv
  severity | kind | mod | file | object | field | vanilla | ours | note

Usage: python anal-patch-drift.py [--since YYYY-MM-DD] [GAME_DIR]
"""
import csv, os, re, sys, glob, collections, datetime

from _refpaths import game_path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # victoria-3-mod
GAME = game_path()
MOD1 = os.path.join(ROOT, "mod1")
OUT = os.path.join(HERE, "data_patch_drift.csv")

# Fields we deliberately author. A diff here is ours; a diff anywhere else is the patch.
OWNED = {"traits", "capped_resources", "resource", "arable_land",
         "arable_resources", "subsistence_building"}
# Fields that describe the map itself. Any diff here is a GAP and never intended.
# subsistence_building is deliberately NOT here: InfraTax authors it, and its delta
# comments already carry the base value, so stage 4 is the right check for it.
STRUCTURAL = {"id", "provinces", "impassable", "prime_land", "city", "port",
              "farm", "mine", "wood", "naval_exit_id"}

rows = []


def add(sev, kind, mod, fil, obj, field, van, ours, note):
    rows.append(dict(severity=sev, kind=kind, mod=mod, file=fil, object=obj,
                     field=field, vanilla=van, ours=ours, note=note))


def read(p):
    try:
        with open(p, encoding="utf-8-sig", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def decomment(t):
    return re.sub(r"#.*", "", t)


def top_blocks(text, with_preamble=False):
    """Top-level `KEY = { ... }` blocks, brace-counted. Returns {key: body}.

    with_preamble also returns the text since the previous block, which is where our
    generated delta comments live (they sit ABOVE the state, not inside it).
    """
    out, t, last = {}, text, 0
    for m in re.finditer(r"^([A-Za-z_0-9]+)\s*=\s*\{", t, re.M):
        i, d = m.end(), 1
        while d and i < len(t):
            c = t[i]
            d += (c == "{") - (c == "}")
            i += 1
        body = t[m.end():i - 1]
        out[m.group(1)] = (t[last:m.start()], body) if with_preamble else body
        last = i
    return out


def named_blocks(text, token):
    """Every `<token> = { ... }` block anywhere, brace-counted. Yields (head, body)."""
    for m in re.finditer(token + r"\s*=\s*\{", text):
        i, d = m.end(), 1
        while d and i < len(text):
            c = text[i]
            d += (c == "{") - (c == "}")
            i += 1
        yield m.group(0), text[m.end():i - 1]


def field(body, key):
    m = re.search(r"\b" + key + r"\s*=\s*(\{[^{}]*\}|\"[^\"]*\"|[^\s{}]+)", decomment(body))
    return " ".join(m.group(1).split()) if m else None


def field_names(body):
    return set(re.findall(r"([a-z_]+)\s*=", decomment(body)))


def cap_map(body):
    inner = field(body, "capped_resources") or ""
    return {a: int(b) for a, b in re.findall(r"(building_[a-z_]+)\s*=\s*(\d+)", inner)}


def token_set(body, key):
    inner = field(body, key) or ""
    return set(re.findall(r'"?([a-z_]*building_[a-z_]+|state_trait_[a-z_0-9]+)"?', inner))


# ---------------------------------------------------------------- stage 1: layers
def stage_layers(since):
    by_day = collections.defaultdict(list)
    for p in glob.glob(os.path.join(GAME, "**", "*.txt"), recursive=True):
        try:
            d = datetime.date.fromtimestamp(os.path.getmtime(p))
        except OSError:
            continue
        by_day[d].append(p)
    layers = sorted(by_day.items(), reverse=True)
    print("patch layers by mtime (newest first):")
    for d, ps in layers[:6]:
        print("   %s  %5d files" % (d, len(ps)))
    if since:
        cut = datetime.date.fromisoformat(since)
        return [p for d, ps in layers if d >= cut for p in ps]
    return [p for d, ps in layers[:1] for p in ps]


# ---------------------------------------------------------------- stage 2: surface
def mod_map_files():
    """{basename: (mod, path)} for every whole-file map_data override we ship."""
    out = {}
    for p in glob.glob(os.path.join(MOD1, "*", "map_data", "state_regions", "*.txt")):
        mod = p.replace("\\", "/").split("/")[-4]
        out[os.path.basename(p)] = (mod, p)
    return out


def stage_surface(layer_files, overrides):
    for p in layer_files:
        b = os.path.basename(p)
        if b in overrides and "state_regions" in p.replace("\\", "/"):
            mod, _ = overrides[b]
            add("BALANCE", "CONFLICT", mod, b, "", "",
                "changed in this patch layer", "whole-file override",
                "the patch edited a file we replace wholesale; nothing of it survives")


# ---------------------------------------------------------------- stage 3 + 4: map_data
def stage_map_data(overrides):
    for b, (mod, ourp) in sorted(overrides.items()):
        vanp = os.path.join(GAME, "map_data", "state_regions", b)
        if not os.path.isfile(vanp):
            add("BALANCE", "GAP", mod, b, "", "", "file absent", "present",
                "we override a vanilla file that no longer exists")
            continue
        van = top_blocks(read(vanp))
        ours_pre = top_blocks(read(ourp), with_preamble=True)
        ours = {k: v[1] for k, v in ours_pre.items()}
        for k in sorted(set(van) - set(ours)):
            add("MECHANICAL", "GAP", mod, b, k, "", "present", "absent",
                "vanilla state missing from our copy; our override deletes it")
        for k in sorted(set(ours) - set(van)):
            add("BALANCE", "GAP", mod, b, k, "", "absent", "present",
                "state in our copy that vanilla no longer defines")

        for k in sorted(set(van) & set(ours)):
            vb, ob = van[k], ours[k]
            for fn in sorted(field_names(vb) - field_names(ob)):
                add("MECHANICAL", "GAP", mod, b, k, fn, "present", "absent",
                    "field vanilla has and our copy lacks")
            for f in sorted(STRUCTURAL):
                a, o = field(vb, f), field(ob, f)
                if a != o and (a is not None or o is not None):
                    add("MECHANICAL", "GAP", mod, b, k, f, a, o,
                        "map structure differs; not a field we author")
            for f in ("traits", "arable_resources"):
                dropped = token_set(vb, f) - token_set(ob, f)
                for x in sorted(dropped):
                    add("BALANCE", "CONFLICT", mod, b, k, f, x, "absent",
                        "vanilla entry dropped by our override")
            va, oa = cap_map(vb), cap_map(ob)
            for key in sorted(set(va) - set(oa)):
                add("BALANCE", "CONFLICT", mod, b, k, "capped_resources:" + key,
                    va[key], "absent", "vanilla cap dropped by our override")

            # stage 4: our own delta comments record the vanilla value at copy time.
            # They sit in the preamble above the state block, not inside it.
            deltas = ours_pre[k][0]
            for f, frm, _to in re.findall(
                    r"(arable_land|subsistence_building)\s+([A-Za-z_0-9]+)->([A-Za-z_0-9]+)", deltas):
                cur = (field(vb, f) or "").strip('"')
                if cur != frm:
                    add("MECHANICAL", "GAP", mod, b, k, f, cur, field(ob, f),
                        "delta comment records a base of %s; vanilla now reads %s" % (frm, cur))
            for bl, frm, _to in re.findall(r"capped:(building_[a-z_]+)\s+(\d+)->(\d+)", deltas):
                cur = va.get(bl)
                if cur is None and frm == "0":
                    continue                     # absent then, absent now
                if str(cur) != frm:
                    add("MECHANICAL", "GAP", mod, b, k, "capped_resources:" + bl, cur,
                        oa.get(bl),
                        "delta comment records a base of %s; vanilla now reads %s" % (frm, cur))


# ---------------------------------------------------------------- stage 5: history
def universes():
    def tops(paths):
        s = set()
        for p in paths:
            s |= set(re.findall(r"^\s*([A-Za-z_0-9]+)\s*=\s*\{", decomment(read(p)), re.M))
        return s

    def both(sub):
        return glob.glob(os.path.join(GAME, sub)) + glob.glob(os.path.join(MOD1, "*", sub))

    u = dict(
        states=tops(both("map_data/state_regions/*.txt")),
        buildings=tops(both("common/buildings/*.txt")),
        pms=tops(both("common/production_methods/*.txt")),
        poptypes=tops(glob.glob(os.path.join(GAME, "common/pop_types/*.txt"))),
        cultures=tops(both("common/cultures/*.txt")),
        religions=tops(glob.glob(os.path.join(GAME, "common/religions/*.txt"))),
        traits=tops(both("common/state_traits/*.txt")),
    )
    prov = set()
    for p in both("map_data/state_regions/*.txt"):
        for _h, bdy in named_blocks(decomment(read(p)), "provinces"):
            prov |= {x.lower() for x in re.findall(r'"?(x[0-9A-Fa-f]{6})"?', bdy)}
    u["provinces"] = prov
    return u


def harvest_buildings(paths):
    """(source, state, building, level) per create_building, brace-accurate."""
    out = []
    for p in sorted(paths):
        t = decomment(read(p))
        if "create_building" not in t:
            continue
        for head, sb in named_blocks(t, r"s:STATE_[A-Z_0-9]+"):
            st = re.search(r"s:(STATE_[A-Z_0-9]+)", head).group(1)
            for _h2, cb in named_blocks(sb, "create_building"):
                b = re.search(r'building\s*=\s*"?(building_[a-z_]+)', cb)
                if not b:
                    continue
                lv = re.search(r"^\s*level\s*=\s*(\d+)", cb, re.M)
                # ownership levels SUM to the building level; never both
                n = int(lv.group(1)) if lv else sum(
                    int(x) for x in re.findall(r"levels\s*=\s*(\d+)", cb))
                out.append((p.replace("\\", "/"), st, b.group(1), n))
    return out


def stage_history(overrides):
    u = universes()
    hist = glob.glob(os.path.join(MOD1, "*", "common", "history", "**", "*.txt"), recursive=True)
    checks = [("STATE", r"\bs:(STATE_[A-Z_0-9]+)", "states"),
              ("PROVINCE", r'"?(x[0-9A-Fa-f]{6})"?', "provinces"),
              ("BUILDING", r'building\s*=\s*"?(building_[a-z_]+)', "buildings"),
              ("PM", r'"(pm_[a-z_0-9]+)"', "pms"),
              ("POPTYPE", r'pop_type\s*=\s*"?([a-z_]+)', "poptypes"),
              ("CULTURE", r'culture\s*=\s*"?([a-z_]+)', "cultures"),
              ("RELIGION", r'religion\s*=\s*"?([a-z_]+)', "religions")]
    for p in hist:
        t, rel = decomment(read(p)), os.path.relpath(p, MOD1).replace("\\", "/")
        mod = rel.split("/")[0]
        for label, pat, key in checks:
            for tok in sorted(set(re.findall(pat, t))):
                probe = tok.lower() if label == "PROVINCE" else tok
                if probe not in u[key]:
                    add("BALANCE", "GAP", mod, rel, tok, label, "not defined", "referenced",
                        "history references a token vanilla no longer defines")

    # live caps: our override where we have one, else vanilla
    live = {}
    for p in glob.glob(os.path.join(GAME, "map_data", "state_regions", "*.txt")):
        live[os.path.basename(p)] = p
    for b, (_mod, p) in overrides.items():
        live[b] = p
    caps = {}
    for p in live.values():
        for k, body in top_blocks(read(p)).items():
            caps[k] = cap_map(body)

    van_b = harvest_buildings(glob.glob(os.path.join(GAME, "common/history/buildings/*.txt")))
    mod_b = harvest_buildings(hist)
    agg = collections.defaultdict(list)
    for r in van_b + mod_b:
        agg[(r[1], r[2])].append(r)
    for (st, bl), rs in sorted(agg.items()):
        cap = caps.get(st, {}).get(bl)
        mine = [r for r in rs if r[0].replace("\\", "/").find("/mod1/") >= 0 or MOD1.replace("\\", "/") in r[0]]
        if cap is None or not mine:
            continue
        total = sum(r[3] for r in rs)
        if total > cap:
            add("BALANCE", "CONFLICT", "", "", st, bl, cap, total,
                "seeded levels (vanilla + mod) exceed the state cap")

    seeded = collections.defaultdict(lambda: collections.defaultdict(int))
    for src, st, bl, n in mod_b:
        seeded[(st, bl)][os.path.relpath(src, MOD1).replace("\\", "/").split("/")[0]] += n
    for (st, bl), mods in sorted(seeded.items()):
        if len(mods) > 1:
            add("BALANCE", "CONFLICT", " + ".join(sorted(mods)), "", st, bl, "",
                "; ".join("%s=%d" % kv for kv in sorted(mods.items())),
                "same state and building seeded by more than one of our mods")


def main():
    args = [a for a in sys.argv[1:]]
    since = None
    if "--since" in args:
        i = args.index("--since")
        since = args[i + 1]
        del args[i:i + 2]
    global GAME
    if args:
        GAME = args[0]
    print("game:", GAME)
    print("mods:", MOD1)
    overrides = mod_map_files()
    print("whole-file map_data overrides:", len(overrides))
    layer = stage_layers(since)
    stage_surface(layer, overrides)
    stage_map_data(overrides)
    stage_history(overrides)

    cols = ["severity", "kind", "mod", "file", "object", "field", "vanilla", "ours", "note"]
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["severity"] != "BALANCE", r["kind"], r["file"], r["object"])):
            w.writerow(r)
    tally = collections.Counter((r["severity"], r["kind"]) for r in rows)
    print("\nfindings -> %s" % OUT)
    for k, n in sorted(tally.items()):
        print("   %-11s %-9s %d" % (k[0], k[1], n))
    print("   TOTAL %d" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
