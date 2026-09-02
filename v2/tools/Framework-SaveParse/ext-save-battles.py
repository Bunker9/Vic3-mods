#!/usr/bin/env python3
"""ext-save-battles.py - SaveParse Set-1 raw extractor (MOD-AGNOSTIC): streams battle_manager and
naval_battle_manager out of a Vic3 save -> save-CURR/raw_battles.csv.

SORT, DO NOT FILTER (DEV-RULES 2026-07-01). EVERY battle block emits at least one row, whether or
not it carries a statistics array, and every per-culture casualty entry emits its own row on top.
A battle with no casualty detail still appears with row_kind=battle so nothing vanishes from the
pool; attribution happens downstream. The first cut of this script emitted a row only on a complete
num_dead/num_wounded/num_demoralized triple and silently dropped 25 of 40 battles - do not
reintroduce that shape.

Battle-level manpower (attacker/defender starting and ending manpower and battalions) is carried on
every row, since that is the save's only dated manpower-loss record: pop and state blocks hold
current values only. Standalone; run-save-parse invokes it with the resolved --save."""
import os
import re
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths

ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")

# battle-level scalars kept verbatim; absent keys stay blank rather than dropping the row
SCALARS = ["type", "war", "front", "province", "status", "start_date", "end_date",
           "attacker_start_battalions", "defender_start_battalions",
           "attacker_ending_battalions", "defender_ending_battalions",
           "attacker_starting_manpower", "defender_starting_manpower",
           "attacker_ending_manpower", "defender_ending_manpower",
           "initial_power_ratio", "num_captured_provinces"]
COLS = (["battle_id", "manager", "row_kind"] + SCALARS +
        ["side", "side_country", "culture", "num_dead", "num_wounded", "num_demoralized"])

_MGR = re.compile(r"^(battle_manager|naval_battle_manager)=\{")
_ID = re.compile(r"^(\d+)=(\{|none)$")
_KV = re.compile(r"^(\w+)=([\w.\-]+)$")


def emit(rows, bid, mgr, sc, kind, side="", country="", culture="", dead="", wnd="", dem=""):
    rows.append([bid, mgr, kind] + [sc.get(k, "") for k in SCALARS] +
                [side, country, culture, dead, wnd, dem])


def main():
    p = argparse.ArgumentParser(description="SaveParse: every battle + per-culture casualties (common, once).")
    p.add_argument("--save", default=None, help="save file (.v3); else resolved from config_game.toml")
    a = p.parse_args()
    save = lib_paths.resolve_save(lib_paths.game_config(), a.save)
    print(f"  ext-battles: scan {save}")

    rows = []
    mgr = None
    depth = 0
    bid = None
    bdepth = 0
    sc = {}
    sides = []          # (side, country) seen in this battle
    culture_rows = []   # (side, country, culture, dead, wounded, demoralized)
    side = None
    side_country = None
    cur_culture = None
    cur = {}
    in_stats = False
    none_seen = 0

    with open(save, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            t = line.strip()

            if mgr is None:
                m = _MGR.match(t)
                if m:
                    mgr, depth = m.group(1), 1
                continue

            depth += line.count("{") - line.count("}")
            if depth <= 0:
                mgr = None
                continue

            if bid is None:
                m = _ID.match(t)
                if m:
                    if m.group(2) == "none":     # placeholder slot, recorded not dropped
                        none_seen += 1
                        emit(rows, m.group(1), mgr, {}, "none_slot")
                        continue
                    bid, bdepth = m.group(1), 1
                    sc, sides, culture_rows = {}, [], []
                    side = side_country = cur_culture = None
                    cur = {}
                    in_stats = False
                continue

            bdepth += line.count("{") - line.count("}")

            if t.startswith("attacker="):
                side, side_country = "attacker", None
            elif t.startswith("defender="):
                side, side_country = "defender", None
            if t.startswith("statistics="):
                in_stats = True
                cur, cur_culture = {}, None

            m = _KV.match(t)
            if m:
                k, v = m.group(1), m.group(2)
                if k in SCALARS:
                    sc.setdefault(k, v)
                elif k == "country" and side and side_country is None:
                    side_country = v
                    sides.append((side, v))
                elif in_stats and k == "culture":
                    cur_culture, cur = v, {}
                elif in_stats and k in ("num_dead", "num_wounded", "num_demoralized"):
                    cur[k] = v
                    if cur_culture is not None and len(cur) == 3:
                        culture_rows.append((side or "", side_country or "", cur_culture,
                                             cur.get("num_dead", ""), cur.get("num_wounded", ""),
                                             cur.get("num_demoralized", "")))
                        cur, cur_culture = {}, None

            if bdepth <= 0:
                # ALWAYS emit the battle itself, then every side, then every culture detail row
                emit(rows, bid, mgr, sc, "battle")
                for s, c in sides:
                    emit(rows, bid, mgr, sc, "side", side=s, country=c)
                for s, c, cu, dd, ww, mm in culture_rows:
                    emit(rows, bid, mgr, sc, "culture", side=s, country=c, culture=cu,
                         dead=dd, wnd=ww, dem=mm)
                bid = None
                in_stats = False

    os.makedirs(ROOT, exist_ok=True)
    path = os.path.join(ROOT, "raw_battles.csv")
    lib_io.write_csv(path, COLS, rows)
    kinds = {}
    for r in rows:
        kinds[r[2]] = kinds.get(r[2], 0) + 1
    print(f"  -> raw_battles.csv: {len(rows)} rows {kinds}")


if __name__ == "__main__":
    main()
