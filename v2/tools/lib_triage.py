#!/usr/bin/env python3
r"""
lib_triage.py — shared helpers for the generic per-mod log-triage job.

NOT run directly. Imported by the orchestrator (run_log_triage.py) and every sub-script
(ext_*/aggr_*/anal_*). Centralizes the STANDARDIZED arg contract + all path/IO/parse logic so no
sub-script hardcodes a path.

Standardized arg contract (master AND every sub-script):
  arg1  MOD_NAME   (required)  -> output namespace testbook/v2/tools/<MOD_NAME>/
  arg2  MOD_PATH   (optional)  -> mod source folder; needed only to (re)build the lists
  --rerun                      -> force-rebuild lists (else reuse-if-present, build-if-missing)
  --prefix P                   -> override the auto-derived keyword prefix
  --logs DIR                   -> override the auto-resolved Vic3 logs dir

Reuse-friendly: log-dir resolution, mod-file walk, prefix detection, and CSV IO are generic.
"""
import os, sys, csv, re, argparse

HERE = os.path.dirname(os.path.abspath(__file__))   # testbook/v2/tools

# Text source extensions worth scanning (logs cite these); binaries are skipped.
TEXT_EXT = {".txt", ".yml", ".yaml", ".gui", ".json"}

# SHARED benign catalog lives OUTSIDE every mod (these patterns recur across mods). It is
# human-curated: column 1 'human_agreed' (Y=truly benign/suppress, N=NOT benign/keep reporting as a
# tracked error, blank=unreviewed). Seeded ONCE with the project's known-benign utf8-bom noise.
SHARED_BENIGN = os.path.join(HERE, "benign.csv")
DEFAULT_BENIGN = [
    ("Y", "should be in utf8-bom encoding", 0),
]


# ---- standardized arg contract ----------------------------------------------
def build_parser(desc):
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("mod_name", metavar="MOD_NAME",
                   help="mod basename; output namespace testbook/v2/tools/<MOD_NAME>/")
    p.add_argument("mod_path", metavar="MOD_PATH", nargs="?", default=None,
                   help="mod source folder (only needed to (re)build lists)")
    p.add_argument("--rerun", action="store_true",
                   help="force-rebuild the lists (else reuse-if-present)")
    p.add_argument("--prefix", default=None, help="override the auto-derived keyword prefix")
    p.add_argument("--logs", default=None, help="override the Vic3 logs dir")
    return p


def parse_args(desc):
    return build_parser(desc).parse_args()


# ---- paths ------------------------------------------------------------------
def tools_dir(mod_name, create=True):
    """Per-mod output dir testbook/v2/tools/<MOD_NAME>/ (self-located, never passed in)."""
    d = os.path.join(HERE, mod_name)
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def out_path(mod_name, filename):
    return os.path.join(tools_dir(mod_name), filename)


def resolve_logs_dir(override=None):
    """Vic3 logs dir. Honors --logs, else resolves Documents via the HKCU 'Personal' shell folder
    (OneDrive-redirected on this machine) + Paradox Interactive\\Victoria 3\\logs."""
    if override:
        return override
    docs = None
    try:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            docs = os.path.expandvars(winreg.QueryValueEx(k, "Personal")[0])
    except Exception:
        docs = os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.join(docs, "Paradox Interactive", "Victoria 3", "logs")


# ---- IO ---------------------------------------------------------------------
def read_text_lines(path):
    """Read a text file as a list of lines, BOM-stripped, decode-robust."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read().splitlines()


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def read_csv(path):
    """Return (header, rows) or (None, []) if absent."""
    if not os.path.exists(path):
        return None, []
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = list(csv.reader(f))
    if not r:
        return None, []
    return r[0], r[1:]


# ---- mod source ------------------------------------------------------------
def walk_mod_files(mod_path):
    """Yield (rel_path, abs_path, basename) for every text source file under the mod folder."""
    out = []
    for root, _dirs, files in os.walk(mod_path):
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() in TEXT_EXT:
                ap = os.path.join(root, fn)
                rel = os.path.relpath(ap, mod_path).replace("\\", "/")
                out.append((rel, ap, fn))
    return sorted(out, key=lambda t: t[0])


_IDENT = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")
_PREFIX = re.compile(r"^([a-z]{2,8})_")


def detect_prefix(mod_files):
    """Dominant '<short>_' identifier prefix across the mod's text files (e.g. 'nous')."""
    from collections import Counter
    tally = Counter()
    for _rel, ap, _fn in mod_files:
        for line in read_text_lines(ap):
            for tok in _IDENT.findall(line):
                m = _PREFIX.match(tok)
                if m:
                    tally[m.group(1)] += 1
    if not tally:
        return None
    return tally.most_common(1)[0][0]


# ---- shared benign catalog -------------------------------------------------
BENIGN_HEADER = ["human_agreed", "pattern", "count"]


def seed_shared_benign():
    """Create the shared benign.csv with the known-benign seed if absent. Never clobbers a curated file."""
    if not os.path.exists(SHARED_BENIGN):
        write_csv(SHARED_BENIGN, BENIGN_HEADER, [[a, p, c] for a, p, c in DEFAULT_BENIGN])
    return SHARED_BENIGN


def load_shared_benign():
    """Return the catalog as a list of mutable [human_agreed, pattern, count] rows (order preserved)."""
    seed_shared_benign()
    _h, rows = read_csv(SHARED_BENIGN)
    out = []
    for r in rows:
        r = (list(r) + ["", "", "0"])[:3]
        out.append([r[0].strip(), r[1], r[2]])
    return out


def save_shared_benign(rows):
    write_csv(SHARED_BENIGN, BENIGN_HEADER, rows)


# Normalise an error line into a mod-agnostic signature so the same message shares ONE catalog row
# across mods/files: drop the [time][src] prefix, mask filenames / quoted values / mod tokens /
# standalone numbers. '\b\d+\b' leaves alphanumerics like 'utf8' intact.
_BRACKETS = re.compile(r"^\s*(?:\[[^\]]*\]\s*)+:?\s*")
_FILE = re.compile(r"[\w./\\-]+\.(?:txt|yml|yaml|gui|dds|mod|json|csv|lua|png|tga)\b", re.I)


def normalize_error(line, mod_tokens=()):
    s = _BRACKETS.sub("", line)
    s = _FILE.sub("<FILE>", s)
    s = re.sub(r'"[^"]*"', '"<X>"', s)
    s = re.sub(r"'[^']*'", "'<X>'", s)
    for t in sorted((t for t in mod_tokens if t), key=len, reverse=True):
        s = s.replace(t, "<TOKEN>")
    s = re.sub(r"\b\d+\b", "#", s)
    return re.sub(r"\s+", " ", s).strip()
