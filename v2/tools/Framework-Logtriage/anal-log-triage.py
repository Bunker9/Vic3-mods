#!/usr/bin/env python3
"""anal-log-triage.py — Logtriage analyzer: turn aggr_log_matches.csv + the data-<Mod> lists into
log-CURR/<Mod>/aggr_markers_status.csv + diagnostics.md (markers fired/unfired, benign-filtered errors, AND the
loc-for-all-kw check). Benign = the shared human-curated catalog in THIS folder (config). Cohesive analyzer
(exceeds the 50-line glue target by design). Ported from tools/anal_log_triage.py. Standalone-runnable."""
import os
import sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
import lib_args, lib_io, lib_paths, lib_config, lib_parse

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")
REFIRE = CFG["analysis"]["refire_flag"]
BENIGN = os.path.join(HERE, CFG["benign"]["file"])
BENIGN_HEADER = ["human_agreed", "pattern", "count"]


def load_benign():
    _h, rows = lib_io.read_csv(BENIGN)
    rows = [(list(r) + ["", "", "0"])[:3] for r in rows]
    if not rows:   # seed if header-only / absent
        rows = [[a, p, "0"] for a, p in CFG["benign"]["seed"]]
    return [[r[0].strip(), r[1], r[2]] for r in rows]


def _examples(counter, n=4, width=40):
    out = [f"'{(p if len(p) <= width else p[:width] + '..')}({c})'" for p, c in counter.most_common(n)]
    return ",".join(out) + (",..." if len(counter) > n else "")


def main(args):
    data = lib_paths.data_dir(args.mod_name, create=False)
    out_dir = lib_paths.run_dir("log-CURR", args.mod_name)
    _h, matches = lib_io.read_csv(os.path.join(out_dir, CFG["outputs"]["matches"]))
    _h, dbgs = lib_io.read_csv(os.path.join(data, "raw_debuglines.csv"))
    _h, kws = lib_io.read_csv(os.path.join(data, "raw_keywords.csv"))
    _h, files = lib_io.read_csv(os.path.join(data, "raw_files.csv"))
    _h, locs = lib_io.read_csv(os.path.join(data, "raw_loc.csv"))

    dbg_hits = Counter(int(r[3]) for r in matches if r[2] == "dbg")
    uniq_lines = {(r[0], r[1]) for r in matches}

    # --- markers fired/unfired -> aggr_markers_status.csv -------------------
    mrows = [[int(r[0]), r[1], r[2], r[3], "Y" if dbg_hits.get(int(r[0]), 0) else "N",
              dbg_hits.get(int(r[0]), 0)] for r in dbgs]
    lib_io.write_csv(os.path.join(out_dir, CFG["outputs"]["markers"]),
                     ["dbg_id", "text", "file_id", "line_no", "fired", "hits"], mrows)
    fired = sum(1 for m in mrows if m[4] == "Y")
    unfired = [m for m in mrows if m[4] == "N"]
    refiring = [m for m in mrows if m[5] >= REFIRE]

    # --- loc-for-all-kw (repurposed raw_loc.csv; §C.3) ----------------------
    # Advisory: a 'def' token with no matching loc key. Includes internal defs (effects/triggers/SVs) that
    # legitimately need no loc, so it is review-advisory, not a hard FAIL.
    loc_keys = {r[1] for r in locs}
    missing_loc = [r[1] for r in kws if len(r) > 2 and r[2] == "def" and r[1] not in loc_keys]

    # --- benign reconciliation over DISTINCT error lines --------------------
    err_map = {(r[0], r[1]): r[6] for r in matches if r[5] == "error"}
    tokens = [r[1] for r in kws] + [r[2] for r in files]
    catalog = load_benign()

    def classify(norm):
        for row in catalog:
            if row[1] and row[1].lower() in norm.lower():
                return row
        return None

    run_counts, new_counts = {}, Counter()
    suppressed = tracked = 0
    tracked_pat, pending_pat, real_errors = Counter(), Counter(), set()
    for text in err_map.values():
        norm = lib_parse.normalize_error(text, tokens)
        row = classify(norm)
        if row is None:
            new_counts[norm] += 1
            real_errors.add(text)
            continue
        run_counts[id(row)] = run_counts.get(id(row), 0) + 1
        agreed = row[0].upper()
        if agreed == "Y":
            suppressed += 1
        elif agreed == "N":
            tracked += 1
            tracked_pat[row[1]] += 1
            real_errors.add(text)
        else:
            pending_pat[row[1]] += 1
            real_errors.add(text)
    for row in catalog:
        if id(row) in run_counts:
            row[2] = str(run_counts[id(row)])
    for sig, c in new_counts.items():
        catalog.append(["", sig, str(c)])
    lib_io.write_csv(BENIGN, BENIGN_HEADER, catalog)
    new_pending = Counter(); new_pending.update(new_counts); new_pending.update(pending_pat)

    # --- diagnostics.md -----------------------------------------------------
    md = [f"# Log triage — {args.mod_name}", ""]
    md.append(f"- matched log lines (unique): **{len(uniq_lines)}** ({len(matches)} match rows)")
    md.append(f"- debug markers fired: **{fired}/{len(mrows)}**")
    md.append(f"- error lines surfaced: **{len(real_errors)}** (suppressed {suppressed} agreed-benign)")
    md.append(f"- loc-for-all-kw: **{len(loc_keys)}** loc keys; **{len(missing_loc)}** def-tokens without a loc (advisory)")
    if refiring:
        md.append(f"- WARN markers firing >= {REFIRE}x (possible re-fire loop): **{len(refiring)}**")
    md.append("\n## Markers fired vs unfired\n")
    md.append("| fired | hits | marker | file_id:line |")
    md.append("|:--:|--:|---|---|")
    for did, text, fid, lno, f, n in mrows:
        md.append(f"| {f} | {n}{'  (re-fire?)' if n >= REFIRE else ''} | {text} | {fid}:{lno} |")
    if unfired:
        md.append("\n> UNFIRED markers = that effect/decision never ran this session:")
        md += [f"> - `{m[1]}`" for m in unfired]
    md.append("\n## Error lines (agreed-benign suppressed)\n")
    md += ([f"- `{e}`" for e in sorted(real_errors)] or ["_None._"])
    md.append("\n## Loc-for-all-kw (advisory)\n")
    md.append(f"def-tokens with no loc entry (review; internal effects/triggers legitimately have none): "
              f"**{len(missing_loc)}**")
    md += [f"- `{k}`" for k in sorted(missing_loc)[:50]]
    md.append("\n## Benign catalog reconciliation\n")
    md.append(f"- new/unreviewed benign patterns: **{len(new_pending)}** (added to benign.csv -> flag Y/N)")
    md.append(f"- tracked errors (human_agreed=N): **{len(tracked_pat)}**")
    verdict = "FAIL" if tracked_pat else ("WARN" if (new_pending or unfired or refiring) else "PASS")
    md.append(f"\n## Verdict: **{verdict}**\n")

    out = os.path.join(out_dir, CFG["outputs"]["report"])
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"  [diagnostics] ({verdict}) markers {fired}/{len(mrows)} fired"
          f"{f' ({len(refiring)} re-firing)' if refiring else ''} -> {out}")
    if new_pending:
        print(f"      {len(new_pending)} new benign errors like {_examples(new_pending)}")
    if tracked_pat:
        print(f"      {len(tracked_pat)} tracked errors like {_examples(tracked_pat)}")
    return out


if __name__ == "__main__":
    main(lib_args.parse_args("Logtriage: analyse matched log lines into diagnostics.", logs=True))
