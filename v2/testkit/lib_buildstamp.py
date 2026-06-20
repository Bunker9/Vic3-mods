#!/usr/bin/env python3
"""
Build-stamp helper for the v2 report header (self-contained).

PORTED into v2 on 2026-06-18 from testkit/render_html.read_build_stamp (v2-harden item b,
"make v2 self-contained" — removes the last import of the v1 testkit from run_v2.py).
"""
import os, re

VTEST_RX = re.compile(r"VTEST_BUILD\s+(.+?)\s*$")

# this file: .../testbook/v2/testkit/lib_buildstamp.py
# mod1 is a sibling of testbook under the container root -> 3 dirnames up, then mod1/...
_MOD1 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "..", "mod1"))


def read_build_stamp(logs_dir):
    """The loaded-build label for the report header.
    Primary: the versiontest popup writes `VTEST_BUILD <stamp>` to debug.log -> the bundle
    that ACTUALLY loaded this run. Fallback: the source stamp in the versiontest loc file
    (may be ahead of what loaded). Returns (stamp, source) where source in {log, source}."""
    path = os.path.join(logs_dir, "debug.log") if logs_dir else None
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for ln in f:
                m = VTEST_RX.search(ln)
                if m:
                    return m.group(1).strip(), "log"
    loc = os.path.join(_MOD1, "versiontestMod", "localization", "english",
                       "versiontest_l_english.yml")
    try:
        with open(loc, encoding="utf-8-sig", errors="replace") as f:
            for ln in f:
                m = re.search(r'versiontest\.1\.d:0\s*"(.+?)"', ln)
                if m:
                    return m.group(1).strip(), "source"
    except OSError:
        pass
    return None, None
