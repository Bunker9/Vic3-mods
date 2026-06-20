#!/usr/bin/env python3
r"""
timeline.py — per-YEAR, per-COUNTRY event timeline from debug.log (for the Timeline tab).

PORTED into v2 (self-contained) on 2026-06-18 from testkit/checks/timeline.py, WITH the
eco-STATE fix (v2-harden item e). v1 keeps its own copy; v2 owns + hardens this one.

debug.log has no game date on mod lines, BUT vanilla logs chronological date lines like
"January 2, 1836: Election ...". We scan top-to-bottom, carry the most-recent YEAR forward,
and stamp every mod event with it. Names come from `debug_log_scopes` dumps (Root / saved
scopes), never from interpolated debug_log (which spams loc errors).

--- ECO-STATE FIX (2026-06-18) -------------------------------------------------------------
The mod ALREADY logs the placement state — `debug_log_scopes = yes` dumps it. The dump format
is NOT "This: State X"; the engine prints the This-scope as a leading line:
    [hh:mm:ss][jomini_effect_impl.cpp:2501]: State Piemonte (xA9397D)
    Root: Country Italy (63)
Two bugs made every eco row land with state=None in v1:
  1) the old regex looked for "This:\s*State" which never appears  -> STATE_RX fixed below.
  2) the "ECO_PLACED <type>" marker is logged BEFORE its own scope dump, so binning at
     marker-time used the previous iteration's scope -> we now DEFER: each marker is parked
     in `pending_eco` and bound to the state(This)+country(Root) of the NEXT scope dump.
This needs NO mod change (the data was always in the log) and is verifiable against the
existing debug.log, not a future game run.

Tracked:
  DIPLO (MyDiploPlayMod): wars (WAR DECLARED), claims (MDP_CLAIM), homelands (MDP_HOMELAND),
    pops (MDP_POP, legacy).
  ECO (Top40EcoBoostMod): buildings placed ("ECO_PLACED <type>"), attributed to the building
    header (debug_log = $B$) + the following scope dump (This=state, Root=country).

Usage: python timeline.py [--logs <dir>] [--json out.json]
"""
import os, re, json, argparse, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_paths import resolve_logs_dir  # noqa: E402

DATE_RX  = re.compile(r"\b[A-Z][a-z]+ \d{1,2}, (\d{4}):")
ATK_RX   = re.compile(r"mdp_attacker:\s*Country\s+(.+?)\s*\(")
TGT_RX   = re.compile(r"mdp_tgt:\s*Country\s+(.+?)\s*\(")
ROOT_RX  = re.compile(r"Root:\s*Country\s+(.+?)\s*\(")
# This-scope when it is a State: the engine prints it as a leading scope-dump line, e.g.
#   [..][jomini_effect_impl.cpp:2501]: State Piemonte (xA9397D)
STATE_RX = re.compile(r"\]:\s*State\s+(.+?)\s*\(")
ECO_HDR  = re.compile(r"eco_effects\.txt:\d+:\s*(.+?)\s*$")   # building-name header ($B$)


