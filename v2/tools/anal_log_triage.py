#!/usr/bin/env python3
r"""
anal_log_triage.py — stage 5 of the triage job. Analyse the matched log lines into diagnostics.

Reads matched_loglines.csv + the key lists and produces:
  - markers_status.csv  (dbg_id, text, file_id, line_no, fired[Y/N], hits) — fired-vs-unfired:
    a defined debug marker that never appears = that effect/decision never ran. A marker firing a
    huge number of times is flagged as a possible re-fire loop.
  - diagnostics.md      — real errors, plus the SHARED benign-catalog reconciliation.

Benign handling (shared, human-curated catalog = lib_triage.SHARED_BENIGN, outside all mods):
each distinct error line is normalised to a mod-agnostic signature and matched against the catalog.
  - human_agreed = Y  -> truly benign, suppressed.
  - human_agreed = N  -> NOT benign: reported every run as a "tracked error".
  - blank / new       -> unreviewed: added to the catalog and reported as a "new benign error" until
                         the human flags Y/N.
Ends with TWO summary lines: new/unreviewed benign patterns, and tracked (N) patterns.

Standardized args (see lib_triage): arg1=MOD_NAME (stage 4 output must exist).
Usage: python anal_log_triage.py NoUSChickenMod
"""
from collections import Counter
import lib_triage as L

REFIRE_FLAG = 100   # marker hit count above which we suspect a re-fire loop


def _examples(counter, n=4, width=40):
    out = []
    for pat, c in counter.most_common(n):
        label = pat if len(pat) <= width else pat[:width] + ".."
        out.append(f"'{label}({c})'")
    extra = ",..." if len(counter) > n else ""
    return ",".join(out) + extra


