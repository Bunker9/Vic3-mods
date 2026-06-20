#!/usr/bin/env bash
# One-click v2 testbook report (the ACTIVE engine). Pass a mod name to limit to one mod
# (e.g. ./run.sh Top40EcoBoostMod), or --open to open the report in the browser.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$DIR/run_v2.py" "$@"
echo
echo "Done. Refresh MAIN-<branch>-testing.html (F5), or re-run with --open."
