#!/usr/bin/env python3
"""
MASTER test orchestrator for Vic3 mods — runs IN the testbook worktree.

One command. Runs every per-mod static check in parallel, parses the game logs once,
regenerates the per-mod json + reports + _meta, and rebuilds the recency-ordered INDEX.md.
Then press F5 in the browser.

    python testbook/testkit/run_test.py                 # all mods under mod1/
    python testbook/testkit/run_test.py Top40EcoBoostMod # one mod
    python testbook/testkit/run_test.py --open           # also open the report

Layout it writes (testbook IS the archive now — no separate sync step):
    testbook/<Mod>/static.json   (generated)      testbook/<Mod>/report.html (generated)
    testbook/<Mod>/_meta.txt     (generated)      testbook/<branch>.html     (combined, gitignored)
    testbook/log.json            (generated, gitignored)
    testbook/INDEX.md            (regenerated, recency-ordered)
The human-authored testbook/<Mod>/bdd.md + observe.md + props.toml are READ, never overwritten.
"""
import os, re, sys, json, argparse, subprocess, webbrowser, shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))            # .../testbook/v1/testkit
TB   = os.path.dirname(HERE)                                  # .../testbook/v1  (v1 archive root)
ROOT = os.path.dirname(os.path.dirname(TB))                  # project container (v1 -> testbook -> root)
MOD1 = os.path.join(ROOT, "mod1")
sys.path.insert(0, os.path.join(HERE, "checks"))
import structure, log_triage, standards, conflict, timeline   # noqa: E402
import render_html                                            # noqa: E402


def discover_mods():
    out = []
    for name in sorted(os.listdir(MOD1)):
        md = os.path.join(MOD1, name)
        if os.path.isfile(os.path.join(md, ".metadata", "metadata.json")):
            out.append(name)
    return out


def git_out(*args, default=""):
    try:
        return subprocess.check_output(["git", "-C", MOD1, *args], text=True).strip()
    except Exception:
        return default


def read(p):
    return open(p, encoding="utf-8").read() if os.path.isfile(p) else ""


def bdd_summary(bdd_path):
    """Port of sync-testbook's Get-BddSummary: count PASS/FAIL/NA from the BDD table."""
    if not os.path.isfile(bdd_path):
        return "n/a"
    p = f = na = 0
    for ln in open(bdd_path, encoding="utf-8"):
        if not ln.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 5 or cells[0] == "#" or re.match(r'^[-: ]+$', cells[0]):
            continue
        exp = "Y" if re.match(r'^(Y|YES)$', cells[2], re.I) else ("N" if re.match(r'^(N|NO)$', cells[2], re.I) else "")
        ans = "Y" if re.match(r'^(Y|YES)$', cells[3], re.I) else ("N" if re.match(r'^(N|NO)$', cells[3], re.I) else "")
        if not ans:
            na += 1
        elif ans == exp:
            p += 1
        else:
            f += 1
    return f"{p} PASS / {f} FAIL / {na} NA"


