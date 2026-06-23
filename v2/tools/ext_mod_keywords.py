#!/usr/bin/env python3
r"""
ext_mod_keywords.py — stage 2 of the triage job. Extract the mod's own keywords/tokens.

The keyword prefix (e.g. 'nous') is auto-derived from the dominant '<short>_' identifier prefix in
the mod source, overridable with --prefix. Every unique identifier containing the prefix as a '_'-
delimited segment is recorded — this catches both leading-prefix tokens ('nous_md_done') AND wrapped
ones the engine logs by full name ('modifier_nous_warbonds', 'ai_strategy_nous_total_war'). 'kind' is
best-effort: 'def' when the token is a block definition LHS ('tok = {'), else 'ref'.

Writes testbook/v2/tools/<MOD_NAME>/list_kw.csv  (kw_id, kw, kind).

Standardized args (see lib_triage): arg1=MOD_NAME, arg2=MOD_PATH (required here).
Usage: python ext_mod_keywords.py NoUSChickenMod "C:\...\NoUSChickenMod" [--prefix nous]
"""
import sys, re
import lib_triage as L


def main(args):
    if not args.mod_path:
        sys.exit("ext_mod_keywords: MOD_PATH (arg2) required to read the mod source.")
    files = L.walk_mod_files(args.mod_path)
    prefix = args.prefix or L.detect_prefix(files)
    if not prefix:
        sys.exit("ext_mod_keywords: could not derive a keyword prefix; pass --prefix.")

    # Any multi-segment identifier that includes the prefix as a whole '_'-delimited segment.
    ident_rx = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")
    seen = {}   # kw -> kind ('def' wins over 'ref')
    for _rel, ap, _fn in files:
        for line in L.read_text_lines(ap):
            for kw in ident_rx.findall(line):
                if prefix not in kw.split("_"):
                    continue
                is_def = bool(re.search(re.escape(kw) + r"\s*=\s*\{", line))
                if kw not in seen or is_def:
                    seen[kw] = "def" if is_def else seen.get(kw, "ref")

    rows = [[i, kw, kind] for i, (kw, kind) in enumerate(sorted(seen.items()), 1)]
    out = L.out_path(args.mod_name, "list_kw.csv")
    L.write_csv(out, ["kw_id", "kw", "kind"], rows)
    print(f"  [2] list_kw.csv: {len(rows)} keywords (prefix '{prefix}_') -> {out}")
    return out


if __name__ == "__main__":
    main(L.parse_args("Extract mod keywords/tokens (stage 2)."))
