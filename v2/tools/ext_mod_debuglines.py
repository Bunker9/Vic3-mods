#!/usr/bin/env python3
r"""
ext_mod_debuglines.py — stage 3 of the triage job. Extract the mod's debug_log markers.

Greps mod source for `debug_log = "..."` (or a bareword loc key) and records the payload text, the
owning file_id (FK into list_files.csv), and the 1-based line number. This canonical marker set is
what stage 5 cross-references against the logs for fired-vs-unfired analysis.

Writes testbook/v2/tools/<MOD_NAME>/list_debug_lines.csv  (dbg_id, text, file_id, line_no).

Standardized args (see lib_triage): arg1=MOD_NAME, arg2=MOD_PATH (required here).
Usage: python ext_mod_debuglines.py NoUSChickenMod "C:\...\NoUSChickenMod"
"""
import sys, re
import lib_triage as L

DEBUG_RX = re.compile(r"""^\s*debug_log\s*=\s*("(?P<q>[^"]*)"|(?P<b>\S+))""")


def main(args):
    if not args.mod_path:
        sys.exit("ext_mod_debuglines: MOD_PATH (arg2) required to read the mod source.")
    files = L.walk_mod_files(args.mod_path)
    # rel_path -> file_id from list_files.csv (built in stage 1); fall back to walk order.
    _h, frows = L.read_csv(L.out_path(args.mod_name, "list_files.csv"))
    relmap = {r[1]: int(r[0]) for r in frows} if frows else {}

    rows = []
    dbg_id = 0
    for i, (rel, ap, _fn) in enumerate(files, 1):
        file_id = relmap.get(rel, i)
        for ln, line in enumerate(L.read_text_lines(ap), 1):
            m = DEBUG_RX.match(line)
            if not m:
                continue
            text = m.group("q") if m.group("q") is not None else m.group("b")
            dbg_id += 1
            rows.append([dbg_id, text, file_id, ln])

    out = L.out_path(args.mod_name, "list_debug_lines.csv")
    L.write_csv(out, ["dbg_id", "text", "file_id", "line_no"], rows)
    print(f"  [3] list_debug_lines.csv: {len(rows)} markers -> {out}")
    return out


if __name__ == "__main__":
    main(L.parse_args("Extract mod debug_log markers (stage 3)."))
