#!/usr/bin/env python3
"""
Parse the Victoria 3 logs after an in-game test run -> per-mod results for the Log tab.

PORTED into v2 (self-contained) on 2026-06-18 from testkit/checks/log_triage.py.
ONLY change vs v1: the TESTBOOK root is resolved one level deeper (this file now lives at
v2/testkit/generic/, so the testbook root is 4 dirnames up instead of 3). Logic identical.
Props are still read from testbook/<Mod>/props.toml (shared with v1 — not duplicated).

Produces, per mod:
  - errors  : error.log entries referencing THIS mod's files (each marked benign or real)
  - census  : building levels placed vs expected cap (mods that declare [census] in props)
And shared: non_mod_errors (vanilla/other) + suspect_mod (create_building over-capacity).

Usage:
    python log_triage.py --logs <vic3 logs dir> --mods <mod_dir> [<mod_dir> ...] [--json out.json]
"""
import sys, os, re, json, argparse, datetime, tomllib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_paths import resolve_logs_dir  # noqa: E402

# Universal benign substrings (engine-level, mod-agnostic). Mod-specific benign + census
# config live in each mod's testbook/<Mod>/props.toml — NOT in this script.
UNIVERSAL_BENIGN = ("should be in utf8-bom encoding",)

# this file: .../testbook/v2/testkit/parse_log.py -> testbook root is 3 dirnames up.
# The per-mod authored spec (props.toml: census / benign / tables) is shared data that lives
# under the v1 archive (testbook/v1/<Mod>/). v2 reads it but imports no v1 CODE.
_TESTBOOK = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))                # .../testbook
PROPS_ROOT = os.path.join(_TESTBOOK, "v1")      # .../testbook/v1


def load_props(mod):
    """Read the shared testbook/v1/<Mod>/props.toml; return {} if absent."""
    p = os.path.join(PROPS_ROOT, mod, "props.toml")
    if not os.path.isfile(p):
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)


def mod_signatures(mod_dirs, props_by_mod):
    """For each mod -> (set of posix relpaths, set of basenames + props extra_signatures)."""
    sigs = {}
    for md in mod_dirs:
        mod = os.path.basename(os.path.normpath(md))
        paths, bases = set(), set()
        for dp, dn, fns in os.walk(md):
            dn[:] = [d for d in dn if d not in (".git", ".vscode", ".claude", "__pycache__")]
            for fn in fns:
                if os.path.splitext(fn)[1].lower() in (".txt", ".yml", ".json"):
                    rel = os.path.relpath(os.path.join(dp, fn), md).replace("\\", "/")
                    paths.add(rel)
                    bases.add(fn)
        bases.update(props_by_mod.get(mod, {}).get("errors", {}).get("extra_signatures", []))
        sigs[mod] = (paths, bases)
    return sigs


def read_lines(p):
    if not p or not os.path.isfile(p):
        return []
    with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read().splitlines()


def parse_error_entries(lines):
    """Group error.log into entries: a [timestamp] line + its indented continuation lines."""
    entries, cur = [], None
    for ln in lines:
        if re.match(r"^\[\d", ln):
            if cur:
                entries.append(cur)
            cur = [ln]
        elif cur is not None and ln.strip():
            cur.append(ln)
    if cur:
        entries.append(cur)
    return ["\n".join(e) for e in entries]


def attribute(entry, sigs):
    """Return the mod name whose file is referenced in this entry, else None."""
    for mod, (paths, bases) in sigs.items():
        if any(p in entry for p in paths) or any(re.search(r"\b" + re.escape(b) + r"\b", entry) for b in bases):
            return mod
    return None


_FILE_RX = (re.compile(r"Script location:\s*([^\s:]+\.[a-z0-9]+)"),
            re.compile(r"File '([^']+)'"),
            re.compile(r"\b([\w./\\-]+\.(?:txt|gui|gfx|yml|json|asset|mesh|lua))\b"))


def extract_file(entry):
    """Best-effort source file an error refers to (for grouping non-mod errors)."""
    for rx in _FILE_RX:
        m = rx.search(entry)
        if m:
            return m.group(1).replace("\\", "/")
    m = re.search(r"\[(\w+\.cpp):\d+\]", entry)        # engine-source tag fallback
    return "engine:" + m.group(1) if m else "(unattributed)"


