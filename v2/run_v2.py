#!/usr/bin/env python3
"""
v2 testbook orchestrator — xlsx-driven, self-contained (no v1 imports).

manifest.json is GENERATED from testbook_status.xlsx (tools/gen_manifest_from_xlsx.py); it is the
single source of truth for the FEATURE taxonomy. Do not hand-edit it.

Two kinds of rendered unit (both are "cards"; "feature" is reserved for real mod mechanics):
  - VIEW  (mod-wide)  : static / log — generic analyzers, NOT features. Output under
                        v2/<Mod>/_modwide/<view>/. Rendered as data-view cards.
  - FEATURE (per mod) : a real mod mechanic from the xlsx IDENTITY id (e.g. ECO-YEARLY). If
                        v2/<Mod>/<ID>/extract.py exists it is run + rendered; otherwise a STUB
                        card (xlsx metadata) marks it as pending. Rendered as data-feature cards.

A feature is placed on every tab in its WHERE-TO-DISPLAY list. Per-tab components are
component_<tab>.html; a single component.html serves the feature's first tab.

Usage:
    python testbook/v2/run_v2.py                  # all mods
    python testbook/v2/run_v2.py Top40EcoBoostMod # one mod
    python testbook/v2/run_v2.py --open           # build + open in browser
"""
import os, sys, json, re, argparse, importlib.util, subprocess, webbrowser
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

HERE    = os.path.dirname(os.path.abspath(__file__))   # .../testbook/v2
TBDIR   = os.path.dirname(HERE)
TESTKIT = os.path.join(HERE, "testkit")             # shared lib + analyzers + extractors (flat)
sys.path.insert(0, TESTKIT)

import lib_components as fb
import lib_buildstamp as build_stamp
from lib_paths import resolve_logs_dir


