#!/usr/bin/env python3
"""anal-goods-ids.py — testbook lookup generator (ONCE-ONLY, hk-config side): vanilla goods -> the
goods_ids literal CSV the debug framework consumes. Reads <game_files_path>/common/goods/*.txt (path from
hk-config/config/refpaths.json — per-machine, gitignored) and emits goods_ids.example.csv BESIDE THIS SCRIPT:
  goods_id,goods_name,base_price   (id = definition ORDER across the sorted files; name = Title Cased key;
  base_price = the good's `cost`).
The save keys market price channels by this numeric id (validated on TEST_ME.v3: 41=Tea / 43=Sugar match a
state's trade.goods{41,43} + traded_goods={tea sugar}).

WORKFLOW (user-directed 2026-07-02): generators for framework literals live HERE, never in the framework
folders (they read base game files and run once per game patch, not per debug run). After a game patch adds
goods (or the prestige-goods DLC), re-run this and MANUALLY copy/curate the rows into
testbook/v2/tools/Framework-SaveParse/goods_ids.example.csv (the user may drop non-market goods, e.g.
services/transportation/electricity/gold, which have no price channel in the save).

Run: python anal-goods-ids.py   (no args; self-locating)"""
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REFPATHS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "config", "refpaths.json")
_TOPKEY = re.compile(r"^([A-Za-z_]\w*)\s*=\s*\{")   # column-0 definition opener
_COST = re.compile(r"^\s*cost\s*=\s*(\d+)")


def main():
    with open(REFPATHS, encoding="utf-8") as f:
        game = json.load(f)["game_files_path"]
    gdir = os.path.join(game, "common", "goods")
    rows, key, cost = [], None, ""
    for fn in sorted(f for f in os.listdir(gdir) if f.endswith(".txt")):
        with open(os.path.join(gdir, fn), encoding="utf-8-sig") as f:
            for line in f:
                m = _TOPKEY.match(line)
                if m:
                    if key is not None:
                        rows.append([len(rows), key.replace("_", " ").title(), cost])
                    key, cost = m.group(1), ""
                elif key is not None and not cost:
                    c = _COST.match(line)
                    if c:
                        cost = c.group(1)
    if key is not None:
        rows.append([len(rows), key.replace("_", " ").title(), cost])
    out = os.path.join(HERE, "goods_ids.example.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["goods_id", "goods_name", "base_price"])
        w.writerows(rows)
    print(f"-> {out}: {len(rows)} goods (id = definition order from {gdir})")
    print("   copy/curate into testbook/v2/tools/Framework-SaveParse/goods_ids.example.csv")


if __name__ == "__main__":
    main()