def parse_census(debug_lines, census_cfg):
    """Generic census from a mod's props [census]: source_file, marker (placed), have_marker,
    expected{}. Country is read from the 'Root: Country <Name>' lines debug_log_scopes emits."""
    source = census_cfg["source_file"]
    expected = census_cfg.get("expected", {})
    rx = re.compile(re.escape(source) + r":\d+:\s*(.+?)\s*$")
    p_rx = re.compile(r"^" + re.escape(census_cfg["marker"]) + r"\s+(\w+)")
    have_m = census_cfg.get("have_marker")
    h_rx = re.compile(r"^" + re.escape(have_m) + r"\s+(\w+)") if have_m else None
    root_rx = re.compile(r"Root:\s*Country\s+(.+?)\s*\(")
    out, cur = [], None
    for ln in debug_lines:
        m = rx.search(ln)
        if m:
            p = m.group(1)
            ph = p_rx.match(p)
            hh = h_rx.match(p) if h_rx else None
            if ph and cur:
                cur["placed"] += 1
                cur["type"] = ph.group(1)
            elif hh and cur:
                cur["have"] += 1
                cur["type"] = hh.group(1)
            elif not ph and not hh and p:
                cur = {"building": p, "country": "?", "type": "?", "placed": 0, "have": 0}
                out.append(cur)
            continue
        rm = root_rx.search(ln)
        if rm and cur and cur["country"] == "?":
            cur["country"] = rm.group(1)
    additive = set(census_cfg.get("additive_types", []))
    for row in out:
        exp = expected.get(row["building"])
        cap = exp["cap"] if exp else None
        row["expected"] = cap
        if cap is None:
            row["need"], row["ok"] = None, False
        elif row["type"] in additive:
            row["need"] = cap
            row["ok"] = row["placed"] >= cap
        else:
            row["need"] = max(0, cap - row["have"])
            row["ok"] = row["have"] + row["placed"] >= cap
    return out


def parse_tables(debug_lines, tables_cfg):
    """Generic per-mod tables: each props [[tables]] = {title, marker, source_file, columns}.
    The mod logs `debug_log` rows like `MARKER cellA | cellB | cellC`; we split on '|'."""
    out = []
    for t in tables_cfg:
        src = re.escape(t["source_file"]) if t.get("source_file") else r"[\w./-]+\.txt"
        rx = re.compile(src + r":\d+:\s*" + re.escape(t["marker"]) + r"\s+(.*?)\s*$")
        rows = [[c.strip() for c in m.group(1).split("|")]
                for ln in debug_lines for m in [rx.search(ln)] if m]
        out.append({"title": t.get("title", t["marker"]),
                    "columns": t.get("columns", []), "rows": rows})
    return out


