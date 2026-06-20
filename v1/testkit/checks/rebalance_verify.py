#!/usr/bin/env python3
r"""
rebalance_verify.py — rough debug-log parser + mod conflict checker for 2026-06-15 rebalance.

Not production-quality; just enough to catch obvious issues:
1. Scan error.log for mdp.3 / soft-remove / East Africa warnings
2. Check for file-name collisions across mods (same filename in different mods)
3. Assert key rebalance changes are present in history files

Usage: python rebalance_verify.py <error_log_path> [mod1_path]
Default mod1_path: auto-derived relative to this script (../../../mod1)
"""
import os, sys, re, json
from pathlib import Path
from collections import defaultdict

def parse_error_log(log_path):
    """Extract lines related to rebalance (mdp.3, soft-remove, East Africa)."""
    issues = []
    key_phrases = [
        "mdp.3", "mdp_annexer", "mdp_subject",  # subject annexation
        "mdp.1", "on_monthly_pulse expander",    # monthly blob
        "soft.?remove", "BIC", "PRU", "EGY", "SAR", "SWE",  # soft-remove tags
        "STATE_OROMIA", "STATE_ERITREA", "cotton_plantation",  # East Africa
        "oil_rig", "rubber_plantation",  # oil/rubber
    ]

    if not os.path.exists(log_path):
        return [f"ERROR: log file not found: {log_path}"]

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f, 1):
            # Look for key phrases (case-insensitive)
            if any(re.search(phrase, line, re.IGNORECASE) for phrase in key_phrases):
                # Extract just the relevant bit
                if "ERROR" in line.upper() or "FATAL" in line.upper():
                    issues.append(f"[{i}] ERROR: {line.strip()[:120]}")
                elif "Unknown effect" in line or "Wrong scope" in line:
                    issues.append(f"[{i}] PARSE ERROR: {line.strip()[:120]}")

    return issues or ["✓ No obvious rebalance-related errors in log"]

def check_mod_conflicts(mod1_path):
    """Check for duplicate filenames across different mods."""
    if not os.path.isdir(mod1_path):
        return [f"ERROR: mod1 path not found: {mod1_path}"]

    mod_files = defaultdict(lambda: defaultdict(list))  # mod -> (ext -> [files])
    mods = [d for d in os.listdir(mod1_path)
            if os.path.isdir(os.path.join(mod1_path, d)) and not d.startswith('.')]

    for mod in mods:
        mod_path = os.path.join(mod1_path, mod)
        for root, dirs, files in os.walk(mod_path):
            for f in files:
                # Record filename and relative path
                rel_path = os.path.relpath(os.path.join(root, f), mod_path)
                mod_files[mod][f].append(rel_path)

    # Find collisions
    collisions = []
    all_filenames = defaultdict(list)
    for mod, files_dict in mod_files.items():
        for fname, paths in files_dict.items():
            all_filenames[fname].append((mod, paths[0]))

    for fname, mod_list in all_filenames.items():
        if len(mod_list) > 1:
            # Collision detected
            mods_involved = ", ".join(m[0] for m in mod_list)
            paths = " | ".join(f"{m[0]}:{m[1]}" for m in mod_list)
            collisions.append(f"COLLISION: {fname} → {paths}")

    return collisions or ["✓ No file-name collisions across mods"]

def check_history_files(mod1_path):
    """Spot-check that rebalance history files exist and are non-empty."""
    checks = []
    files_to_check = [
        ("Top40EcoBoostMod/common/history/buildings/zz_eco_starters_eastafrica.txt", "East Africa override"),
        ("Top40EcoBoostMod/common/history/buildings/zz_eco_starters_oil_rubber.txt", "Oil/rubber seeding"),
        ("MyDiploPlayMod/common/history/diplomacy/zz_mdp_truces.txt", "Truces (OMA↔NEJ)"),
        ("MyDiploPlayMod/events/mdp_events.txt", "mdp.3 subject annexation"),
    ]

    for rel_path, desc in files_to_check:
        full_path = os.path.join(mod1_path, rel_path)
        if not os.path.exists(full_path):
            checks.append(f"MISSING: {desc} ({rel_path})")
        else:
            size = os.path.getsize(full_path)
            if size < 100:
                checks.append(f"EMPTY: {desc} ({size} bytes)")
            else:
                # Quick sanity check: read first few lines
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(500)
                    if "GENERATED" in content or "=" in content or "create" in content:
                        checks.append(f"✓ {desc}")
                    else:
                        checks.append(f"SUSPICIOUS: {desc} (no obvious content)")

    return checks

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUSAGE: python rebalance_verify.py <error_log_path> [mod1_path]")
        print("DEFAULT mod1_path: auto-derived relative to this script (../../../mod1)")
        sys.exit(1)

    log_path = sys.argv[1]
    _here = os.path.dirname(os.path.abspath(__file__))  # .../testbook/v1/testkit/checks
    _default_mod1 = os.path.normpath(os.path.join(_here, "..", "..", "..", "..", "mod1"))
    mod1_path = sys.argv[2] if len(sys.argv) > 2 else _default_mod1

    print("\n" + "="*70)
    print("REBALANCE VERIFICATION (rough checks)")
    print("="*70)

    print("\n1. ERROR LOG SCAN (rebalance-related):")
    print("-" * 70)
    for issue in parse_error_log(log_path):
        print(f"  {issue}")

    print("\n2. MOD FILE CONFLICTS:")
    print("-" * 70)
    for collision in check_mod_conflicts(mod1_path):
        print(f"  {collision}")

    print("\n3. REBALANCE HISTORY FILES:")
    print("-" * 70)
    for check in check_history_files(mod1_path):
        print(f"  {check}")

    print("\n" + "="*70)
    print("END REBALANCE VERIFICATION")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
