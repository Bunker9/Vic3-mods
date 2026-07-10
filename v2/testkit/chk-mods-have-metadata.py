#!/usr/bin/env python3
"""
Repo-level guard: every mod folder MUST carry .metadata/metadata.json.

WHY (2026-07-10 release scrub): chk_structure.py already FAILS a mod whose
metadata is missing, but the CI workflow loop only invokes it on folders that
HAVE .metadata/metadata.json - so a mod that accidentally lost its metadata is
silently skipped and ships broken (the game will not load it). This script
closes that hole: run it once per PR against the repo ROOT; it fails if any
top-level folder looks like a mod (contains common/ events/ localization/
map_data/ or gfx/) but has no .metadata/metadata.json.

Usage:
    python chk-mods-have-metadata.py <repo-root>

CI wiring (one-line UI edit to .github/workflows/static-checks.yml, since the
push PAT deliberately lacks workflow scope):
    python _harness/v2/testkit/chk-mods-have-metadata.py .
"""
import sys, os

# folders at repo root that are never mods
IGNORE = {".git", ".github", ".vscode", ".claude", ".idea", "_harness", "__pycache__"}
# a folder containing any of these is mod content and therefore needs metadata
MOD_MARKERS = {"common", "events", "localization", "map_data", "gfx"}


def main(root):
    bad = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if not os.path.isdir(p) or name in IGNORE:
            continue
        has_meta = os.path.isfile(os.path.join(p, ".metadata", "metadata.json"))
        looks_mod = any(os.path.isdir(os.path.join(p, m)) for m in MOD_MARKERS)
        if looks_mod and not has_meta:
            bad.append(name)
        elif has_meta or looks_mod:
            print(f"  [OK ] {name}")
    if bad:
        for name in bad:
            print(f"  [FAIL] {name}: mod content present but .metadata/metadata.json MISSING")
        print(f"---- {len(bad)} mod folder(s) without metadata ----")
        return 1
    print("---- all mod folders carry metadata ----")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
