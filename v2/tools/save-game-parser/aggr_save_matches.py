#!/usr/bin/env python3
r"""aggr_save_matches.py — stage 1: scan the save once, emit matched_savefile_loglines.csv.

Join keys = the mod's kw list (tools/<MOD>/list_kw.csv) PLUS a generic <abbr>_fingerprint_* regex
(so brand-new fingerprint markers are caught without rebuilding any list). One CSV row per occurrence
of a mod token that actually PERSISTED into the save.

Columns: mod, fp, fp_type, save_token, section, doc_path, value, vtype, date, line_no, sample
  fp        - the token found persisting in the save
  fp_type   - variable (Vic3 'flags' are variables) / modifier / global_variable / other
  save_token- the raw save key it appeared under (flag / modifier / variable / ...)
  doc_path  - dotted breadcrumb of enclosing named blocks (quick way to navigate to it)
  value     - stored value for a variable (raw 'identity'/'value'); date for a modifier's start_date
  line_no   - 1-based line number in the (decompressed) save file
"""
import re
import lib_saveparse as L

HEADER = ["mod", "fp", "fp_type", "save_token", "section", "doc_path",
          "value", "vtype", "date", "line_no", "sample"]


def _decode(value, vtype):
    """Vic3 stores a numeric 'value' variable as fixed-point ×100000 (calibrated: JIANGXI cap 1008 ->
    stored 100800000). Decode to the human value; booleans/other pass through."""
    if vtype == "value" and re.fullmatch(r"-?\d+", value or ""):
        d = int(value) / 100000
        return str(int(d)) if d == int(d) else f"{d:.5f}".rstrip("0").rstrip(".")
    return value


def main(args):
    kws = L.load_kw(args.mod_name)
    abbr = L.mod_abbr(kws, args.prefix)
    literal = {kw for kw, _kind in kws}
    fp_re = re.compile(re.escape(abbr) + r"_fingerprint_[A-Za-z0-9_]+") if abbr else None

    save = L.resolve_save(args.save)
    print(f"  scan: {save}")
    print(f"  keys: {len(literal)} kw + /{abbr}_fingerprint_*/")
    matches = L.scan(save, literal, fp_re)

    rows = [[args.mod_name, m["term"], m["fp_type"], m["save_token"], m["section"],
             m["doc_path"], _decode(m["value"], m["vtype"]), m["vtype"], m["date"], m["line_no"], m["sample"]]
            for m in matches]
    rows.sort(key=lambda r: (r[2], r[1], r[9]))
    outp = L.out_path(args.mod_name, "matched_savefile_loglines.csv")
    L.write_csv(outp, HEADER, rows)
    print(f"  -> {outp}  ({len(rows)} persisted occurrences)")
    return matches


if __name__ == "__main__":
    main(L.parse_args("Scan a save for a mod's persisted tokens + fingerprints (stage 1)."))
