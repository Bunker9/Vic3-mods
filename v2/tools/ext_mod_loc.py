#!/usr/bin/env python3
r"""
ext_mod_loc.py — stage 3b of the triage job. Extract the mod's defined localization keys.

Parses localization .yml files for `key:0 "..."` definitions so 'missing/unused localization' log
errors can be matched separately from code tokens.

Writes testbook/v2/tools/<MOD_NAME>/list_loc.csv  (loc_id, key, file_id, line_no).

Standardized args (see lib_triage): arg1=MOD_NAME, arg2=MOD_PATH (required here).
Usage: python ext_mod_loc.py NoUSChickenMod "C:\...\NoUSChickenMod"
"""
import sys, re
import lib_triage as L

LOC_RX = re.compile(r'^\s*(?P<key>[A-Za-z0-9_.]+):\d+\s+"')


def main(args):
    if not args.mod_path:
        sys.exit("ext_mod_loc: MOD_PATH (arg2) required to read the mod source.")
    files = L.walk_mod_files(args.mod_path)
    _h, frows = L.read_csv(L.out_path(args.mod_name, "list_files.csv"))
    relmap = {r[1]: int(r[0]) for r in frows} if frows else {}

    rows = []
    loc_id = 0
    for i, (rel, ap, fn) in enumerate(files, 1):
        if not fn.lower().endswith((".yml", ".yaml")):
            continue
        file_id = relmap.get(rel, i)
        for ln, line in enumerate(L.read_text_lines(ap), 1):
            m = LOC_RX.match(line)
            if not m:
                continue
            loc_id += 1
            rows.append([loc_id, m.group("key"), file_id, ln])

    out = L.out_path(args.mod_name, "list_loc.csv")
    L.write_csv(out, ["loc_id", "key", "file_id", "line_no"], rows)
    print(f"  [3b] list_loc.csv: {len(rows)} loc keys -> {out}")
    return out


if __name__ == "__main__":
    main(L.parse_args("Extract mod localization keys (stage 3b)."))
