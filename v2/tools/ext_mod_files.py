#!/usr/bin/env python3
r"""
ext_mod_files.py — stage 1 of the triage job. Extract the mod's source filenames.

Writes testbook/v2/tools/<MOD_NAME>/list_files.csv  (file_id, rel_path, basename).
basename is the join key against the game logs (logs cite e.g. 'nous_decisions.txt').

Standardized args (see lib_triage): arg1=MOD_NAME, arg2=MOD_PATH (required here to read source).
Usage: python ext_mod_files.py NoUSChickenMod "C:\...\NoUSChickenMod"
"""
import sys
import lib_triage as L


def main(args):
    if not args.mod_path:
        sys.exit("ext_mod_files: MOD_PATH (arg2) required to read the mod source.")
    files = L.walk_mod_files(args.mod_path)
    rows = [[i, rel, base] for i, (rel, _ap, base) in enumerate(files, 1)]
    out = L.out_path(args.mod_name, "list_files.csv")
    L.write_csv(out, ["file_id", "rel_path", "basename"], rows)
    print(f"  [1] list_files.csv: {len(rows)} files -> {out}")
    return out


if __name__ == "__main__":
    main(L.parse_args("Extract mod source filenames (stage 1)."))
