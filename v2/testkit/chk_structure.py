#!/usr/bin/env python3
"""
Static structure / encoding / syntax checks for a single Vic3 mod.

PORTED into v2 (self-contained) on 2026-06-18 from testkit/checks/structure.py.
Identical logic; v2 owns this copy so it no longer reaches into the v1 testkit.

Deterministic, zero-false-positive checks done BEFORE a mod is allowed to PR to master:
  - encoding     : script .txt + loc .yml must be UTF-8 BOM ; metadata .json must be NO BOM
  - braces       : '{' vs '}' balance per .txt
  - quotes       : even number of unescaped '"' per .txt
  - empty_scopes : no ACTIVE (non-commented) empty control/effect block per .txt (an
                   `if`/`immediate`/`option`/`trigger`/`when_taken`/... scope left empty
                   except a `limit`). Added 2026-07-04; REUSES the Framework-Toggle
                   scope_keywords config (config_toggle.toml) as the single-source keyword
                   allowlist so data empties (`traits = {}`, `impassable = {}`) are never
                   considered. Detection is char/column level (the toggle's own line-granular
                   check_scopes false-positives on single-line `if = { ... }` blocks).
  - debug_markers: INFORMATIONAL (never fails) count of ACTIVE debug_log / _fingerprint_
                   lines, via lib_toggle's own patterns - the static side of the Ceremony 3
                   promote check (must read 0 at PR/merge; expected non-zero mid-dev).
  - folder       : file sits under a known-valid mod root (allowlist; folders.cwt = v2)
  - metadata     : .metadata/metadata.json parses + has required keys

Reuse note: the last two checks import lib_toggle (Framework-Toggle) + lib_config
(Framework-common). If that framework is not importable they degrade to n/a and the core
brace/quote/encoding checks still run (best-effort import, never a hard dependency).

This is the "Static" tab data source. It reads NO game state; it only inspects files.

Usage:
    python structure.py <path-to-mod-folder> [--json <out.json>]
"""
import sys, os, json, argparse, datetime, re

BOM = b"\xef\xbb\xbf"

# --- REUSE the Framework-Toggle comment-agnostic scope/marker engine (empty-scope + debug/fp leak detection)
#     instead of re-implementing a brace parser here. Best-effort: if the toggle framework is not importable
#     (moved/renamed, missing tomllib), _TOGGLE stays None and both derived checks degrade to n/a - the core
#     brace/quote/encoding/metadata checks still run so this never becomes a hard dependency.
_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
_TOGGLE_DIR = os.path.join(_TOOLS, "Framework-Toggle")
try:
    sys.path.insert(0, _TOGGLE_DIR)
    sys.path.insert(0, os.path.join(_TOOLS, "Framework-common"))
    import lib_toggle
    _TCFG = lib_toggle.config(_TOGGLE_DIR)
except Exception:                       # toggle framework absent / config unreadable
    lib_toggle, _TCFG = None, None

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


def _match_brace(s, i):
    """s[i] is '{'; return index of the matching '}', or -1 if unbalanced."""
    depth = 0
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _strip_limit_children(inner):
    """Remove complete `limit = { ... }` spans (a limit is a condition, not body), so an `if` whose only
    content is its limit reads as empty. Depth-matched, char-level."""
    out, i = [], 0
    while i < len(inner):
        m = re.match(r"limit\s*=\s*\{", inner[i:])
        if m:
            close = _match_brace(inner, i + m.end() - 1)
            if close != -1:
                i = close + 1
                continue
        out.append(inner[i])
        i += 1
    return "".join(out)


def check_empty_scopes(text):
    """Structural check: flag any ACTIVE (uncommented) control/effect scope left empty-except-limit - an
    `if`/`else_if`/`immediate`/`option`/`trigger`/`hidden_effect`/`when_taken`/`random`/... block whose body
    is nothing but a `limit` and/or comments. The keyword set is REUSED from the Framework-Toggle config
    (config_toggle.toml scope_keywords) so it stays single-sourced and data empties (`traits = {}`,
    `impassable = {}`) are never considered. Detection is CHAR/COLUMN level (not line-granular like the
    toggle's own check_scopes, which false-positives on single-line `if = { ... }` blocks) - so compact
    one-line control blocks with a real inline body are correctly seen as non-empty."""
    if lib_toggle is None or _TCFG is None:
        return (None, "n/a (toggle lib unavailable)")
    scopes = _TCFG["scopes"]
    orig = text.splitlines()
    # comment-stripped copy, newlines preserved so we can recover line numbers; a commented-out scope
    # therefore has no opener to match and is never flagged.
    stripped = "\n".join(ln.split("#", 1)[0] for ln in orig)
    defects, cruft = [], []
    for m in re.finditer(r"([A-Za-z_]\w*)\s*=\s*\{", stripped):
        key = m.group(1)
        if key not in scopes:
            continue
        close = _match_brace(stripped, m.end() - 1)
        if close == -1:
            continue                       # unbalanced; the braces check owns that failure
        body = _strip_limit_children(stripped[m.end():close])
        if re.search(r"[A-Za-z0-9]", body):
            continue                       # has a real inline/nested effect -> not empty
        oline = stripped.count("\n", 0, m.start()) + 1
        cline = stripped.count("\n", 0, close) + 1
        # Empty ONLY because a debug_log / _fingerprint_ inside it is commented out (the expected promote
        # state, or a toggle that left the wrapper) -> benign cruft, NOT a gating defect. A scope empty with
        # no such marker is a genuine authoring dead-branch (e.g. an else_if with a limit but no effect).
        if any(lib_toggle._has_marker(l, _TCFG) for l in orig[oline - 1:cline]):
            cruft.append(oline)
        else:
            defects.append(f"line {oline}: '{key}' scope has no effect (only a limit / comments)")
    parts = []
    if defects:
        parts.append("; ".join(defects[:10]) + (f" (+{len(defects) - 10} more)" if len(defects) > 10 else ""))
    if cruft:
        parts.append(f"{len(cruft)} debug/fingerprint-only empty scope(s) [benign, collapsible]")
    return (not defects, " | ".join(parts) if parts else "no empty control scope")


