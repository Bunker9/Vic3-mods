#!/usr/bin/env python3
"""ext-save-goods.py — SaveParse Set-1 raw extractor (T103, MOD-AGNOSTIC, parse-once): walk the save's
market_manager and dump every price_trend channel -> COMMON save-CURR/raw_market_goods.csv, one row per
(market x goods): market_id ('world' or the database id), RAW numeric goods_id (the goods_ids catalog names
it — UAT SP-02 raw/enrich split), sample date, sample count, current (last), min and max price. Countries
link to markets via raw_countries.market. Uses its OWN block tokenizer because market channels open in the
save's COMPACT form `}1={` (close+open on one line), which the generic breadcrumb walker treats as a bare
closer (only channel 0 was captured before — fixed 2026-07-02). Standalone; run-save-parse invokes it."""
import os
import re
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths, lib_config, lib_parse

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
G = CFG["goods"]
ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")
_TOK = re.compile(r"\}|([\w:.\-]+)=\{")   # a closer, OR a named opener (handles `}1={` close+open lines)


def main():
    p = argparse.ArgumentParser(description="SaveParse Set1: market goods prices (common, once).")
    p.add_argument("--save", default=None, help="save file (.v3); else resolved from config_game.toml")
    a = p.parse_args()
    save = lib_paths.resolve_save(lib_paths.game_config(), a.save)
    print(f"  ext-goods: scan {save} ({G['manager']})")
    chans, stack, started = {}, [], False
    for raw in lib_parse.iter_save_lines(save):
        line = raw.strip()
        if not started:
            if line.startswith(G["manager"] + "={"):
                started, stack = True, [G["manager"]]
            continue
        if len(stack) >= 3 and stack[-2] == G["channels_key"] and G["trend_key"] in stack:
            gid = stack[-1]                                   # inside price_trend.channels.<goods_id>
            market = "world" if G["world_key"] in stack else \
                (stack[stack.index("database") + 1] if "database" in stack else "?")
            entry = chans.setdefault((market, gid), {"date": "", "values": []})
            if line.startswith("date="):
                entry["date"] = line.split("=", 1)[1]
            elif line.startswith("values={"):
                entry["values"] = [float(v) for v in line[len("values={"):].rstrip("} ").split()]
        for m in _TOK.finditer(line):
            if m.group(0) == "}":
                if stack:
                    stack.pop()
            else:
                stack.append(m.group(1))
        if started and not stack:
            break                                             # left market_manager — stop the stream early
    rows = []
    for (market, gid), e in chans.items():
        v = e["values"]
        if v:
            rows.append([market, gid, e["date"], len(v), v[-1], min(v), max(v)])
    lib_io.write_csv(os.path.join(ROOT, CFG["outputs"]["market_goods"]),
                     ["market_id", "goods_id", "sample_date", "samples", "price_current",
                      "price_min", "price_max"], rows, sort=True)
    n_mkts = len({m for m, _g in chans})
    print(f"  -> {CFG['outputs']['market_goods']}: {len(rows)} (market x goods) rows across {n_mkts} markets")


if __name__ == "__main__":
    main()