def run(logs_dir):
    path = os.path.join(logs_dir, "debug.log") if logs_dir else None
    wars, eco = [], defaultdict(int)
    counts = defaultdict(lambda: {"claims": 0, "homelands": 0, "pops": 0})  # (year,country)->counts
    if not path or not os.path.isfile(path):
        return _empty()

    # init to the Vic3 campaign start: game-start events (eco seeding via on_game_started) log
    # BEFORE the first vanilla "Month Day, 1836:" line, so they'd otherwise be year=None.
    year = 1836
    cur_atk = cur_tgt = cur_root = cur_bldg = None
    dump_state = None          # state captured from the in-progress scope dump (This line)
    pending_eco = []           # eco markers awaiting their scope dump: [{year, building, type}]
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for ln in f:
            d = DATE_RX.search(ln)
            if d:
                year = int(d.group(1))
            m = ATK_RX.search(ln)
            if m: cur_atk = m.group(1)
            m = TGT_RX.search(ln)
            if m: cur_tgt = m.group(1)

            # eco building-name header ($B$): set cur_bldg. Exclude marker/own lines so they
            # aren't mistaken for a building name.
            if ("eco_effects.txt" in ln and not any(k in ln for k in
                    ("ECO_", "FORTESTLOG", "ECONOSLOT", "eco_have"))):
                h = ECO_HDR.search(ln)
                if h:
                    cur_bldg = h.group(1)

            # eco placement marker -> PARK it; bound to the next scope dump (state+country).
            if "ECO_PLACED" in ln:
                typ = ln.strip().split()[-1]            # champ / support / flavour
                pending_eco.append({"year": year, "building": cur_bldg, "type": typ})

            # scope dump, This-line when it is a State -> remember for the pending markers.
            ms = STATE_RX.search(ln)
            if ms:
                dump_state = ms.group(1)

            # scope dump, Root-line (Country) -> completes a dump. Set cur_root (for diplo
            # history claims) AND flush any parked eco markers to THIS dump's state+country.
            mr = ROOT_RX.search(ln)
            if mr:
                cur_root = mr.group(1)
                if pending_eco:
                    for p in pending_eco:
                        eco[(p["year"], cur_root, p["building"], dump_state, p["type"])] += 1
                    pending_eco = []
                dump_state = None

            # diplo markers (one line each; never coincide with a scope line)
            if "WAR DECLARED" in ln and cur_atk and cur_tgt:
                wars.append({"year": year, "attacker": cur_atk, "target": cur_tgt})
            elif "MDP_CLAIM" in ln:
                actor = cur_atk or cur_root   # war-chain claims vs history-file claims
                if actor:
                    counts[(year, actor)]["claims"] += 1
            elif "MDP_HOMELAND" in ln:
                actor = cur_atk or cur_root
                if actor:
                    counts[(year, actor)]["homelands"] += 1
            elif "MDP_POP" in ln:
                actor = cur_atk or cur_root
                if actor:
                    counts[(year, actor)]["pops"] += 1

    diplo_counts = [{"year": y, "country": c, **v} for (y, c), v in sorted(
        counts.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1] or ""))]
    eco_rows = [{"year": y, "country": c, "building": b, "state": s, "type": t, "count": n}
                for (y, c, b, s, t), n in sorted(eco.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1] or ""))]
    countries = sorted({w["attacker"] for w in wars} | {w["target"] for w in wars}
                       | {r["country"] for r in diplo_counts if r["country"]}
                       | {r["country"] for r in eco_rows if r["country"]})
    years = sorted({w["year"] for w in wars if w["year"]} |
                   {r["year"] for r in eco_rows if r["year"]} |
                   {r["year"] for r in diplo_counts if r["year"]})
    return {"years": years, "countries": countries, "wars": wars,
            "diplo_counts": diplo_counts, "eco": eco_rows,
            "summary": {"wars": len(wars), "eco_placements": sum(r["count"] for r in eco_rows),
                        "years": years}}


def _empty():
    return {"years": [], "countries": [], "wars": [], "diplo_counts": [], "eco": [],
            "summary": {"wars": 0, "eco_placements": 0, "years": []}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = run(a.logs or resolve_logs_dir())
    print(f"years={res['years']}  countries={len(res['countries'])}  "
          f"wars={res['summary']['wars']}  eco_placements={res['summary']['eco_placements']}")
    placed_with_state = sum(r["count"] for r in res["eco"] if r.get("state") not in (None, "?"))
    print(f"eco rows={len(res['eco'])}  placements with a real state={placed_with_state}")
    for w in res["wars"][:10]:
        print(f"  {w['year']}  WAR  {w['attacker']} -> {w['target']}")
    for r in res["eco"][:8]:
        print(f"  {r['year']}  ECO  {r['country']}  {r['building']} [{r['type']}] @{r.get('state','?')} x{r['count']}")
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), indent=2)