def regen_index():
    """Rebuild INDEX.md from every <Mod>/_meta.txt, newest-tested on top."""
    rows = []
    for name in sorted(os.listdir(TB)):
        d = os.path.join(TB, name)
        meta = os.path.join(d, "_meta.txt")
        if not (os.path.isdir(d) and os.path.isfile(meta)):
            continue
        m = read(meta)
        def g(k):
            mm = re.search(rf'{k}:\s*(.+)', m)
            return mm.group(1).strip() if mm else ""
        rows.append((name, g("tested"), g("branch"), g("commit"), g("bdd")))
    rows.sort(key=lambda r: r[1], reverse=True)
    lines = ["# Testbook - archived test runs", "",
             "Orphan branch (never merged to master). Most-recently-tested mod on top.", "",
             "| Mod | Last tested | Branch | Commit | BDD |", "|---|---|---|---|---|"]
    for name, tested, branch, commit, bdd in rows:
        lines.append(f"| [{name}]({name}/report.html) | {tested} | {branch} | `{commit}` | {bdd} |")
    with open(os.path.join(TB, "INDEX.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument("mods", nargs="*", help="mod folder names under mod1/ (default: all)")
    ap.add_argument("--logs", help="override Vic3 logs dir")
    ap.add_argument("--open", action="store_true", help="open the report in the browser")
    a = ap.parse_args()

    mods = a.mods or discover_mods()
    mod_dirs = [os.path.join(MOD1, m) for m in mods]
    branch = git_out("rev-parse", "--abbrev-ref", "HEAD", default="test")
    commit = git_out("rev-parse", "--short", "HEAD", default="?")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"Testing [{branch} @ {commit}]: {', '.join(mods)}")

    # 1) static checks in parallel -> testbook/<mod>/static.json
    def do_static(md):
        res = structure.run(md)
        outdir = os.path.join(TB, res["mod"])
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "static.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        # advisory authoring-standards pass (green/yellow) — separate stream, NOT a gate
        st = standards.run(md)
        with open(os.path.join(outdir, "standards.json"), "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2)
        res["standards"] = st
        return res
    with ThreadPoolExecutor() as ex:
        statics = list(ex.map(do_static, mod_dirs))
    mods_static = [(s["mod"], s) for s in statics]

    # 2) logs parsed once -> testbook/log.json (gitignored)
    logs_dir = a.logs or log_triage.resolve_logs_dir()
    logdata = log_triage.run(logs_dir, mod_dirs)
    with open(os.path.join(TB, "log.json"), "w", encoding="utf-8") as f:
        json.dump(logdata, f, indent=2)

    # 3) human inputs (read-only) from testbook/<Mod>/
    mods_human = []
    for m in mods:
        td = os.path.join(TB, m)
        mods_human.append((m, read(os.path.join(td, "observe.md")),
                           read(os.path.join(td, "bdd.md"))))

    # 3b) cross-mod conflict scan (Conflicts tab)
    conflictdata = conflict.run(mod_dirs)
    with open(os.path.join(TB, "conflicts.json"), "w", encoding="utf-8") as f:
        json.dump(conflictdata, f, indent=2)
    print(f"Conflicts: {conflictdata['summary']['hard']} hard, "
          f"{conflictdata['summary']['soft']} soft")

    # 3c) per-year / per-country event timeline (Timeline tab)
    timelinedata = timeline.run(logs_dir)
    with open(os.path.join(TB, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(timelinedata, f, indent=2)
    print(f"Timeline: {timelinedata['summary']['wars']} wars, "
          f"{timelinedata['summary']['eco_placements']} eco builds, years {timelinedata['years']}")

    # 4) render the combined report (root, viewable) ...
    root_report = os.path.join(TB, f"{branch.replace('/', '-')}.html")
    build_stamp = render_html.read_build_stamp(logs_dir)
    bs_label = build_stamp[0] or "(not found)"
    print(f"Build stamp: {bs_label!r} (from {build_stamp[1] or 'none'})")
    render_html.render(branch, mods_static, logdata, mods_human, root_report, conflictdata,
                       timelinedata, build_stamp)

    # ... then per tested mod: report.html copy + _meta.txt (was sync-testbook's job)
    for m in mods:
        td = os.path.join(TB, m)
        os.makedirs(td, exist_ok=True)
        shutil.copyfile(root_report, os.path.join(td, "report.html"))
        bdd = bdd_summary(os.path.join(td, "bdd.md"))
        with open(os.path.join(td, "_meta.txt"), "w", encoding="utf-8") as f:
            f.write(f"tested: {stamp}\nbranch: {branch}\ncommit: {commit}\nbdd:    {bdd}\n")

    # 5) rebuild the recency-ordered index
    regen_index()

    sfail = sum(s["summary"]["failed"] for _, s in mods_static)
    syel = sum(len(s.get("standards", {}).get("findings", [])) for _, s in mods_static)
    print(f"  static: {sfail} failed | log: {logdata['summary']['mod_real_errors']} mod errors, "
          f"{logdata['summary']['non_mod_errors']} non-mod")
    print(f"  standards: {syel} advisory finding(s) (green/yellow; see <mod>/standards.json)")
    print(f"  report -> {root_report}")
    print(f"  archived per-mod report.html + _meta.txt; INDEX.md rebuilt")
    if a.open:
        webbrowser.open("file:///" + root_report.replace("\\", "/"))


if __name__ == "__main__":
    run()
