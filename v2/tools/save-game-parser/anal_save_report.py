#!/usr/bin/env python3
r"""anal_save_report.py — stage 2: summarise matched_savefile_loglines.csv into diagnostics.md.

Reads the stage-1 CSV (re-runnable standalone) and writes a per-mod verdict: deliberate fingerprints
found (with value/where), other persisted tokens (variables/modifiers) found, and which kw-list tokens
did NOT persist (expected for loc/effect/trigger/decision names — they are never save state)."""
import re
from collections import defaultdict
import lib_saveparse as L

# A kw that can NEVER be save state: script-values (_sv_), triggers, on-actions, loc keys, effect/decision
# names, file basenames. Mix of substring (code categories) + suffix (loc/name endings) signals.
NONPERSIST = re.compile(r"_sv_|_trigger|_on_action"
                        r"|(_desc|_tooltip|_tt|_effect|_effects|_decision|_yearly|_startup|_check|"
                        r"_values?|_caps?|_levels?|_diag)$")


def main(args):
    header, rows = L.read_csv(L.out_path(args.mod_name, "matched_savefile_loglines.csv"))
    if header is None:
        raise SystemExit("anal_save_report: run aggr_save_matches first.")
    ix = {c: i for i, c in enumerate(header)}

    by_term = defaultdict(list)
    for r in rows:
        by_term[r[ix["fp"]]].append(r)

    fps = sorted(t for t in by_term if L.FP_INFIX in t)
    others = sorted(t for t in by_term if L.FP_INFIX not in t)

    kws = L.load_kw(args.mod_name)
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
            extra.append("value=" + ",".join(vals[:4]) + ("…" if len(vals) > 4 else ""))
        if dates:
            extra.append("date=" + ",".join(dates[:3]))
        return (f"- `{term}`  x{len(rs)}  [{'/'.join(kinds)}]  in {','.join(secs[:4])}"
                f"{('  ' + '; '.join(extra)) if extra else ''}  (first L{rs[0][ix['line_no']]})")

    out = [f"# Save-parse diagnostics — {args.mod_name}", ""]
    out.append(f"Persisted occurrences: **{len(rows)}**  ·  distinct tokens: **{len(by_term)}**  "
               f"(fingerprints: {len(fps)}, other persisted: {len(others)})")
    out.append("")
    out.append("## Deliberate fingerprints found (`*_fingerprint_*`)")
    out += [line(t) for t in fps] or ["- _none yet — add fingerprint vars + run a game, then re-scan._"]
    out.append("")
    out.append("## Other mod tokens that persisted (variables / modifiers)")
    out += [line(t) for t in others] or ["- _none._"]
    out.append("")
    out.append("## kw-list tokens NOT in the save (expected for non-state names)")
    out.append("These never persist (loc keys, scripted effects/triggers, decision ids, script-values, "
               "file basenames). Absence here is normal — only variables / flags / modifiers persist.")
    exp = [kw for kw, _k in missing if NONPERSIST.search(kw)]
    susp = [kw for kw, _k in missing if not NONPERSIST.search(kw)]
    out.append(f"- expected-absent (non-state names): {len(exp)} — " + ", ".join(exp[:18])
               + ("…" if len(exp) > 18 else ""))
    if susp:
        out.append(f"- ⚠ absent but NOT obviously a non-state name ({len(susp)}): " + ", ".join(susp)
                   + "  ← verify these were supposed to persist (feature may not have fired)")
    out.append("")

    md = L.out_path(args.mod_name, "diagnostics.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"  -> {md}")
    print(f"     fingerprints={len(fps)}  other-persisted={len(others)}  not-in-save={len(missing)}")


if __name__ == "__main__":
    main(L.parse_args("Summarise the save-parse matches into diagnostics.md (stage 2)."))
