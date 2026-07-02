#!/usr/bin/env python3
"""ext-diag-eval.py — Logtriage Set-3 evaluator: run the diag_literals rules over a TARGET's metrics.csv ->
<target>/diag_fired.csv (the rows whose condition is TRUE and status != ignore). TARGET (arg1) = a MOD_NAME
or `_global`. The rules CSV is SWAPPABLE DATA (--literals PATH; default = the copy run-log-diag seeded at
log-CURR ROOT) — point it at another game's / an experimental rules file and the engine works unchanged
(UAT LT-06: reusable across literal-CSV versions and future PDX games). Standalone; run-log-diag invokes."""
import os
import sys
import argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "Framework-common"))
sys.path.insert(0, HERE)
import lib_io, lib_paths, lib_config, lib_diag

CFG = lib_config.load_framework_config(HERE, "config_logtriage.toml")
ROOT = os.path.join(lib_paths.GAME_ROOT, "log-CURR")
COLS = ["id", "text", "condition", "logical_reasoning", "user_comments", "status"]


def main():
    p = argparse.ArgumentParser(description="Set3: evaluate diag_literals rules over a target's metrics.")
    p.add_argument("target", metavar="TARGET", help="MOD_NAME or _global (a subdir of log-CURR/)")
    p.add_argument("--literals", default=None,
                   help="rules CSV (default: the diag_literals.csv seeded at log-CURR ROOT) — swappable per game/version")
    a = p.parse_args()
    tdir = os.path.join(ROOT, a.target)
    _h, mrows = lib_io.read_csv(os.path.join(tdir, CFG["outputs"]["metrics"]))
    if _h is None:
        sys.exit(f"ext-diag-eval: no metrics.csv for {a.target} — run run-log-aggr (mods) / aggr-log-smoke (_global) first")
    metrics = {k: v for k, v in mrows}
    lit_path = a.literals or os.path.join(ROOT, CFG["diag"]["root"])
    literals = lib_io.read_csv_dicts(lit_path)
    if not literals:
        sys.exit(f"ext-diag-eval: no rules at {lit_path} — run run-log-diag (seeds it) or pass --literals")
    fired = lib_diag.fired(metrics, literals)
    lib_io.write_csv(os.path.join(tdir, CFG["outputs"]["fired"]), COLS,
                     [[r.get(c, "") for c in COLS] for r in fired])
    print(f"  [diag-eval] {a.target}: {len(fired)}/{len(literals)} rules fired (rules: {os.path.basename(lit_path)})")


if __name__ == "__main__":
    main()
