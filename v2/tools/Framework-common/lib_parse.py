#!/usr/bin/env python3
"""lib_parse — shared parse primitives for THE debug framework: prefix detection, fixed-point value
decode, Vic3 save iteration + structural breadcrumb walk, and error-line normalization. Genuine
parse-logic regexes live HERE (not in config). Cohesive lib — may exceed the 50-line glue target."""
import re
import io
import zipfile
from collections import Counter

_IDENT = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")
_PREFIX = re.compile(r"^([a-z]{2,8})_")


def detect_prefix(tokens, override=None, stopwords=()):
    """Dominant '<short>_' prefix across identifier tokens (e.g. 'nous'), IGNORING common vanilla command/scope
    prefixes in stopwords — else 'add'/'set'/'building' outrank a mod's real tag (caught on MyDiploPlay/eco
    2026-06-30). override always wins; stopwords come from config (mod-agnostic, tunable)."""
    if override:
        return override
    stop = set(stopwords)
    tally = Counter()
    for tok in tokens:
        m = _PREFIX.match(tok)
        if m and m.group(1) not in stop:
            tally[m.group(1)] += 1
    return tally.most_common(1)[0][0] if tally else None


def iter_identifiers(lines):
    """Yield every snake_case identifier across an iterable of text lines."""
    for line in lines:
        yield from _IDENT.findall(line)


def decode_value(raw, factor):
    """Decode a save numeric var: Vic3 stores fixed-point as int(value*factor); factor comes from config."""
    try:
        return int(raw) / factor
    except (TypeError, ValueError):
        return raw


# ---- Vic3 save reading + structural walk ------------------------------------
def iter_save_lines(path):
    """Yield text lines from a Vic3 save: zip (.v3 'gamestate' member) OR plaintext (melted)."""
    with open(path, "rb") as fb:
        head = fb.read(2)
    if head == b"PK":
        with zipfile.ZipFile(path) as z:
            member = "gamestate" if "gamestate" in z.namelist() else z.namelist()[-1]
            with z.open(member) as raw:
                for line in io.TextIOWrapper(raw, encoding="utf-8", errors="replace"):
                    yield line.rstrip("\n")
    else:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                yield line.rstrip("\n")


_OPENER = re.compile(r"^\s*([\w:.\-]+)=\{")


def iter_save_blocks(path):
    """Yield (line_no, line, doc_path, section) for each save line, tracking the dotted breadcrumb of
    enclosing NAMED blocks — the navigation path the SaveParse matcher attributes each hit to."""
    depth = 0
    named = []   # (open_depth, key) for named-block openers only
    for ln, line in enumerate(iter_save_lines(path), 1):
        breadcrumb = ".".join(k for _d, k in named)
        section = named[0][1] if named else "(header)"
        yield ln, line, breadcrumb, section
        opener = _OPENER.match(line)
        opens, closes = line.count("{"), line.count("}")
        if opener and opens > closes:
            named.append((depth, opener.group(1)))
        depth += opens - closes
        if depth < 0:
            depth = 0
        while named and named[-1][0] >= depth:
            named.pop()


# key=value assignment + the few-line lookahead for a var's value/type and a modifier's start_date.
_ASSIGN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([A-Za-z_][\w:.\-]*)")
_IDENTITY = re.compile(r"\bidentity=(-?\d+)")
_VALUE = re.compile(r"\bvalue=([A-Za-z0-9_.\-]+)")
_TYPE = re.compile(r"\btype=([A-Za-z_]+)")
_STARTDATE = re.compile(r"\bstart_date=([\d.]+)")
_TOKEN_KIND = {"flag": "variable", "variable": "variable", "modifier": "modifier",
               "global_variable": "global_variable"}


def scan(path, literal_terms, fp_re, lookahead=6):
    """SaveParse matcher: one streaming pass; record every `key=<term>` where <term> is in literal_terms OR
    matches fp_re. Each match carries the enclosing breadcrumb (via iter_save_blocks) + a few-line lookahead
    for a variable's value/type and a modifier's start_date."""
    out, pending = [], []
    for ln, line, doc_path, section in iter_save_blocks(path):
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
                if left - 1 > 0:
                    still.append((rec, left - 1))
            pending = still
        for m in _ASSIGN.finditer(line):
            tok, val = m.group(1), m.group(2)
            if val in literal_terms or (fp_re and fp_re.fullmatch(val)):
                rec = {"term": val, "save_token": tok, "fp_type": _TOKEN_KIND.get(tok, "other"),
                       "section": section, "doc_path": doc_path, "value": "", "vtype": "",
                       "date": "", "line_no": ln, "sample": line.strip()[:120]}
                out.append(rec)
                pending.append((rec, lookahead))
    return out


def scan_kinds(path, lookahead=6):
    """SORT-not-FILTER save dump (Set-1 common): one streaming pass; record EVERY `flag=` / `variable=` /
    `modifier=` / `global_variable=` assignment regardless of the value (no mod filter — attribution is a
    later per-mod join over the resulting raw pool). Same record shape + value/date lookahead as scan()."""
    out, pending = [], []
    for ln, line, doc_path, section in iter_save_blocks(path):
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
                if left - 1 > 0:
                    still.append((rec, left - 1))
            pending = still
        for m in _ASSIGN.finditer(line):
            tok, val = m.group(1), m.group(2)
            if tok in _TOKEN_KIND:
                rec = {"term": val, "save_token": tok, "fp_type": _TOKEN_KIND[tok],
                       "section": section, "doc_path": doc_path, "value": "", "vtype": "",
                       "date": "", "line_no": ln, "sample": line.strip()[:120]}
                out.append(rec)
                pending.append((rec, lookahead))
    return out


# ---- error-line normalization (logtriage) -----------------------------------
_BRACKETS = re.compile(r"^\s*(?:\[[^\]]*\]\s*)+:?\s*")
_FILE = re.compile(r"[\w./\\-]+\.(?:txt|yml|yaml|gui|dds|mod|json|csv|lua|png|tga)\b", re.I)


def normalize_error(line, mod_tokens=()):
    """Mod-agnostic error signature: drop [time][src] prefix, mask files / quotes / mod-tokens / numbers."""
    s = _BRACKETS.sub("", line)
    s = _FILE.sub("<FILE>", s)
    s = re.sub(r'"[^"]*"', '"<X>"', s)
    s = re.sub(r"'[^']*'", "'<X>'", s)
    for t in sorted((t for t in mod_tokens if t), key=len, reverse=True):
        s = s.replace(t, "<TOKEN>")
    s = re.sub(r"\b\d+\b", "#", s)
    return re.sub(r"\s+", " ", s).strip()
