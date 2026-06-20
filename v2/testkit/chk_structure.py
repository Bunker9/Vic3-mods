#!/usr/bin/env python3
"""
Static structure / encoding / syntax checks for a single Vic3 mod.

PORTED into v2 (self-contained) on 2026-06-18 from testkit/checks/structure.py.
Identical logic; v2 owns this copy so it no longer reaches into the v1 testkit.

Deterministic, zero-false-positive checks done BEFORE a mod is allowed to PR to master:
  - encoding   : script .txt + loc .yml must be UTF-8 BOM ; metadata .json must be NO BOM
  - braces     : '{' vs '}' balance per .txt
  - quotes     : even number of unescaped '"' per .txt
  - folder     : file sits under a known-valid mod root (allowlist; folders.cwt = v2)
  - metadata   : .metadata/metadata.json parses + has required keys

This is the "Static" tab data source. It reads NO game state; it only inspects files.

Usage:
    python structure.py <path-to-mod-folder> [--json <out.json>]
"""
import sys, os, json, argparse, datetime

BOM = b"\xef\xbb\xbf"

# Valid top-level roots inside a Vic3 mod (v1 allowlist; refine from folders.cwt later).
VALID_ROOTS = {"common", "events", "localization", "gfx", "music", "sound",
               "map_data", "gui", "fonts", "jomini", "dlc_metadata", ".metadata"}
# Files we don't encoding/syntax-check.
SKIP_EXT = {".dds", ".tga", ".png", ".bk2", ".yml~", ".md", ".gitkeep",
            ".ogg", ".wav", ".mesh", ".gfx~"}
# Editor/tooling dirs that live alongside a mod but are NOT mod content (gitignored).
SKIP_DIRS = {".git", ".vscode", ".claude", ".idea", "__pycache__"}


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def check_encoding(path, data):
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path).lower()
    has_bom = data.startswith(BOM)
    if name.endswith(".json"):
        return (not has_bom, "no BOM (correct for json)" if not has_bom
                else "HAS BOM (json must NOT have one)")
    if ext in (".txt", ".yml"):
        return (has_bom, "UTF-8 BOM" if has_bom else "MISSING UTF-8 BOM")
    return (None, "n/a")


def check_braces(text):
    o, c = text.count("{"), text.count("}")
    return (o == c, f"{{ {o}  }} {c}")


def check_quotes(text):
    # count unescaped double-quotes; odd = unbalanced
    q = text.count('"') - text.count('\\"')
    return (q % 2 == 0, f'{q} quotes ({"even" if q % 2 == 0 else "ODD"})')


def check_folder(rel):
    root = rel.replace("\\", "/").split("/", 1)[0]
    return (root in VALID_ROOTS, f"root '{root}'" + ("" if root in VALID_ROOTS else " UNKNOWN"))


def check_metadata(mod_dir):
    mp = os.path.join(mod_dir, ".metadata", "metadata.json")
    if not os.path.isfile(mp):
        return {"ok": False, "msg": ".metadata/metadata.json MISSING"}
    raw = read_bytes(mp)
    if raw.startswith(BOM):
        return {"ok": False, "msg": "metadata.json has a BOM (must not)"}
    try:
        meta = json.loads(raw.decode("utf-8"))
    except Exception as e:
        return {"ok": False, "msg": f"metadata.json invalid JSON: {e}"}
    required = ["name", "game_id", "supported_game_version"]
    missing = [k for k in required if k not in meta]
    if missing:
        return {"ok": False, "msg": f"missing keys: {', '.join(missing)}"}
    if meta.get("game_id") != "victoria3":
        return {"ok": False, "msg": f"game_id = {meta.get('game_id')!r} (expected 'victoria3')"}
    return {"ok": True, "msg": f"name={meta['name']} ver={meta['supported_game_version']}"}


def run(mod_dir):
    mod = os.path.basename(os.path.normpath(mod_dir))
    files = []
    for dirpath, dirnames, filenames in os.walk(mod_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]  # prune tooling dirs
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, mod_dir)
            ext = os.path.splitext(fn)[1].lower()
            if ext in SKIP_EXT or fn == ".gitkeep":
                continue
            if rel.replace("\\", "/").startswith(".git"):
                continue
            data = read_bytes(full)
            checks = {}
            enc_ok, enc_msg = check_encoding(fn, data)
            if enc_ok is not None:
                checks["encoding"] = {"ok": enc_ok, "msg": enc_msg}
            fold_ok, fold_msg = check_folder(rel)
            checks["folder"] = {"ok": fold_ok, "msg": fold_msg}
            if ext == ".txt":
                text = data.decode("utf-8-sig", errors="replace")
                b_ok, b_msg = check_braces(text)
                q_ok, q_msg = check_quotes(text)
                checks["braces"] = {"ok": b_ok, "msg": b_msg}
                checks["quotes"] = {"ok": q_ok, "msg": q_msg}
            file_ok = all(c["ok"] for c in checks.values() if c["ok"] is not None)
            files.append({"path": rel.replace("\\", "/"), "ok": file_ok, "checks": checks})

    meta = check_metadata(mod_dir)
    passed = sum(1 for f in files if f["ok"]) + (1 if meta["ok"] else 0)
    total = len(files) + 1
    return {
        "mod": mod,
        "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "metadata": meta,
        "files": files,
        "summary": {"checks": total, "passed": passed, "failed": total - passed},
    }


def print_summary(res):
    print(f"\n=== STATIC CHECKS: {res['mod']} ===")
    m = res["metadata"]
    print(f"  [{'OK ' if m['ok'] else 'FAIL'}] metadata.json  {m['msg']}")
    for f in res["files"]:
        flag = "OK " if f["ok"] else "FAIL"
        bad = "" if f["ok"] else "  <- " + "; ".join(
            f"{k}:{v['msg']}" for k, v in f["checks"].items() if v["ok"] is False)
        print(f"  [{flag}] {f['path']}{bad}")
    s = res["summary"]
    print(f"  ---- {s['passed']}/{s['checks']} passed, {s['failed']} failed ----")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mod_dir")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = run(a.mod_dir)
    print_summary(res)
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        print(f"  json -> {a.json}")
    sys.exit(0 if res["summary"]["failed"] == 0 else 1)
