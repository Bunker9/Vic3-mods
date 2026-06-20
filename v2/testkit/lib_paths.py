#!/usr/bin/env python3
"""Shared utilities for v2 testbook checks (self-contained — no v1 testkit imports).

Ported from testkit/checks/utils.py on 2026-06-18 as part of the v2-harden
"make v2 self-contained" task (item b). v1 keeps its own copy; v2 owns this one.
"""
import os


def resolve_logs_dir():
    """Find the Victoria 3 logs directory, handling OneDrive-redirected Documents."""
    up = os.environ.get("USERPROFILE", "")
    for base in (os.path.join(up, "OneDrive", "Dokumen"),
                 os.path.join(up, "OneDrive", "Documents"),
                 os.path.join(up, "Documents")):
        d = os.path.join(base, "Paradox Interactive", "Victoria 3", "logs")
        if os.path.isdir(d):
            return d
    return None