def check_debug_markers(lines):
    """INFORMATIONAL (never fails the file): count ACTIVE (uncommented) debug_log / _fingerprint_ lines using
    the toggle's own patterns. The static half of the Ceremony 3 promote gate - must be 0 at PR/merge, but is
    expected non-zero mid-dev, so this only surfaces the count and never flips file_ok."""
    if lib_toggle is None or _TCFG is None:
        return (None, "n/a")
    m = _TCFG["marker"]
    n = sum(1 for ln in lines if lib_toggle._is_active(ln, m) and lib_toggle._has_marker(ln, _TCFG))
    return (True, f"{n} active debug_log/fingerprint line(s)" + (" (OFF; promote-ready)" if n == 0 else ""))


def check_folder(rel):
    root = rel.replace("\\", "/").split("/", 1)[0]
    return (root in VALID_ROOTS, f"root '{root}'" + ("" if root in VALID_ROOTS else " UNKNOWN"))


def check_sibling_mods_metadata(mod_dir):
    """Repo-level guard, run as part of EVERY per-mod check (2026-07-10).

    WHY: the CI workflow loop only invokes this checker on folders that HAVE
    .metadata/metadata.json, so a mod that accidentally lost its metadata was
    silently skipped and shipped broken (the game will not load it). Scanning
    the CHECKED mod's sibling folders closes that hole with NO workflow change:
    any per-mod run fails if a sibling looks like a mod but carries no metadata.

    The logic lives in the individually-callable SUB-SCRIPT
    chk-mods-have-metadata.py (run it standalone on a repo root for details);
    hyphen-named sub-scripts are invoked as SUBPROCESSES per the naming rule.
    Degrades to n/a if the sub-script is absent (same best-effort stance as the
    lib_toggle imports).
    """
    sub = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chk-mods-have-metadata.py")
    if not os.path.isfile(sub):
        return {"ok": None, "msg": "chk-mods-have-metadata.py sub-script not found - n/a"}
    root = os.path.dirname(os.path.abspath(os.path.normpath(mod_dir)))
    try:
        import subprocess
        r = subprocess.run([sys.executable, sub, root],
                           capture_output=True, text=True, timeout=60)
    except Exception as e:
        return {"ok": None, "msg": f"sibling scan unavailable: {e}"}
    if r.returncode == 0:
        return {"ok": True, "msg": "all sibling mod folders carry metadata"}
    detail = "; ".join(l.strip() for l in (r.stdout or "").splitlines() if "FAIL" in l) \
             or (r.stdout or r.stderr or "").strip()[-200:]
    return {"ok": False, "msg": detail or "sibling mod folder(s) missing metadata"}


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
                es_ok, es_msg = check_empty_scopes(text)
                checks["empty_scopes"] = {"ok": es_ok, "msg": es_msg}
                dm_ok, dm_msg = check_debug_markers(text.splitlines())
                checks["debug_markers"] = {"ok": dm_ok, "msg": dm_msg}
            file_ok = all(c["ok"] for c in checks.values() if c["ok"] is not None)
            files.append({"path": rel.replace("\\", "/"), "ok": file_ok, "checks": checks})

    meta = check_metadata(mod_dir)
    siblings = check_sibling_mods_metadata(mod_dir)
    extra = 1 if siblings["ok"] is not None else 0
    passed = (sum(1 for f in files if f["ok"]) + (1 if meta["ok"] else 0)
              + (1 if siblings["ok"] else 0))
    total = len(files) + 1 + extra
    return {
        "mod": mod,
        "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "metadata": meta,
        "sibling_mods_metadata": siblings,
        "files": files,
        "summary": {"checks": total, "passed": passed, "failed": total - passed},
    }


def print_summary(res):
    print(f"\n=== STATIC CHECKS: {res['mod']} ===")
    m = res["metadata"]
    print(f"  [{'OK ' if m['ok'] else 'FAIL'}] metadata.json  {m['msg']}")
    sib = res.get("sibling_mods_metadata")
    if sib and sib["ok"] is not None:
        print(f"  [{'OK ' if sib['ok'] else 'FAIL'}] sibling mods metadata  {sib['msg']}")
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
