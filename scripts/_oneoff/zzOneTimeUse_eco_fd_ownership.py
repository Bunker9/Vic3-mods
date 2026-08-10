"""ONE-OFF: hand the EXTRACTION and MANUFACTURING buildings in Top40EcoBoostMod's existing
history to financial districts sitting in the owner's CAPITAL. Agriculture is left alone.

User-approved 2026-08-09; this is the one sanctioned exception to no-scripted-mod-file-edits,
because the 753 target blocks are textually identical and cannot be Edit-targeted one at a time.

    add_ownership = { country  = { country = "c:AUS" levels = 1 } }
 -> add_ownership = { building = { type = "building_financial_district"
                                   country = "c:AUS" levels = 1 region = "STATE_VIENNA" } }

`levels` is carried across untouched: ownership levels SUM to the building's level, so changing
that number would silently change the building. Both block forms in these files are handled
(expanded across lines in zz_eco_starters/whale_gold, one-line in zz_eco_flavour).

Run with --apply to write; default is a dry run. Every edit lands in
hk-config/tools/data_eco_fd_ownership_edits.csv for review and re-checking.
"""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HK = os.path.dirname(os.path.dirname(HERE))                  # hk-config
ROOT = os.path.dirname(HK)                                   # victoria-3-mod
sys.path.insert(0, os.path.join(HK, "tools"))
from _refpaths import game_path                              # noqa: E402

BUILD_DIR = os.path.join(ROOT, "mod1", "Top40EcoBoostMod", "common", "history", "buildings")
FILES = ["zz_eco_starters.txt", "zz_eco_flavour.txt", "zz_eco_whale_gold.txt",
         "zz_eco_starters_eastafrica.txt"]
OUT_CSV = os.path.join(HK, "tools", "data_eco_fd_ownership_edits.csv")

# The nine types present in these files that are extraction or manufacturing.
TARGETS = {"building_logging_camp", "building_coal_mine", "building_iron_mine",
           "building_lead_mine", "building_sulfur_mine", "building_gold_mine",
           "building_whaling_station", "building_fishing_wharf", "building_tooling_workshop"}


def capitals():
    """{tag: STATE_X} from vanilla common/country_definitions."""
    caps, d = {}, os.path.join(game_path(), "common", "country_definitions")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8-sig", errors="replace") as f:
            text = "\n".join(ln.split("#", 1)[0] for ln in f.read().splitlines())
        for tag, body in re.findall(r"^(\w{3})\s*=\s*\{(.*?)^\}", text, re.S | re.M):
            m = re.search(r"capital\s*=\s*(STATE_\w+)", body)
            if m:
                caps[tag] = m.group(1)
    return caps


BLD = re.compile(r'building\s*=\s*"?(building_\w+)"?')


def blocks(text, keyword):
    """Yield (start, end) of every `<keyword> = { ... }` block, brace-counted.

    A regex cannot do this: the non-greedy form stops at the first inner closing brace, which
    silently skipped every expanded add_ownership block on the first run of this script.
    """
    for m in re.finditer(keyword + r"\s*=\s*\{", text):
        depth, i = 1, m.end()
        while depth and i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        yield m.start(), i
# country-ownership block, either form; captures indent, tag and levels
OWN = re.compile(r'([ \t]*)add_ownership\s*=\s*\{\s*country\s*=\s*\{\s*'
                 r'country\s*=\s*"?(c:\w+)"?\s*levels\s*=\s*(\d+)\s*\}\s*\}')


