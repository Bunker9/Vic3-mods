#!/usr/bin/env python3
"""
ext_errors.py — GLOBAL "Errors" view: render the grouped game error.log (parse_errors) as a v2
panel. Rendered ONCE (not per mod) and wired into run_v2 as a framework tab, because cpp errors are
game-global (they reference vanilla files, not mod markers).

Each error group is a collapsible block: count + relevance pill + a raw log snippet + a note on
whether/how our mod code could be the cause. The relevance classes are deliberately NOT auto-
dismissive — `vanilla?` means "vanilla file, but a mod could be triggering it; review".
"""
import sys, os

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import lib_components as fb
import parse_errors

# relevance class -> (pill css, short label)
PILL = {
    "mod-data":   ("bad",  "mod-data"),
    "mod-script": ("bad",  "mod-script"),
    "vanilla?":   ("warn", "vanilla? (maybe mod)"),
    "vanilla":    ("grey", "vanilla"),
    "uncertain":  ("warn", "uncertain"),
}


def run(out_dir, logs_dir=None):
    data = parse_errors.run(logs_dir)
    groups = data["groups"]
    total = data["total"]

    # roll up counts per relevance class for the header
    by_kind = {}
    for g in groups:
        by_kind[g["kind"]] = by_kind.get(g["kind"], 0) + g["count"]

    h = []
    if not logs_dir or not data.get("logs_dir"):
        h.append("<p class='muted small'>No logs dir resolved.</p>")
    h.append("<p>"
             + fb.badge("bad" if total else "ok", f"{total} cpp errors")
             + " " + fb.badge("grey", f"{len(groups)} groups")
             + "</p>")
    # class summary line
    order = ["mod-data", "mod-script", "vanilla?", "uncertain", "vanilla"]
    cls_badges = [fb.badge(PILL[k][0], f"{PILL[k][1]}: {by_kind[k]}")
                  for k in order if by_kind.get(k)]
    if cls_badges:
        h.append("<p>" + " ".join(cls_badges) + "</p>")
    h.append("<p class='small muted'>Relevance is a hint, not a verdict: <b>vanilla?</b> = a vanilla "
             "file threw it, but mod code may be triggering it (review the snippet before ruling our "
             "code out).</p>")

    # one collapsible per group, most frequent first; mod-linked ones auto-open
    for g in groups:
        cls, lbl = PILL.get(g["kind"], ("grey", g["kind"]))
        ref = f" <code>{fb.esc(g['ref_file'])}</code>" if g["ref_file"] else ""
        opn = " open" if g["kind"] in ("mod-data", "mod-script") else ""
        h.append(f"<details{opn}><summary>{fb.badge('warn', str(g['count']))} "
                 f"{fb.badge(cls, lbl)}{ref} "
                 f"<span class='small'>{fb.esc(g['signature'][:90])}</span></summary>")
        h.append("<pre class='note'>" + fb.esc("\n".join(g["snippet"])) + "</pre>")
        if g["note"]:
            h.append(f"<p class='small'>{fb.esc(g['note'])}</p>")
        h.append("</details>")

    summary = {"total": total, "groups": len(groups), "by_kind": by_kind}
    fb.write_data(out_dir, "data_errors.json", data)
    fb.write_component(out_dir, "(global)", "errors", "errors", "Errors", 0,
                       "\n".join(h), summary=summary)
    print(f"  [errors] global: {total} cpp errors in {len(groups)} groups "
          + " ".join(f"{k}={v}" for k, v in by_kind.items()))


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(_HERE), "_global", "errors")
    run(out)
