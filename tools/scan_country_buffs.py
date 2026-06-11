#!/usr/bin/env python3
r"""
Scan the Vic3 game files for the BUFFS countries can get over a game, to inform champ/support
selection (e.g. which good a nation gets late-game output buffs on). Re-run when the game
version changes.

Two structured sources (the richest for goods/economy buffs):

  1) COMPANIES (common/company_types/) -> tools/buffs_companies.csv
     company | file | eligibility (culture/tag/region from potential+possible) |
     buildings (goods it covers) | prosperity_modifier buffs | prestige_goods
     -> "what good-buff can a country unlock by chartering a company, and how to qualify".

  2) NAMED MODIFIERS (common/static_modifiers/) + every add_modifier grant of them
     -> tools/buffs_modifier_grants.csv
     modifier | buffs (token=value;...) | granted_by (folder->type) | duration | file | countries
     -> the user's "start from modifiers, see where they're called, note duration / file / who".
     Country attribution is a HEURISTIC: tag from a history/countries filename, else c:TAG tokens
     found near the add_modifier; "(conditional)" when none -> verify by opening the file.

NOT covered (v2): inline modifiers embedded in journal_entries / laws / technologies / building
PMs (those aren't named, so they need a different per-source parser).

Usage:  python tools/scan_country_buffs.py
"""
import os, re, csv, glob

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game"
OUT = os.path.dirname(os.path.abspath(__file__))
TAGRE = re.compile(r"\bc:([A-Z0-9_]{2,})")
NUMRE = re.compile(r"^\s*([a-z][a-z0-9_]+)\s*=\s*(-?[0-9.]+)\s*(?:#.*)?$")
SKIP_TOK = {"icon", "background", "level", "value", "add", "days", "months", "years", "chance"}


def read(p):
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def strip_comments(text):
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in text.splitlines())


def top_blocks(text):
    """Yield (name, body) for each `name = { ... }` defined at brace-depth 0."""
    text = strip_comments(text)
    name, buf, depth = None, [], 0
    for ln in text.splitlines():
        if depth == 0:
            m = re.match(r"^(\w[\w.]*)\s*=\s*\{", ln)
            if m:
                name, buf = m.group(1), [ln]
                depth = ln.count("{") - ln.count("}")
                if depth <= 0:
                    yield name, "\n".join(buf)
                    name = None
            continue
        buf.append(ln)
        depth += ln.count("{") - ln.count("}")
        if depth <= 0:
            yield name, "\n".join(buf)
            name, depth = None, 0


def sub_block(body, key):
    """Return the text inside `key = { ... }` within body (first occurrence), brace-matched."""
    m = re.search(r"\b" + key + r"\s*=\s*\{", body)
    if not m:
        return ""
    i = m.end() - 1
    depth, start = 0, i
    while i < len(body):
        depth += (body[i] == "{") - (body[i] == "}")
        i += 1
        if depth == 0:
            return body[start + 1:i - 1]
    return body[start + 1:]


def tokens(block):
    """token=value pairs (skip icons/structural)."""
    out = []
    for ln in block.splitlines():
        m = NUMRE.match(ln)
        if m and m.group(1) not in SKIP_TOK:
            out.append(f"{m.group(1)}={m.group(2)}")
    return out


def country_names():
    f = os.path.join(OUT, "country_stats.csv")
    names = {}
    if os.path.isfile(f):
        for row in csv.DictReader(open(f, encoding="utf-8-sig")):
            if row.get("tag") and row.get("country"):
                names[row["tag"]] = row["country"]
    return names


NAMES = country_names()
def tagstr(tag):
    return f"c:{tag}({NAMES[tag]})" if tag in NAMES else f"c:{tag}"