def main(args):
    _h, matches = L.read_csv(L.out_path(args.mod_name, "matched_loglines.csv"))
    _h, dbgs = L.read_csv(L.out_path(args.mod_name, "list_debug_lines.csv"))
    _h, kws = L.read_csv(L.out_path(args.mod_name, "list_kw.csv"))
    _h, files = L.read_csv(L.out_path(args.mod_name, "list_files.csv"))

    # cols: log_file(0) log_line_no(1) match_type(2) match_id(3) matched_value(4) severity(5) log_text(6)
    dbg_hits = Counter(int(r[3]) for r in matches if r[2] == "dbg")
    uniq_lines = {(r[0], r[1]) for r in matches}

    # --- markers_status.csv -------------------------------------------------
    mrows = []
    for r in dbgs:   # dbg_id, text, file_id, line_no
        n = dbg_hits.get(int(r[0]), 0)
        mrows.append([int(r[0]), r[1], r[2], r[3], "Y" if n else "N", n])
    L.write_csv(L.out_path(args.mod_name, "markers_status.csv"),
                ["dbg_id", "text", "file_id", "line_no", "fired", "hits"], mrows)
    fired = sum(1 for m in mrows if m[4] == "Y")
    unfired = [m for m in mrows if m[4] == "N"]
    refiring = [m for m in mrows if m[5] >= REFIRE_FLAG]

    # --- benign reconciliation over DISTINCT error lines --------------------
    err_map = {(r[0], r[1]): r[6] for r in matches if r[5] == "error"}   # de-dupe by log position
    tokens = [r[1] for r in kws] + [r[2] for r in files]                 # mask kw + basenames
    catalog = L.load_shared_benign()                                    # [[agreed, pattern, count], ...]

    def classify(norm):
        for row in catalog:
            if row[1] and row[1].lower() in norm.lower():
                return row
        return None

    run_counts = {}                 # id(row) -> occurrences this run
    new_counts = Counter()          # new signature -> occurrences
    suppressed = tracked = 0
    tracked_pat = Counter()         # N patterns seen this run
    pending_pat = Counter()         # blank patterns seen this run
    real_error_texts = set()        # tracked(N) + pending(blank) -> surfaced in detail
    for text in err_map.values():
        norm = L.normalize_error(text, tokens)
        row = classify(norm)
        if row is None:
            new_counts[norm] += 1
            real_error_texts.add(text)
            continue
        run_counts[id(row)] = run_counts.get(id(row), 0) + 1
        agreed = row[0].upper()
        if agreed == "Y":
            suppressed += 1
        elif agreed == "N":
            tracked += 1
            tracked_pat[row[1]] += 1
            real_error_texts.add(text)
        else:
            pending_pat[row[1]] += 1
            real_error_texts.add(text)

    # update counts (this run) for rows seen; append new signatures as blank/unreviewed rows.
    for row in catalog:
        if id(row) in run_counts:
            row[2] = str(run_counts[id(row)])
    for sig, c in new_counts.items():
        catalog.append(["", sig, str(c)])
    L.save_shared_benign(catalog)

    # new/unreviewed = freshly added + already-in-catalog-but-still-blank seen this run
    new_pending = Counter()
    new_pending.update(new_counts)
    new_pending.update(pending_pat)

    # --- diagnostics.md -----------------------------------------------------
    md = [f"# Log triage — {args.mod_name}", ""]
    md.append(f"- matched log lines (unique): **{len(uniq_lines)}** ({len(matches)} match rows)")
    md.append(f"- debug markers fired: **{fired}/{len(mrows)}**")
    md.append(f"- error lines surfaced: **{len(real_error_texts)}** "
              f"(suppressed {suppressed} agreed-benign)")
    if refiring:
        md.append(f"- ⚠ markers firing ≥{REFIRE_FLAG}× (possible re-fire loop): **{len(refiring)}**")
    md.append("")

    md.append("## Markers fired vs unfired")
    md.append("")
    md.append("| fired | hits | marker | file_id:line |")
    md.append("|:--:|--:|---|---|")
    for did, text, fid, lno, f, n in mrows:
        flag = "  ⚠re-fire?" if n >= REFIRE_FLAG else ""
        md.append(f"| {f} | {n}{flag} | {text} | {fid}:{lno} |")
    if unfired:
        md.append("")
        md.append("> UNFIRED markers = that effect/decision never ran this session:")
        for m in unfired:
            md.append(f"> - `{m[1]}`")
    if refiring:
        md.append("")
        md.append(f"> RE-FIRE WATCH (≥{REFIRE_FLAG} hits) — check for a missing once-only guard / "
                  f"already-active gate:")
        for m in refiring:
            md.append(f"> - `{m[1]}` — {m[5]} hits")
    md.append("")

    md.append("## Error lines (agreed-benign suppressed)")
    md.append("")
    if real_error_texts:
        for e in sorted(real_error_texts):
            md.append(f"- `{e}`")
    else:
        md.append("_None._")
    md.append("")

    md.append("## Benign catalog reconciliation")
    md.append("")
    md.append(f"- new/unreviewed benign patterns: **{len(new_pending)}** "
              "(added to the shared benign.csv → flag human_agreed Y/N)")
    md.append(f"- tracked errors (human_agreed=N, not benign): **{len(tracked_pat)}**")
    md.append("")

    verdict = "FAIL" if tracked_pat else ("WARN" if (new_pending or unfired or refiring) else "PASS")
    md.append(f"## Verdict: **{verdict}**")
    md.append("")

    out = L.out_path(args.mod_name, "diagnostics.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # --- console: the two reconciliation lines + verdict --------------------
    print(f"  [5] diagnostics.md ({verdict}): markers {fired}/{len(mrows)} fired"
          f"{' (' + str(len(refiring)) + ' re-firing)' if refiring else ''} -> {out}")
    if new_pending:
        print(f"      {len(new_pending)} new benign errors like {_examples(new_pending)}")
    if tracked_pat:
        print(f"      {len(tracked_pat)} existing tracked errors like {_examples(tracked_pat)}")
    return out


if __name__ == "__main__":
    main(L.parse_args("Analyse matched log lines into diagnostics (stage 5)."))
