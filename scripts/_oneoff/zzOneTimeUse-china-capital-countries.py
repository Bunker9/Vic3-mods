# zzOneTimeUse 2026-08-17 - countries whose CAPITAL state sits in China.
# Sizes the exploded-China population for the ExpMktAccessMod famine decision.
# Reads Framework-SaveParse OUTPUT only (save-CURR/), never the .v3 or vanilla game files.
# State lists copied from vanilla common/strategic_regions/east_asia_strategic_regions.txt
# (region_south_china :21, region_north_china :28) and common/geographic_regions/
# 06_old_strategic_regions.txt:457 (geographic_region_manchuria_old, Korea entries dropped).
import csv, collections, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
R = os.path.join(ROOT, "testbook", "v2", "tools", "Game-Victoria3", "save-CURR")

SOUTH = """STATE_GUIZHOU STATE_CHONGQING STATE_SICHUAN STATE_SOUTHERN_ANHUI STATE_SHAOZHOU
STATE_GUANGDONG STATE_FUJIAN STATE_FORMOSA STATE_GUANGXI STATE_ZHEJIANG STATE_SUZHOU
STATE_NANJING STATE_HUNAN STATE_JIANGXI STATE_YUNNAN STATE_EASTERN_HUBEI STATE_WESTERN_HUBEI""".split()
NORTH = """STATE_SHANDONG STATE_BEIJING STATE_ZHILI STATE_HENAN STATE_NORTHERN_ANHUI STATE_SHANXI
STATE_JIANGSU STATE_ULIASTAI STATE_URGA STATE_HINGGAN STATE_ALXA STATE_NINGXIA STATE_GANSU
STATE_XIAN""".split()
MANCH = """STATE_SOUTHERN_MANCHURIA STATE_NORTHERN_MANCHURIA STATE_SHENGJING
STATE_OUTER_MANCHURIA STATE_AMUR""".split()
CHINA = {}
for group, states in (("south", SOUTH), ("north", NORTH), ("manchuria", MANCH)):
    CHINA.update({s: group for s in states})


def read(name):
    with open(os.path.join(R, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    # raw_states.region is ALREADY the template name (STATE_MINSK), not a state_region id.
    st = {r["id"]: r for r in read("raw_states.csv")}
    co = {r["id"]: r for r in read("raw_countries.csv")}
    pop = collections.Counter()
    for r in read("raw_pops.csv"):
        if r["location"]:
            pop[r["location"]] += float(r["workforce"] or 0) + float(r["dependents"] or 0)
    owned = collections.defaultdict(list)
    for sid, s in st.items():
        owned[s.get("country", "")].append(sid)

    rows = []
    for cid, c in co.items():
        cap = st.get(c.get("capital", ""), {})
        tmpl = cap.get("region", "")
        if tmpl in CHINA:
            # tag lives in the `definition` column; `tag` is blank in this save.
            rows.append((c["definition"], c["country_type"], c["market"], tmpl, CHINA[tmpl],
                         len(owned[cid]), sum(pop[s] for s in owned[cid])))
    print("%-5s %-14s %-7s %-26s %-6s %s" % ("tag", "type", "market", "capital region", "states", "pop"))
    for r in sorted(rows, key=lambda x: -x[6]):
        print("%-5s %-14s %-7s %-26s %-6d %s"
              % (r[0], r[1], r[2], "%s (%s)" % (r[3], r[4]), r[5], format(int(r[6]), ",")))
    print("china-capital countries: %d ; combined pop %s"
          % (len(rows), format(int(sum(r[6] for r in rows)), ",")))


if __name__ == "__main__":
    main()
