#!/usr/bin/env python3
"""Shared utilities for testbook checks (log_triage, timeline, etc.)."""
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
