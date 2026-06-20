#!/usr/bin/env python3
"""
Generic static-checks feature.
Runs structure + standards on the mod, writes data_static.json + component.html.
Mod name is auto-derived from the feature folder's filesystem path.
"""
import sys, os

_HERE = os.path.dirname(os.path.abspath(__file__))   # v2/testkit (shared lib + checks, flat)
sys.path.insert(0, _HERE)

import lib_components as fb
import chk_structure as structure, chk_standards as standards


def run(feature_dir, logs_dir=None):
    mod   = fb.mod_name_from_feature_dir(feature_dir)
    mod_dir = os.path.join(fb.MOD1, mod)
    if not os.path.isdir(mod_dir):
        print(f"  [static] SKIP {mod}: mod dir not found")
        return

    st  = structure.run(mod_dir)
    sta = standards.run(mod_dir)

    h = []

    # --- structure table ---
    rows = []
    for f in st["files"]:
        c = f["checks"]
        def cv(k):
            v = c.get(k)
            if not v or v["ok"] is None: return ("-", "muted")
            return ("OK", "ok") if v["ok"] else (v["msg"][:40], "bad")
        rows.append([f["path"], cv("encoding"), cv("braces"), cv("quotes"), cv("folder")])
    meta = st["metadata"]
    meta_cls = "ok" if meta["ok"] else "bad"
    meta_row = [(meta["msg"], meta_cls)]
    h.append(fb.tbl(
        ["File", "Encoding", "Braces", "Quotes", "Folder"],
        [["metadata.json", (meta["msg"][:50], meta_cls), "", "", ""]] + rows
    ))

    # --- standards findings ---
    if sta["findings"]:
        h.append(f"<p class='warn' style='margin:10px 0 4px'>"
                 f"{fb.badge('warn', str(len(sta['findings'])) + ' advisory findings')}</p>")
        rows2 = []
        for f_ in sta["findings"]:
            sev_cls = "bad" if f_["severity"] == "red" else "warn"
            rows2.append([(f_["rule"], sev_cls), f_["object"], f_["file"],
                          str(f_["line"]), f_["msg"][:60]])
        h.append(fb.tbl(["Rule", "Object", "File", "Line", "Message"], rows2))
    else:
        h.append("<p class='ok small'>Standards: all clear.</p>")

    summary = {
        "fail":      st["summary"]["failed"],
        "pass":      st["summary"]["passed"],
        "checks":    st["summary"]["checks"],
        "standards": len(sta["findings"]),
    }
    fb.write_data(feature_dir, "data_static.json", {"structure": st, "standards": sta})
    fb.write_component(feature_dir, mod, "static", "static", "Static Checks", 0,
                       "\n".join(h), summary=summary)
    print(f"  [static] {mod}: {summary['fail']} fail, {summary['standards']} advisory")


if __name__ == "__main__":
    import sys as _sys
    fd = _sys.argv[1] if len(_sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    run(fd)
