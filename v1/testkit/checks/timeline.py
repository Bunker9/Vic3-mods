#!/usr/bin/env python3
r"""
timeline.py — per-YEAR, per-COUNTRY event timeline from debug.log (for the Timeline tab).

debug.log has no game date on mod lines, BUT vanilla logs chronological date lines like
"January 2, 1836: Election ...". We scan top-to-bottom, carry the most-recent YEAR forward,
and stamp every mod event with it. Names come from `debug_log_scopes` dumps (Root / saved
scopes), never from interpolated debug_log (which spams loc errors).

Tracked:
  DIPLO (MyDiploPlayMod):
    - wars started     : "mdp_try_next_war WAR DECLARED" block -> mdp_attacker -> mdp_tgt
    - claims given     : MDP_CLAIM markers   (1 per claimed state)   -> attacker
    - homeland changes : MDP_HOMELAND markers                        -> attacker
    - pops given       : MDP_POP markers                             -> attacker
  ECO (Top40EcoBoostMod):
    - buildings placed : "ECO_PLACED <type>" markers, attributed to the most-recent
                         "Root: Country X" + building-name header (debug_log = $B$).

FORWARD CONTRACT (so this needs no revisit when the mod changes land):
  - When champ/support move to a yearly Jan-01 pulse (T48), each placement still logs the
    building header + "ECO_PLACED <type>" + a Root scope dump -> it bins into the right year
    automatically (the carried date advances).
  - New diplo events just need a fixed ASCII marker + (for actor/target) debug_log_scopes.

Usage: python timeline.py [--logs <dir>] [--json out.json]
"""
import os, re, json, argparse, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import resolve_logs_dir  # noqa: E402

DATE_RX  = re.compile(r"\b[A-Z][a-z]+ \d{1,2}, (\d{4}):")
ATK_RX   = re.compile(r"mdp_attacker:\s*Country\s+(.+?)\s*\(")
TGT_RX   = re.compile(r"mdp_tgt:\s*Country\s+(.+?)\s*\(")
ROOT_RX  = re.compile(r"Root:\s*Country\s+(.+?)\s*\(")
THIS_RX  = re.compile(r"This:\s*State\s+(.+?)\s*\(")          # state scope for eco
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
    cur_atk = cur_tgt = cur_root = cur_bldg = cur_state = None
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for ln in f:
            d = DATE_RX.search(ln)
            if d:
                year = int(d.group(1))
            m = ATK_RX.search(ln)
            if m: cur_atk = m.group(1)
            m = TGT_RX.search(ln)
            if m: cur_tgt = m.group(1)
            m = ROOT_RX.search(ln)
            if m: cur_root = m.group(1)
            m = THIS_RX.search(ln)
            if m: cur_state = m.group(1)

            if "WAR DECLARED" in ln and cur_atk and cur_tgt:
                wars.append({"year": year, "attacker": cur_atk, "target": cur_tgt})
            elif "MDP_CLAIM" in ln:
                # cur_atk is set for war-chain claims; cur_root is set for history-file claims
                actor = cur_atk or cur_root
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

            # eco: every build logs uniformly now -> a `debug_log = $B$` building-name header,
            # then `eco_hit_<type>` (-> "ECO_PLACED champ|support|flavour"), then a scope dump
            # (Root=country, This=state). Exclude markers so they aren't read as building names.
            if ("eco_effects.txt" in ln and not any(k in ln for k in
                    ("ECO_", "FORTESTLOG", "ECONOSLOT", "eco_have"))):
                h = ECO_HDR.search(ln)
                if h:
                    cur_bldg = h.group(1)
            if "ECO_PLACED" in ln:                       # champ / support / flavour build
                typ = ln.strip().split()[-1]
                eco[(year, cur_root, cur_bldg, cur_state, typ)] += 1

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
    for w in res["wars"][:10]:
        print(f"  {w['year']}  WAR  {w['attacker']} -> {w['target']}")
    for r in res["eco"][:8]:
        print(f"  {r['year']}  ECO  {r['country']}  {r['building']} [{r['type']}] @{r.get('state','?')} x{r['count']}")
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), indent=2)
