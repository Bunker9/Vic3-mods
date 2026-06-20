#!/usr/bin/env python3
"""
Generic log-errors feature.
Parses error.log + debug.log for this mod, writes data_log.json + component.html.
Mod name is auto-derived from the feature folder's filesystem path.
"""
import sys, os

_HERE = os.path.dirname(os.path.abspath(__file__))   # v2/testkit (shared lib + checks, flat)
sys.path.insert(0, _HERE)

import lib_components as fb
import parse_log as log_triage


def run(feature_dir, logs_dir=None):
    mod     = fb.mod_name_from_feature_dir(feature_dir)
    mod_dir = os.path.join(fb.MOD1, mod)
    if not os.path.isdir(mod_dir):
        print(f"  [log] SKIP {mod}: mod dir not found")
        return

    logs = logs_dir or log_triage.resolve_logs_dir()
    data = log_triage.run(logs, [mod_dir])
    mod_data = data["mods"].get(mod, {"errors": [], "census": [], "tables": [], "error_groups": []})

    h = []
    real  = [e for e in mod_data["errors"] if not e["benign"]]
    benign = [e for e in mod_data["errors"] if e["benign"]]
    groups = mod_data.get("error_groups", [])
    emitted = mod_data.get("emitted", 0)

    # health badges (smoking-gun): did this mod log at all, and how many were errors?
    # emitted == 0 is flagged red — the mod may not be running.
    h.append("<p>"
             + fb.badge("grey" if emitted else "bad", f"{emitted} log lines emitted")
             + " "
             + fb.badge("ok" if not real else "bad", f"{len(real)} errors")
             + "</p>")

    if real:
        h.append(f"<p class='bad'>{fb.badge('bad', str(len(real)) + ' real errors')} "
                 f"<span class='small'>in {len(groups)} files</span></p>")
        for g in groups:
            h.append(f"<details><summary><code>{fb.esc(g['file'])}</code> "
                     f"{fb.badge('warn', str(g['count']))}</summary>")
            for t in g["entries"]:
                h.append(f"<pre class='note'>{fb.esc(t)}</pre>")
            h.append("</details>")
    else:
        h.append("<p class='ok small'>No real errors for this mod.</p>")

    if benign:
        h.append(f"<details><summary class='small'>{len(benign)} benign note(s)</summary>")
        for e in benign:
            h.append(f"<pre class='note'>{fb.esc(e['text'])}</pre>")
        h.append("</details>")

    if mod_data["census"]:
        rows = []
        for r in mod_data["census"]:
            ok_cls = "ok" if r["ok"] else "bad"
            rows.append([r.get("country", "?"), r["building"], r.get("type", "?"),
                         str(r.get("have", 0)), str(r.get("need", "?")),
                         str(r["placed"]), str(r.get("expected", "?")),
                         ("OK" if r["ok"] else "NO", ok_cls)])
        h.append("<h4 style='margin:10px 0 4px'>Census</h4>")
        h.append(fb.tbl(["Country", "Building", "Type", "Have", "Need", "Placed", "Cap", "OK"],
                        rows, cfilter="0"))

    for t in mod_data.get("tables", []):
        h.append(f"<h4 style='margin:10px 0 4px'>{fb.esc(t['title'])}</h4>")
        if t["rows"]:
            h.append(fb.tbl(t["columns"], t["rows"]))
        else:
            h.append("<p class='muted small'>no rows logged</p>")

    summary = {
        "errors": len(real),
        "benign": len(benign),
        "census": len(mod_data["census"]),
        "emitted": emitted,
    }
    fb.write_data(feature_dir, "data_log.json", data)
    fb.write_component(feature_dir, mod, "log", "log", "Log Errors", 0,
                       "\n".join(h), summary=summary)
    print(f"  [log] {mod}: {summary['emitted']} emitted, {summary['errors']} errors, "
          f"{summary['benign']} benign")


if __name__ == "__main__":
    import sys as _sys
    fd = _sys.argv[1] if len(_sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    run(fd)