def load_manifest():
    with open(os.path.join(HERE, "manifest.json"), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Run phase
# ---------------------------------------------------------------------------
def _import(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_view(mod_name, view, logs_dir):
    """Mod-wide view (static / log) via the generic analyzer -> _modwide/<view>/."""
    out_dir = os.path.join(HERE, mod_name, "_modwide", view)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(TESTKIT, f"ext_{view}.py")
    if not os.path.isfile(path):
        return
    try:
        _import(path, f"_view_{view}").run(out_dir, logs_dir)
    except Exception as e:
        print(f"  [ERROR] {mod_name}/_modwide/{view}: {e}")


def feature_dir(mod_name, fid):
    return os.path.join(HERE, mod_name, fid)


def feature_impl(mod_name, fid):
    return os.path.isfile(os.path.join(feature_dir(mod_name, fid), "extract.py"))


def run_feature(mod_name, fid, logs_dir):
    fdir = feature_dir(mod_name, fid)
    path = os.path.join(fdir, "extract.py")
    if not os.path.isfile(path):
        return
    try:
        _import(path, f"_feat_{mod_name}_{fid}").run(fdir, logs_dir)
    except Exception as e:
        print(f"  [ERROR] {mod_name}/{fid}: {e}")


# ---------------------------------------------------------------------------
# Component / summary readers
# ---------------------------------------------------------------------------
def read_body(path):
    """Read a component html file; strip a leading TBCOMP marker line; return body or None."""
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lines = content.splitlines()
    if lines and lines[0].startswith("<!-- TBCOMP"):
        return "\n".join(lines[1:])
    return content


def view_clean(view, summary):
    if not summary:
        return False
    if view == "static":
        return summary.get("fail", 1) == 0 and summary.get("standards", 1) == 0
    if view == "log":
        # clean = no errors AND the mod logged something (emitted==0 is a smoking gun -> stay open)
        return summary.get("errors", 1) == 0 and summary.get("emitted", 0) > 0
    return False


# ---------------------------------------------------------------------------
# Card builders
# ---------------------------------------------------------------------------
def view_card(mod_name, view):
    """A mod-wide view card (static / log). Returns (sort_key, html) or None."""
    vdir = os.path.join(HERE, mod_name, "_modwide", view)
    body = read_body(os.path.join(vdir, "component.html"))
    if body is None:
        return None
    summary = fb.read_data(vdir, "summary.json")
    clean   = view_clean(view, summary)
    pill    = fb.badge("ok", "clean") if clean else ""
    head    = f"<h2>{fb.esc(mod_name)}<span class='hpill'>{pill}</span></h2>"
    inner   = (f"<details><summary class='small'>clean — click to expand</summary>{body}</details>"
               if clean else body)
    html = (f"<div class='card' data-view='{view}' data-mod='{mod_name}'>{head}{inner}</div>")
    return ((mod_name, 0, view), html)


def feature_card(mod_name, feat, tab):
    """A per-feature card on `tab` — its component if implemented, else a stub. (sort_key, html)."""
    fid  = feat["id"]
    fdir = feature_dir(mod_name, fid)
    impl = feature_impl(mod_name, fid)
    name = feat.get("name", fid)
    tag  = f"<span class='mod-tag'>{fb.esc(mod_name)} · {fb.esc(fid)}</span>"

    body = None
    if impl:
        body = read_body(os.path.join(fdir, f"component_{tab}.html"))
        if body is None and feat["tabs"] and tab == feat["tabs"][0]:
            body = read_body(os.path.join(fdir, "component.html"))

    if body is not None:
        head = f"<h2>{fb.esc(name)}{tag}</h2>"
        html = f"<div class='card' data-feature='{fid}' data-mod='{mod_name}'>{head}{body}</div>"
    else:
        st   = feat.get("status") or ""
        pill = fb.badge("warn", st) if st else fb.badge("grey", "pending")
        head = f"<h2>{fb.esc(name)}{tag}<span class='hpill'>{pill}</span></h2>"
        html = (f"<div class='card stub' data-feature='{fid}' data-mod='{mod_name}'>"
                f"{head}{fb.stub_card_body(feat)}</div>")
    order = int(feat.get("order") or 0)
    return ((mod_name, 1, f"{order:03d}-{fid}"), html)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def build_dashboard(manifest, mods):
    rows = []
    for mod_name in mods:
        mod_cfg = manifest["mods"][mod_name]
        b = [f"<span class='dash-mod'>{fb.esc(mod_name)}</span><span class='dash-stats'>"]
        sd = fb.read_data(os.path.join(HERE, mod_name, "_modwide", "static"), "summary.json")
        b.append(fb.badge("ok" if sd and sd["fail"] == 0 else ("bad" if sd else "grey"),
                          f"static: {sd['fail']}f" if sd else "static: ?"))
        ld = fb.read_data(os.path.join(HERE, mod_name, "_modwide", "log"), "summary.json")
        if ld:
            b.append(fb.badge("grey" if ld.get("emitted") else "bad", f"{ld.get('emitted',0)} logs"))
            b.append(fb.badge("ok" if ld["errors"] == 0 else "bad", f"{ld['errors']}e"))
        else:
            b.append(fb.badge("grey", "log: ?"))
        feats = mod_cfg["features"]
        nimpl = sum(1 for ft in feats if feature_impl(mod_name, ft["id"]))
        b.append(fb.badge("ok" if nimpl == len(feats) else "warn",
                          f"features: {nimpl}/{len(feats)}"))
        b.append("</span>")
        rows.append(f"<div class='dash-row'>{''.join(b)}</div>")
    return f"<div class='dashboard'>{''.join(rows)}</div>"


# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------
def global_errors_card():
    """The framework-level global Errors card (game-wide cpp error.log). (sort_key, html) or None."""
    gdir = os.path.join(HERE, "_global", "errors")
    body = read_body(os.path.join(gdir, "component.html"))
    if body is None:
        return None
    gsum = fb.read_data(gdir, "summary.json") or {}
    n = gsum.get("total", 0)
    pill = fb.badge("bad" if n else "ok", f"{n} cpp errors")
    head = f"<h2>Game error.log (global)<span class='hpill'>{pill}</span></h2>"
    html = f"<div class='card' data-view='errors' data-mod=''>{head}{body}</div>"
    return ((" ", 0, "errors"), html)


def assemble(manifest, branch, stamp, mods):
    tab_cfgs = list(manifest["tabs"])
    if not any(t["id"] == "errors" for t in tab_cfgs):       # framework tab (not from xlsx)
        tab_cfgs = tab_cfgs + [{"id": "errors", "label": "Errors"}]
    # gather cards per tab
    tabs = {t["id"]: [] for t in tab_cfgs}
    for mod_name in mods:
        mod_cfg = manifest["mods"][mod_name]
        for view in mod_cfg.get("modwide", []):
            if view in tabs:
                c = view_card(mod_name, view)
                if c:
                    tabs[view].append(c)
        for feat in mod_cfg["features"]:
            for tab in feat["tabs"]:
                if tab in tabs:
                    tabs[tab].append(feature_card(mod_name, feat, tab))
    gec = global_errors_card()
    if gec:
        tabs["errors"].append(gec)
    for t in tabs:
        tabs[t].sort(key=lambda x: x[0])

    mod_opts = ["<option value=''>All mods</option>"] + [
        f"<option value='{m}'>{fb.esc(m)}</option>" for m in mods]
    mod_filter = f"<select id='mod-filter'>{''.join(mod_opts)}</select>"

    tab_btns = "".join(
        f"<div class='tab{'  active' if i == 0 else ''}' data-tab='{t['id']}' "
        f"onclick=\"showTab('{t['id']}')\">{fb.esc(t['label'])}</div>"
        for i, t in enumerate(tab_cfgs))

    panel_html = []
    for i, t in enumerate(tab_cfgs):
        panel_html.append(f"<div class='panel{' active' if i == 0 else ''}' data-tab='{t['id']}'>")
        cards = tabs.get(t["id"], [])
        if cards:
            panel_html += [html for _, html in cards]
        else:
            panel_html.append("<p class='muted small'>No cards for this tab.</p>")
        panel_html.append("</div>")

    stamp_str = ""
    if stamp and stamp[0]:
        tag = "loaded build" if stamp[1] == "log" else "source stamp"
        stamp_str = f" &nbsp; <span class='small'>build: <b>{fb.esc(stamp[0])}</b> ({tag})</span>"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Vic3 v2 — {fb.esc(branch)}</title>
<style>{fb.CSS}</style></head><body>
<header>
  <h1>Vic3 test v2 — <code>{fb.esc(branch)}</code></h1>
  <div class='hdr-sub'>generated {now}{stamp_str} &nbsp;
    <span class='small'>xlsx-driven · re-run <code>python testbook/v2/run_v2.py</code> then F5.</span>
  </div>
</header>
{build_dashboard(manifest, mods)}
<div class='nav-bar'>
  {mod_filter}
  <div class='tabs'>{tab_btns}</div>
</div>
<div id='panels'>
  {''.join(panel_html)}
</div>
<div id='toTop' onclick='toTop()'>&#8679; Top</div>
<script>{fb.JS}</script>
</body></html>"""


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mods", nargs="*")
    ap.add_argument("--logs")
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()

    manifest = load_manifest()
    all_mods = list(manifest["mods"])
    mods = [m for m in (a.mods or all_mods) if m in manifest["mods"]]

    # Name the report after the MOD branch under test (mod1: dev/test/release), NOT the
    # testbook worktree's own orphan branch.
    try:
        branch = subprocess.check_output(
            ["git", "-C", fb.MOD1, "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    except Exception:
        branch = "unknown"
    logs_dir = a.logs or resolve_logs_dir()
    print(f"v2 build — branch: {branch}, logs: {logs_dir or '(none)'}")

    # run views + implemented features in parallel
    tasks = []
    for m in mods:
        for view in manifest["mods"][m].get("modwide", []):
            tasks.append(("view", m, view))
        for feat in manifest["mods"][m]["features"]:
            if feature_impl(m, feat["id"]):
                tasks.append(("feat", m, feat["id"]))

    def _run(t):
        if t[0] == "view":
            run_view(t[1], t[2], logs_dir)
        else:
            run_feature(t[1], t[2], logs_dir)

    with ThreadPoolExecutor() as ex:
        list(ex.map(_run, tasks))

    # GLOBAL "Errors" view — game-wide cpp error.log, rendered once (not per-mod, not from xlsx).
    try:
        _import(os.path.join(TESTKIT, "ext_errors.py"), "_view_errors").run(
            os.path.join(HERE, "_global", "errors"), logs_dir)
    except Exception as e:
        print(f"  [ERROR] _global/errors: {e}")

    try:
        stamp = build_stamp.read_build_stamp(logs_dir)
    except Exception:
        stamp = (None, None)

    html = assemble(manifest, branch, stamp, mods)
    out  = os.path.join(HERE, f"MAIN-{branch.replace('/', '-')}-testing.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Assembled -> {out}")
    if a.open:
        webbrowser.open("file:///" + out.replace("\\", "/"))


if __name__ == "__main__":
    main()
