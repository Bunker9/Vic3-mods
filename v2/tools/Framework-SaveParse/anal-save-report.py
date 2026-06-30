#!/usr/bin/env python3
"""anal-save-report.py — SaveParse analyzer: summarise aggr_save_matches.csv into diagnostics.md — deliberate
fingerprints found (value/where), other persisted tokens, and which kw-list tokens did NOT persist (expected
for loc/effect/trigger/decision names). Cohesive analyzer. Ported from save-game-parser/anal_save_report.py."""
import os
import re
import sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config

CFG = lib_config.load_framework_config(HERE, "config_saveparse.toml")
INFIX = CFG["markers"]["fingerprint_infix"]
NONPERSIST = re.compile(r"_sv_|_trigger|_on_action"
                        r"|(_desc|_tooltip|_tt|_effect|_effects|_decision|_yearly|_startup|_check|"
                        r"_values?|_caps?|_levels?|_diag)$")


def main(args):
    d = lib_paths.run_dir("save-CURR", args.mod_name)
    header, rows = lib_io.read_csv(os.path.join(d, CFG["outputs"]["matches"]))
    if header is None:
        sys.exit("anal-save-report: run aggr-save-matches first.")
    ix = {c: i for i, c in enumerate(header)}
    by_term = defaultdict(list)
    for r in rows:
        by_term[r[ix["fp"]]].append(r)
    fps = sorted(t for t in by_term if INFIX in t)
    others = sorted(t for t in by_term if INFIX not in t)
    data = lib_paths.data_dir(args.mod_name, create=False)
    _h, kwrows = lib_io.read_csv(os.path.join(data, "raw_keywords.csv"))
    kws = [(r[1], r[2] if len(r) > 2 else "") for r in (kwrows or [])]
    persisted = set(by_term)
    missing = [(kw, kind) for kw, kind in kws if kw not in persisted]

    def line(term):
        rs = by_term[term]
        kinds = sorted({r[ix["fp_type"]] for r in rs})
        vals = sorted({r[ix["value"]] for r in rs if r[ix["value"]]})
        dates = sorted({r[ix["date"]] for r in rs if r[ix["date"]]})
        secs = sorted({r[ix["section"]] for r in rs})
        extra = []
        if vals:
            extra.append("value=" + ",".join(vals[:4]) + ("..." if len(vals) > 4 else ""))
        if dates:
            extra.append("date=" + ",".join(dates[:3]))
        return (f"- `{term}`  x{len(rs)}  [{'/'.join(kinds)}]  in {','.join(secs[:4])}"
                f"{('  ' + '; '.join(extra)) if extra else ''}  (first L{rs[0][ix['line_no']]})")

    out = [f"# Save-parse diagnostics — {args.mod_name}", ""]
    out.append(f"Persisted occurrences: **{len(rows)}** · distinct tokens: **{len(by_term)}** "
               f"(fingerprints: {len(fps)}, other persisted: {len(others)})")
    out.append("\n## Deliberate fingerprints found (`*_fingerprint_*`)")
    out += [line(t) for t in fps] or ["- _none yet — add fingerprint vars + run a game, then re-scan._"]
    out.append("\n## Other mod tokens that persisted (variables / modifiers)")
    out += [line(t) for t in others] or ["- _none._"]
    out.append("\n## kw-list tokens NOT in the save (expected for non-state names)")
    out.append("These never persist (loc keys, scripted effects/triggers, decision ids, script-values, file "
               "basenames). Absence is normal — only variables / modifiers persist.")
    exp = [kw for kw, _k in missing if NONPERSIST.search(kw)]
    susp = [kw for kw, _k in missing if not NONPERSIST.search(kw)]
    out.append(f"- expected-absent (non-state names): {len(exp)} — " + ", ".join(exp[:18])
               + ("..." if len(exp) > 18 else ""))
    if susp:
        out.append(f"- WARN absent but NOT obviously a non-state name ({len(susp)}): " + ", ".join(susp)
                   + "  <- verify these were supposed to persist (feature may not have fired)")
    md = os.path.join(d, CFG["outputs"]["report"])
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"  -> {md}\n     fingerprints={len(fps)} other-persisted={len(others)} not-in-save={len(missing)}")


if __name__ == "__main__":
    main(lib_args.parse_args("SaveParse: summarise matches into diagnostics.md.", save=True))
