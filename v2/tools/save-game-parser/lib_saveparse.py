#!/usr/bin/env python3
r"""lib_saveparse.py — shared helpers for the per-mod SAVE-game parser / fingerprint-verifier.

Sibling of tools/lib_triage.py, but for the SAVE side: instead of joining a mod's key lists against
the game LOGS, it joins them (+ the mod's deliberate <abbr>_fingerprint_ markers) against a
decompressed Victoria 3 save (.v3), which DURABLY persists variables / flags / modifiers, each
attributed to the exact object that carries it. Vic3 stores a variable in the save as `flag=<name>`
(there is NO set_*_flag effect in Vic3 — see docs/vic3-token-gotchas.md); an active modifier as
`modifier=<name>` with a `start_date`.

NOT run directly. Imported by run_save_parser.py and the sub-scripts (aggr_*/anal_*).

Standardized arg contract (same family as lib_triage):
  arg1  MOD_NAME  (required)  -> output namespace tools/save-game-parser/<MOD_NAME>/;
                                 join keys come from tools/<MOD_NAME>/list_kw.csv (built by the triage job)
  --save PATH                 -> override the save file (else newest *.v3 in the Vic3 'save games' dir)
  --prefix P                  -> override the auto-derived mod abbreviation
  --rerun                     -> force re-scan (else reuse the matched CSV if present)
"""
import os, sys, csv, re, argparse, io, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))            # testbook/v2/tools/save-game-parser
TOOLS_ROOT = os.path.dirname(HERE)                           # testbook/v2/tools  (owns <mod>/list_kw.csv)

FP_INFIX = "_fingerprint_"   # the deliberate save-fingerprint marker infix (DEV-RULES)


# ---- standardized arg contract ----------------------------------------------
def build_parser(desc):
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("mod_name", metavar="MOD_NAME",
                   help="mod basename; output namespace tools/save-game-parser/<MOD_NAME>/")
    p.add_argument("--save", default=None, help="override save file (.v3); else newest in 'save games'")
    p.add_argument("--prefix", default=None, help="override the auto-derived mod abbreviation")
    p.add_argument("--rerun", action="store_true", help="force re-scan (else reuse matched CSV)")
    return p


def parse_args(desc):
    return build_parser(desc).parse_args()


# ---- paths / IO -------------------------------------------------------------
def out_dir(mod_name, create=True):
    d = os.path.join(HERE, mod_name)
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def out_path(mod_name, filename):
    return os.path.join(out_dir(mod_name), filename)


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def read_csv(path):
    if not os.path.exists(path):
        return None, []
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = list(csv.reader(f))
    return (r[0], r[1:]) if r else (None, [])


# ---- join keys (from the triage job — single source of truth) ---------------
def load_kw(mod_name):
    """Return [(kw, kind), ...] from tools/<MOD_NAME>/list_kw.csv (built by run_log_triage)."""
    p = os.path.join(TOOLS_ROOT, mod_name, "list_kw.csv")
    header, rows = read_csv(p)
    if header is None:
        raise SystemExit(
            f"save-parser: no keyword list at {p}\n"
            f"  Build it first with the triage job:\n"
            f'    python {os.path.join(TOOLS_ROOT, "run_log_triage.py")} {mod_name} "<path-to-mod>" --rerun')
    ik = {c: i for i, c in enumerate(header)}
    return [(row[ik["kw"]], row[ik.get("kind", 1)] if len(row) > 1 else "") for row in rows if row]


def mod_abbr(kws, override=None):
    """Dominant '<abbr>_' prefix across the kw list (e.g. nous / zw / stdinnv)."""
    if override:
        return override
    from collections import Counter
    tally = Counter()
    for kw, _kind in kws:
        m = re.match(r"^([a-z]{2,8})_", kw)
        if m:
            tally[m.group(1)] += 1
    return tally.most_common(1)[0][0] if tally else None


# ---- save resolution + reading ----------------------------------------------
def resolve_save(override=None):
    """The save file. Honors --save; else newest *.v3 in <Documents>/Paradox Interactive/Victoria 3/save games."""
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
    sg = os.path.join(docs, "Paradox Interactive", "Victoria 3", "save games")
    if not os.path.isdir(sg):
        raise SystemExit(f"save-parser: save-games dir not found: {sg}  (pass --save <file.v3>)")
    v3 = [os.path.join(sg, f) for f in os.listdir(sg) if f.lower().endswith(".v3")]
    if not v3:
        raise SystemExit(f"save-parser: no *.v3 in {sg}  (pass --save <file.v3>)")
    return max(v3, key=os.path.getmtime)