# ---------------------------------------------------------------- 1) COMPANIES
def scan_companies():
    rows = []
    for path in glob.glob(os.path.join(GAME, "common", "company_types", "*.txt")):
        fname = os.path.basename(path)
        for name, body in top_blocks(read(path)):
            elig = sub_block(body, "potential") + "\n" + sub_block(body, "possible")
            cults = sorted(set(re.findall(r"cu:(\w+)", elig)))
            tags = sorted(set(re.findall(r"c:([A-Z0-9_]{2,})", elig)))
            regions = sorted(set(re.findall(r"s:(STATE_\w+)", elig)))
            blds = re.findall(r"building_\w+", sub_block(body, "building_types") + " " +
                              sub_block(body, "extension_building_types"))
            buffs = tokens(sub_block(body, "prosperity_modifier"))
            prestige = re.findall(r"prestige_good_\w+", sub_block(body, "possible_prestige_goods"))
            eligibility = "; ".join(filter(None, [
                "culture:" + ",".join(cults) if cults else "",
                "tag:" + ",".join(tags) if tags else "",
                "region:" + ",".join(regions[:6]) if regions else ""]))
            rows.append({
                "company": name, "file": fname, "eligibility": eligibility or "(broad)",
                "buildings": " ".join(sorted(set(blds))),
                "prosperity_buffs": " ; ".join(buffs),
                "prestige_goods": " ".join(prestige),
            })
    return rows


# ----------------------------------------------------- 2) NAMED MODIFIER GRANTS
def load_named_modifiers():
    mods = {}
    for path in glob.glob(os.path.join(GAME, "common", "static_modifiers", "*.txt")):
        for name, body in top_blocks(read(path)):
            mods[name] = tokens(body)
    return mods


FOLDER_TYPE = [
    ("history/countries", "history(country)"), ("history/", "history"),
    ("journal_entries", "journal"), ("decisions", "decision"),
    ("company_types", "company"), ("on_actions", "on_action"),
    ("scripted_effects", "scripted_effect"), ("laws", "law"),
    ("interest_groups", "interest_group"), ("amendments", "amendment"),
    ("/events/", "event"),
]


def src_type(relpath):
    for frag, label in FOLDER_TYPE:
        if frag in relpath:
            return label
    return "other"


def scan_grants(mods):
    """Find add_modifier grants of known named modifiers across common/ + events/."""
    rows = []
    files = (glob.glob(os.path.join(GAME, "common", "**", "*.txt"), recursive=True) +
             glob.glob(os.path.join(GAME, "events", "**", "*.txt"), recursive=True))
    grant_re = re.compile(r"add_modifier\s*=\s*(?:\{\s*name\s*=\s*(\w+)([^}]*)\}|(\w+))")
    for path in files:
        rel = path.replace(GAME, "").replace("\\", "/")
        if "static_modifiers" in rel:
            continue
        text = strip_comments(read(path))
        lines = text.splitlines()
        fname_tag = None
        mfn = re.match(r"(\w{2,3})\s*-", os.path.basename(path))  # "pan - punjab.txt"
        if "history/countries" in rel and mfn:
            fname_tag = mfn.group(1).upper()
        for i, ln in enumerate(lines):
            for m in grant_re.finditer(ln):
                mod = m.group(1) or m.group(3)
                if mod not in mods:
                    continue
                dur = ""
                dm = re.search(r"(months|years|days)\s*=\s*(\d+)", m.group(2) or "")
                if dm:
                    dur = f"{dm.group(2)} {dm.group(1)}"
                # country attribution: filename tag, else c:TAG within ~25 lines above
                if fname_tag:
                    who = tagstr(fname_tag)
                else:
                    ctx = "\n".join(lines[max(0, i - 25):i + 2])
                    tags = sorted(set(TAGRE.findall(ctx)))
                    who = ", ".join(tagstr(t) for t in tags) if tags else "(conditional)"
                rows.append({
                    "modifier": mod, "buffs": " ; ".join(mods[mod]) or "(non-numeric)",
                    "granted_by": src_type(rel), "duration": dur or "permanent",
                    "countries": who, "file": rel.lstrip("/"),
                })
    return rows


def write_csv(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    if not os.path.isdir(GAME):
        raise SystemExit(f"Game dir not found: {GAME}")
    comp = scan_companies()
    write_csv(os.path.join(OUT, "buffs_companies.csv"), comp,
              ["company", "file", "eligibility", "buildings", "prosperity_buffs",
               "prestige_goods"])
    print(f"buffs_companies.csv          {len(comp)} companies")

    mods = load_named_modifiers()
    grants = scan_grants(mods)
    grants.sort(key=lambda r: (r["modifier"], r["file"]))
    write_csv(os.path.join(OUT, "buffs_modifier_grants.csv"), grants,
              ["modifier", "buffs", "granted_by", "duration", "countries", "file"])
    print(f"buffs_modifier_grants.csv    {len(grants)} grants of {len(mods)} named modifiers")
