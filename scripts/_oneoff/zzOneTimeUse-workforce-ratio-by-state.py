# zzOneTimeUse 2026-08-17 - per-state workforce share of population.
# Reads Framework-SaveParse OUTPUT only (save-CURR/), never the .v3 or vanilla game files.
# Run Framework-SaveParse/run-save-parse.py first. Finding written up in
# testbook/v2/tools/Framework-common/scratch/2026-08-17_workforce_ratio_recheck.md
import csv, collections, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
R = os.path.join(ROOT, "testbook", "v2", "tools", "Game-Victoria3", "save-CURR")
THRESHOLD = 0.20


def load():
    wf, dep = collections.Counter(), collections.Counter()
    with open(os.path.join(R, "raw_pops.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            loc = r["location"]
            if loc:
                wf[loc] += float(r["workforce"] or 0)
                dep[loc] += float(r["dependents"] or 0)
    with open(os.path.join(R, "aggr_employment.csv"), encoding="utf-8") as f:
        emp = {r["state_id"]: r for r in csv.DictReader(f)}
    rows = []
    for sid, w in wf.items():
        pop = w + dep[sid]
        if pop < 1:
            continue
        e = emp.get(sid, {})
        rows.append((w / pop, pop, w, e.get("owner_tag", ""), e.get("state_region", ""), sid))
    return sorted(rows)


def main():
    rows = load()
    under = [r for r in rows if r[0] < THRESHOLD]
    print("states with pops: %d ; under %.0f%%: %d" % (len(rows), THRESHOLD * 100, len(under)))
    for r in under:
        print("%6.2f%%  pop=%10s  wf=%9s  %-4s  %-30s st=%s"
              % (r[0] * 100, format(int(r[1]), ","), format(int(r[2]), ","), r[3], r[4], r[5]))
    print("median %.2f%%  min %.2f%%  max %.2f%%"
          % (statistics.median([x[0] for x in rows]) * 100, rows[0][0] * 100, rows[-1][0] * 100))
    for lo, hi in ((0, .15), (.15, .20), (.20, .25), (.25, .30), (.30, 1)):
        print("  %4.0f%% to %4.0f%%: %3d states" % (lo * 100, hi * 100, len([r for r in rows if lo <= r[0] < hi])))
    for tag in ("GBR",):
        g = [r for r in rows if r[3] == tag]
        if g:
            print("%s: %d states, min %.2f%% (%s), median %.2f%%, max %.2f%%"
                  % (tag, len(g), g[0][0] * 100, g[0][4],
                     statistics.median([x[0] for x in g]) * 100, g[-1][0] * 100))


if __name__ == "__main__":
    main()