def convert(text, fname, caps, edits):
    """Rewrite every targeted country-ownership block in one file's text."""
    out, pos = [], 0
    for sm in re.finditer(r"\ts:(STATE_\w+)\s*=\s*\{", text):
        state = sm.group(1)
        end = text.find("\n\ts:", sm.end())
        end = len(text) if end == -1 else end
        seg = text[sm.start():end]
        new_seg = seg
        for cb_start, cb_end in reversed(list(blocks(seg, "create_building"))):
            body = seg[cb_start:cb_end]
            bm = BLD.search(body)
            if not bm or bm.group(1) not in TARGETS or "financial_district" in body:
                continue
            om = OWN.search(body)
            if not om:
                continue
            indent, ctag, levels = om.group(1), om.group(2), om.group(3)
            tag = ctag.split(":")[1]
            region = caps.get(tag)
            if not region:
                print(f"  SKIP no capital for {tag} ({state} {bm.group(1)})")
                continue
            one_line = "\n" not in om.group(0)
            if one_line:
                repl = (f'{indent}add_ownership = {{ building = {{ '
                        f'type = "building_financial_district" country = "{ctag}" '
                        f'levels = {levels} region = "{region}" }} }}')
            else:
                i = indent
                repl = (f'{i}add_ownership = {{\n'
                        f'{i}\tbuilding = {{\n'
                        f'{i}\t\ttype = "building_financial_district"\n'
                        f'{i}\t\tcountry = "{ctag}"\n'
                        f'{i}\t\tlevels = {levels}\n'
                        f'{i}\t\tregion = "{region}"\n'
                        f'{i}\t}}\n'
                        f'{i}}}')
            new_body = body.replace(om.group(0), repl, 1)
            new_seg = new_seg.replace(body, new_body, 1)
            edits.append({"file": fname, "state": state, "tag": tag,
                          "building": bm.group(1), "levels": levels,
                          "old_form": "one_line" if one_line else "expanded",
                          "fd_region": region})
        out.append(text[pos:sm.start()] + new_seg)
        pos = end
    out.append(text[pos:])
    return "".join(out)


NEW_FILES = ["zz_eco_champ.txt", "zz_eco_support.txt"]


def fix_regions(apply, caps):
    """Repoint every FD ownership `region` in the two new files at the OWNER's capital.

    The champ file was authored with capitals already; the support file was written earlier with
    the local state, so this is what corrects those 180 lines.
    """
    total = 0
    for fn in NEW_FILES:
        path = os.path.join(BUILD_DIR, fn)
        text = open(path, encoding="utf-8-sig", errors="replace").read()
        new, n = text, 0
        for sm in re.finditer(r"\ts:(STATE_\w+) = \{", text):
            end = text.find("\n\ts:", sm.end())
            end = len(text) if end == -1 else end
            seg = text[sm.start():end]
            new_seg = seg
            for rm in re.finditer(r"region_state:(\w+) = \{", seg):
                tag = rm.group(1)
                want = caps.get(tag)
                if not want:
                    continue
                rs_end = seg.find("region_state:", rm.end())
                rs_end = len(seg) if rs_end == -1 else rs_end
                body = seg[rm.end():rs_end]
                fixed = re.sub(r'(type = "building_financial_district"[^\n]*?region = ")STATE_\w+(")',
                               lambda m: m.group(1) + want + m.group(2), body)
                if fixed != body:
                    n += fixed.count(want) - body.count(want)
                    new_seg = new_seg.replace(body, fixed, 1)
            if new_seg != seg:
                new = new.replace(seg, new_seg, 1)
        print(f"  {fn:22s} {n:4d} FD regions -> owner capital")
        total += n
        if apply and n:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(new)
    return total


def main():
    apply = "--apply" in sys.argv
    caps, edits = capitals(), []
    if "--fix-regions" in sys.argv:
        fix_regions(apply, caps)
        return
    for fn in FILES:
        path = os.path.join(BUILD_DIR, fn)
        raw = open(path, encoding="utf-8-sig", errors="replace").read()
        before = len(edits)
        new = convert(raw, fn, caps, edits)
        n = len(edits) - before
        # invariants: nothing but the ownership blocks may move
        assert new.count("create_building") == raw.count("create_building"), fn
        assert new.count("{") - new.count("}") == raw.count("{") - raw.count("}"), fn
        print(f"  {fn:34s} {n:4d} blocks -> financial district")
        if apply and n:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(new)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "state", "tag", "building", "levels",
                                          "old_form", "fd_region"])
        w.writeheader()
        w.writerows(edits)
    print(f"{'APPLIED' if apply else 'DRY RUN'}  {len(edits)} edits  ->  {OUT_CSV}")
    if not apply:
        print("  re-run with --apply to write the files")


if __name__ == "__main__":
    main()