def run(logs_dir, mod_dirs):
    mod_names = [os.path.basename(os.path.normpath(md)) for md in mod_dirs]
    props_by_mod = {m: load_props(m) for m in mod_names}
    sigs = mod_signatures(mod_dirs, props_by_mod)
    err_lines = read_lines(os.path.join(logs_dir, "error.log")) if logs_dir else []
    dbg_lines = read_lines(os.path.join(logs_dir, "debug.log")) if logs_dir else []

    benign_subs = list(UNIVERSAL_BENIGN)
    for p in props_by_mod.values():
        benign_subs += p.get("errors", {}).get("benign", [])

    mods = {m: {"errors": [], "census": [], "tables": []} for m in sigs}
    non_mod = []
    for entry in parse_error_entries(err_lines):
        benign = any(b in entry for b in benign_subs)
        owner = attribute(entry, sigs)
        rec = {"text": entry, "benign": benign}
        if owner:
            mods[owner]["errors"].append(rec)
        elif not benign:
            non_mod.append(rec)

    census = []
    for m in mod_names:
        cfg = props_by_mod[m].get("census")
        if cfg:
            c = parse_census(dbg_lines, cfg)
            mods[m]["census"] = c
            census += c
        tcfg = props_by_mod[m].get("tables")
        if tcfg:
            mods[m]["tables"] = parse_tables(dbg_lines, tcfg)

    by_file = {}
    for rec in non_mod:
        by_file.setdefault(extract_file(rec["text"]), []).append(rec["text"])
    non_mod_groups = [{"file": f, "count": len(v), "entries": v}
                      for f, v in sorted(by_file.items(), key=lambda kv: -len(kv[1]))]

    SUP_RX  = re.compile(r"(?:State|Building in) (.+?) has \d+ of building type (.+?) and can only support (\d+)")
    BACK_RX = re.compile(r"Failed creating backing building for Building Type (building_\w+) in State '([^']+)'")
    suspect = []
    for rec in non_mod:
        t = rec["text"]
        m = SUP_RX.search(t)
        if m:
            src = ("HISTORY create_building wrong (state.cpp)" if "state.cpp" in t
                   else "runtime over-build (building_manager.cpp)" if "building_manager" in t
                   else "over-capacity")
            suspect.append({"state": m.group(1), "building": m.group(2),
                            "supports": m.group(3), "source": src, "text": t})
            continue
        b = BACK_RX.search(t)
        if b:
            suspect.append({"state": b.group(2), "building": b.group(1),
                            "supports": "backing-fail", "source": "backing build failed (pdx_assert)", "text": t})
        elif any(s in t for s in ("can only support", "Failed creating backing building")):
            suspect.append({"state": "?", "building": "?", "supports": "?",
                            "source": "create_building over-capacity", "text": t})

    for m in mods:
        mbf = {}
        for e in mods[m]["errors"]:
            if not e["benign"]:
                mbf.setdefault(extract_file(e["text"]), []).append(e["text"])
        mods[m]["error_groups"] = [{"file": f, "count": len(v), "entries": v}
                                   for f, v in sorted(mbf.items(), key=lambda kv: -len(kv[1]))]

    # health smoking-gun: how many debug.log lines did each mod EMIT? Attribute by the source-file
    # the marker line carries (`<relpath>:<lineno>:`); the `-` dashed markers are the human finder,
    # but file-basename attribution is robust + catches non-dashed markers too. 0 emitted = the mod
    # likely isn't running at all (independent of whether there were errors).
    base2mod = {}
    for m, (paths, bases) in sigs.items():
        for b in bases:
            base2mod.setdefault(b, m)
    _FILE_LINE_RX = re.compile(r"([\w.\-]+\.(?:txt|yml)):\d+:")
    emitted = {m: 0 for m in sigs}
    for ln in dbg_lines:
        fm = _FILE_LINE_RX.search(ln)
        if fm:
            owner = base2mod.get(fm.group(1))
            if owner:
                emitted[owner] += 1
    for m in mods:
        mods[m]["emitted"] = emitted.get(m, 0)

    real_mod_errs = sum(1 for m in mods.values() for e in m["errors"] if not e["benign"])
    return {
        "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "logs_dir": logs_dir,
        "mods": mods,
        "non_mod_errors": non_mod,
        "non_mod_groups": non_mod_groups,
        "suspect_mod": suspect,
        "summary": {"mod_real_errors": real_mod_errs, "non_mod_errors": len(non_mod),
                    "non_mod_files": len(non_mod_groups), "census_rows": len(census),
                    "suspect_mod": len(suspect)},
    }


def print_summary(res):
    for mod, d in res["mods"].items():
        print(f"\n=== LOG: {mod} ===")
        if d["census"]:
            for r in d["census"]:
                flag = "OK " if r["ok"] else "<< "
                print(f"  {flag}{r.get('country','?'):<14} {r['building']:<22} "
                      f"have {r.get('have',0)} need {r.get('need','?')} placed {r['placed']}/{r['expected']}")
        real = [e for e in d["errors"] if not e["benign"]]
        ben = [e for e in d["errors"] if e["benign"]]
        print(f"  errors: {len(real)} real, {len(ben)} benign")
        for e in real[:10]:
            print("   ! " + e["text"].splitlines()[0])
    print(f"\n=== NON-MOD (vanilla/other) real errors: {len(res['non_mod_errors'])} ===")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs")
    ap.add_argument("--mods", nargs="+", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    logs = a.logs or resolve_logs_dir()
    res = run(logs, a.mods)
    print_summary(res)
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        print(f"\njson -> {a.json}")
