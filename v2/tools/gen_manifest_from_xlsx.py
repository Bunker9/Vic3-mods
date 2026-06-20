#!/usr/bin/env python3
r"""
GENERATOR — emits v2/manifest.json from hk-config/data/testbook_status.xlsx (sheet `vic3`).

The xlsx is the SINGLE SOURCE OF TRUTH for the feature taxonomy (decision 2026-06-18). This
script reads its IDENTITY (mod, feature, id) + WHERE-TO-DISPLAY (tab) + STATUS columns and emits
the build manifest run_v2.py consumes. Do NOT hand-edit manifest.json — edit the xlsx and re-run:

    python testbook/v2/tools/gen_manifest_from_xlsx.py

"feature" is a PROTECTED WORD: the per-mod `features` list below holds REAL mod mechanics (xlsx
IDENTITY ids like ECO-CHAMP). The mod-wide views (static / log) are NOT features -> `modwide`.

--- tab normalization (the one heuristic; review here) -------------------------------------
The xlsx `tab/visual` cell is human free-text. We split on '+' and '/' and map each part to a
canonical tab id by keyword (first match wins, priority order below). A feature may land on
several tabs (e.g. "Census ptab + Timeline" -> [census, timeline]).
"""
import os, sys, json, re

HERE = os.path.dirname(os.path.abspath(__file__))                 # .../testbook/v2/tools
V2   = os.path.dirname(HERE)                                      # .../testbook/v2
ROOT = os.path.dirname(os.path.dirname(V2))                       # container (v2->testbook->root)
XLSX = os.path.join(ROOT, "hk-config", "data", "testbook_status.xlsx")

# canonical tabs (id -> label), in display order
TABS = [
    ("static",   "Static Checks"),
    ("log",      "Log"),
    ("census",   "Census / State"),
    ("modifier", "Modifiers"),
    ("timeline", "Timeline"),
    ("diplo",    "Diplomacy"),
    ("config",   "Config"),
    ("bdd",      "BDD"),
]
TAB_IDS = {t for t, _ in TABS}

# xlsx short mod name -> v2/mod1 folder name
MOD_FOLDER = {
    "versiontest":   "versiontestMod",
    "EcoBoost":      "Top40EcoBoostMod",
    "MyDiploPlay":   "MyDiploPlayMod",
    "ExpFight":      "ExpFightMod",
    "ExpMkt":        "ExpMktAccessMod",
    "InfraTax":      "InfraTaxMod",
    "BetterPopPromo":"BetterPopPromoMod",
}

# keyword -> canonical tab, scanned in priority order within each free-text part
_KW = [
    ("static",   "static"), ("standards", "static"), ("encoding", "static"),
    ("diplo",    "diplo"),
    ("config",   "config"),
    ("modifier", "modifier"),
    ("pop",      "census"), ("census", "census"), ("state", "census"),
    ("timeline", "timeline"), ("year", "timeline"),
    ("log",      "log"), ("assert", "log"), ("compare", "log"),
    ("bdd",      "bdd"),
]


def norm_tabs(cell):
    """Free-text WHERE cell -> ordered list of canonical tab ids (de-duped)."""
    if not cell:
        return []
    out = []
    for part in re.split(r"[+/]", str(cell)):
        low = part.lower()
        for kw, tab in _KW:           # first keyword match wins for this part
            if kw in low:
                if tab not in out:
                    out.append(tab)
                break
    return out


def col_index(header_row):
    idx = {}
    for i, c in enumerate(header_row):
        if not c:
            continue
        c = str(c).lower()
        for key in ("mod", "feature", "id", "debug markers", "tab", "status"):
            if key in c and key not in idx:
                idx[key] = i
    return idx


def feature_impl(mod_folder, fid):
    """True if v2/<Mod>/<ID>/ has an extract.py (an implemented feature)."""
    return os.path.isfile(os.path.join(V2, mod_folder, fid, "extract.py"))


def main():
    import openpyxl
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["vic3"]
    rows = list(ws.iter_rows(values_only=True))
    ix = col_index(rows[1])

    mods = {}                         # folder -> {label, modwide, features[]}
    generic_static_rules = []         # GEN-* rows describe the shared static view
    for r in rows[2:]:
        if not any(r):
            continue
        short = r[ix["mod"]]
        fid   = r[ix["id"]]
        name  = r[ix["feature"]]
        if not fid:
            continue
        markers = r[ix["debug markers"]] if "debug markers" in ix else None
        status  = r[ix["status"]] if "status" in ix else None
        tabs    = norm_tabs(r[ix["tab"]] if "tab" in ix else None)

        if short and short.strip() == "(generic)":
            generic_static_rules.append({"id": fid, "name": name})
            continue
        folder = MOD_FOLDER.get(short)
        if not folder:
            print(f"  [warn] unknown mod short-name {short!r} (row id {fid}) — skipped")
            continue
        m = mods.setdefault(folder, {"label": short, "modwide": ["static", "log"], "features": []})
        m["features"].append({
            "id": fid, "name": name, "tabs": tabs or ["log"],
            "markers": (str(markers) if markers else ""),
            "status": (str(status) if status else ""),
            "impl": feature_impl(folder, fid),
        })

    manifest = {
        "_generated": "by tools/gen_manifest_from_xlsx.py from testbook_status.xlsx — DO NOT hand-edit",
        "version": 3,
        "tabs": [{"id": t, "label": lbl} for t, lbl in TABS],
        "static_rules": generic_static_rules,     # the shared 'static' view's sub-checks
        "mods": mods,
    }
    out = os.path.join(V2, "manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    nfeat = sum(len(m["features"]) for m in mods.values())
    nimpl = sum(1 for m in mods.values() for ft in m["features"] if ft["impl"])
    print(f"manifest -> {out}")
    print(f"  {len(mods)} mods, {nfeat} features ({nimpl} implemented, {nfeat - nimpl} stub), "
          f"{len(TABS)} tabs, {len(generic_static_rules)} static rules")
    for folder, m in mods.items():
        tabset = sorted({t for ft in m["features"] for t in ft["tabs"]})
        print(f"  {folder:20} {len(m['features'])} features -> tabs {tabset}")


if __name__ == "__main__":
    main()
