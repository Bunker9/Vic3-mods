#!/usr/bin/env python3
"""ext-save-stateall.py - SaveParse Set-1 raw extractor (MOD-AGNOSTIC): EVERYTHING in a Vic3 save
that belongs to one state, from EVERY manager, with EVERY field kept verbatim.

SORT, DO NOT FILTER (DEV-RULES 2026-07-01), taken literally:
  * no manager is skipped - the walk covers the whole file, not a chosen list of blocks
  * no field is skipped - there is no configured field list, every key=value in a matching record
    is emitted, nested blocks included, arrays kept whole as one value
  * records that merely reference the state are kept too, tagged by WHY they matched
Deciding what matters happens AFTER this dump, against this dump.

Two passes over the file:
  1. index every top-level `<manager>.database.<id>` record that belongs to the state - matched on
     any of `state=<id>`, `location=<id>`, `region=<id>`, `home_hq=<id>`, `capital=<id>`, or being
     the `states.database.<id>` record itself - and record which key matched.
  2. dump every field of every indexed record.

Outputs (save-CURR/):
  raw_state<ID>_all.csv    pop_id-agnostic: record_id, manager, match_reason, path, key, value, line_no
  raw_state<ID>_index.csv  one row per matching record: record_id, manager, match_reason, line_no, n_fields

Args follow the shared contract: --save resolves like every other SaveParse stage.
Usage: python ext-save-stateall.py --state 430 [--save FILE]"""
import os
import re
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_io, lib_paths

ROOT = os.path.join(lib_paths.GAME_ROOT, "save-CURR")
LINK_KEYS = ("state", "location", "region", "home_hq", "capital", "state_region", "province_state")

_TOP = re.compile(r"^([\w:.\-]+)=\{")
_ID = re.compile(r"^(-?\d+)=\{$")
_OPEN = re.compile(r"^([\w]+)=\{$")
_KV = re.compile(r"^([\w]+)=(.*)$")


def walk(save, on_record):
    """Stream the save, calling on_record(manager, rec_id, lines) for every
    <manager>.database.<id> record. lines = list of (path, key, value, line_no)."""
    mgr = None
    mgr_depth = 0
    in_db = False
    db_depth = 0
    rid = None
    rdepth = 0
    stack = []
    buf = []
    with open(save, "r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            t = line.strip()
            opens = line.count("{")
            closes = line.count("}")

            if mgr is None:
                m = _TOP.match(t)
                if m and opens > closes:
                    mgr, mgr_depth = m.group(1), 1
                continue

            if rid is None:
                if not in_db:
                    if t == "database={":
                        in_db, db_depth = True, 1
                    else:
                        mgr_depth += opens - closes
                        if mgr_depth <= 0:
                            mgr = None
                    continue
                m = _ID.match(t)
                if m:
                    rid, rdepth, stack, buf = m.group(1), 1, [], []
                    continue
                db_depth += opens - closes
                if db_depth <= 0:
                    in_db = False
                    mgr_depth += 0
                    mgr = None
                continue

            before = rdepth
            rdepth += opens - closes

            m = _KV.match(t)
            if m:
                k, v = m.group(1), m.group(2).rstrip()
                buf.append((".".join(stack), k, v.rstrip("{").strip(), i))

            o = _OPEN.match(t)
            if o and opens > closes:
                stack.append(o.group(1))
            elif stack and rdepth < before:
                for _ in range(before - rdepth):
                    if stack:
                        stack.pop()

            if rdepth <= 0:
                on_record(mgr, rid, buf)
                rid = None


def main():
    p = argparse.ArgumentParser(description="SaveParse: every record of one state, every field, no filter.")
    p.add_argument("--state", required=True, help="state id, e.g. 430 for Wales")
    p.add_argument("--save", default=None, help="save file (.v3); else resolved from config_game.toml")
    a = p.parse_args()
    save = lib_paths.resolve_save(lib_paths.game_config(), a.save)
    sid = a.state
    print(f"  ext-stateall: scan {save} state={sid}")

    rows = []
    index = []
    seen_mgr = {}
    scanned = [0]

    def handle(mgr, rid, buf):
        scanned[0] += 1
        seen_mgr[mgr] = seen_mgr.get(mgr, 0) + 1
        reasons = []
        if mgr == "states" and rid == sid:
            reasons.append("is_the_state")
        for path, k, v, ln in buf:
            if v == sid and k in LINK_KEYS:
                reasons.append(f"{k}={sid}" + (f"@{path}" if path else ""))
        if not reasons:
            return
        reason = "|".join(sorted(set(reasons)))
        first_line = buf[0][3] if buf else -1
        index.append([rid, mgr, reason, first_line, len(buf)])
        for path, k, v, ln in buf:
            rows.append([rid, mgr, reason, path, k, v, ln])

    walk(save, handle)

    os.makedirs(ROOT, exist_ok=True)
    lib_io.write_csv(os.path.join(ROOT, f"raw_state{sid}_all.csv"),
                     ["record_id", "manager", "match_reason", "path", "key", "value", "line_no"], rows)
    lib_io.write_csv(os.path.join(ROOT, f"raw_state{sid}_index.csv"),
                     ["record_id", "manager", "match_reason", "line_no", "n_fields"], index)
    per = {}
    for r in index:
        per[r[1]] = per.get(r[1], 0) + 1
    print(f"  scanned {scanned[0]} records across {len(seen_mgr)} managers")
    print(f"  -> raw_state{sid}_index.csv: {len(index)} matching records {per}")
    print(f"  -> raw_state{sid}_all.csv:   {len(rows)} field rows")


if __name__ == "__main__":
    main()