def iter_save_lines(path):
    """Yield text lines from a Vic3 save. Handles a plaintext (decompressed/melted) save AND the
    normal zip form (.v3 = a zip whose 'gamestate' member holds the text)."""
    with open(path, "rb") as fb:
        head = fb.read(4)
    if head[:2] == b"PK":                       # zip container -> read the 'gamestate' member
        with zipfile.ZipFile(path) as z:
            member = "gamestate" if "gamestate" in z.namelist() else z.namelist()[-1]
            with z.open(member) as raw:
                for line in io.TextIOWrapper(raw, encoding="utf-8", errors="replace"):
                    yield line.rstrip("\n")
    else:                                       # plaintext save (header line is 'SAV01...')
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                yield line.rstrip("\n")


# ---- the scan ---------------------------------------------------------------
# A persisted hit is the VALUE side of `key=value` (flag=<var>, modifier=<mod>, variable=<var>, ...).
_ASSIGN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([A-Za-z_][\w:.\-]*)")
_OPENER = re.compile(r"^\s*([\w:.\-]+)=\{")
_IDENTITY = re.compile(r"\bidentity=(-?\d+)")
_VALUE = re.compile(r"\bvalue=([A-Za-z0-9_.\-]+)")
_TYPE = re.compile(r"\btype=([A-Za-z_]+)")
_STARTDATE = re.compile(r"\bstart_date=([\d.]+)")

# save_token -> fingerprint type reported in the CSV
_TOKEN_KIND = {"flag": "variable", "variable": "variable", "modifier": "modifier",
               "global_variable": "global_variable"}


def scan(path, literal_terms, fp_re):
    """Single streaming pass. Returns a list of match dicts. Each match = one `key=<term>` where
    <term> is in literal_terms OR matches fp_re. Tracks a dotted breadcrumb of enclosing NAMED blocks,
    and peeks the next few lines for a variable's value/type and a modifier's start_date."""
    out = []
    pending = []                 # [(record, lines_left)] awaiting value/type/date from following lines
    depth = 0
    named = []                   # (open_depth, key) for named block openers only -> the breadcrumb

    for ln, line in enumerate(iter_save_lines(path), 1):
        # 1) fill any pending records from this line (value / type / date sit a few lines below)
        if pending:
            still = []
            for rec, left in pending:
                if rec["fp_type"] == "modifier":
                    m = _STARTDATE.search(line)
                    if m and not rec["date"]:
                        rec["date"] = m.group(1)
                else:
                    mt = _TYPE.search(line)
                    if mt and not rec["vtype"]:
                        rec["vtype"] = mt.group(1)
                    mv = _IDENTITY.search(line) or _VALUE.search(line)
                    if mv and not rec["value"]:
                        rec["value"] = mv.group(1)
                left -= 1
                if left > 0:
                    still.append((rec, left))
            pending = still

        # 2) match key=term assignments on this line
        breadcrumb = ".".join(k for _d, k in named)
        section = named[0][1] if named else "(header)"
        for m in _ASSIGN.finditer(line):
            tok, val = m.group(1), m.group(2)
            if val in literal_terms or (fp_re and fp_re.fullmatch(val)):
                rec = {"term": val, "save_token": tok,
                       "fp_type": _TOKEN_KIND.get(tok, "other"),
                       "section": section, "doc_path": breadcrumb,
                       "value": "", "vtype": "", "date": "", "line_no": ln,
                       "sample": line.strip()[:120]}
                out.append(rec)
                pending.append((rec, 6))      # look ~6 lines ahead for value/type/start_date

        # 3) update the structural breadcrumb AFTER attributing this line to its parent
        opener = _OPENER.match(line)
        opens, closes = line.count("{"), line.count("}")
        if opener and opens > closes:
            named.append((depth, opener.group(1)))
        depth += opens - closes
        if depth < 0:
            depth = 0
        while named and named[-1][0] >= depth:
            named.pop()

    return out
