#!/usr/bin/env python3
r"""
aggr_log_matches.py — stage 4 of the triage job. Join the game logs against the mod's key lists.

Scans error.log + debug.log + game.log line-by-line and tests each line against the three join-key
sets built in stages 1-3: file basenames, mod keywords, and debug-marker texts. Emits one row per
match.

Writes testbook/v2/tools/<MOD_NAME>/matched_loglines.csv:
  log_file, log_line_no, match_type(file|kw|dbg), match_id, matched_value, severity, log_text

severity is by source log (error/debug/info). Benign classification is done downstream in
anal_log_triage against the SHARED, human-curated benign catalog (lib_triage.SHARED_BENIGN).

Standardized args (see lib_triage): arg1=MOD_NAME (lists must already exist); --logs overrides dir.
Usage: python aggr_log_matches.py NoUSChickenMod [--logs DIR]
"""
import os, re
import lib_triage as L

LOG_FILES = [("error.log", "error"), ("debug.log", "debug"), ("game.log", "info")]


def _need(mod_name, fname):
    h, rows = L.read_csv(L.out_path(mod_name, fname))
    if h is None:
        raise SystemExit(f"aggr_log_matches: missing {fname}; build the lists first (--rerun + MOD_PATH).")
    return rows


def main(args):
    files = _need(args.mod_name, "list_files.csv")        # file_id, rel_path, basename
    kws = _need(args.mod_name, "list_kw.csv")             # kw_id, kw, kind
    dbgs = _need(args.mod_name, "list_debug_lines.csv")   # dbg_id, text, file_id, line_no

    # Precompile matchers. Keywords use token boundaries (so 'nous_war_play' won't hit
    # 'nous_war_play_desc'); basenames + debug texts are distinctive enough for substring.
    file_keys = [(int(r[0]), r[2]) for r in files]
    kw_keys = [(int(r[0]), r[1], re.compile(r"(?<![A-Za-z0-9_])" + re.escape(r[1]) + r"(?![A-Za-z0-9_])"))
               for r in kws]
    dbg_keys = [(int(r[0]), r[1]) for r in dbgs]

    logs_dir = L.resolve_logs_dir(args.logs)
    rows = []
    for fname, severity in LOG_FILES:
        path = os.path.join(logs_dir, fname)
        if not os.path.exists(path):
            continue
        for ln, line in enumerate(L.read_text_lines(path), 1):
            for dbg_id, text in dbg_keys:
                if text and text in line:
                    rows.append([fname, ln, "dbg", dbg_id, text, severity, line])
            for kw_id, kw, rx in kw_keys:
                if rx.search(line):
                    rows.append([fname, ln, "kw", kw_id, kw, severity, line])
            for file_id, base in file_keys:
                if base in line:
                    rows.append([fname, ln, "file", file_id, base, severity, line])

    out = L.out_path(args.mod_name, "matched_loglines.csv")
    L.write_csv(out, ["log_file", "log_line_no", "match_type", "match_id", "matched_value",
                      "severity", "log_text"], rows)
    print(f"  [4] matched_loglines.csv: {len(rows)} matches across {logs_dir} -> {out}")
    return out


if __name__ == "__main__":
    main(L.parse_args("Join game logs against mod key lists (stage 4)."))
