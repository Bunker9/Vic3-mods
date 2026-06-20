#!/usr/bin/env python3
r"""
pretest_checklist.py — rebalance pre-test checklist (runs before game launch).

Checks:
1. All rebalance history files present + non-empty
2. No mod folder/file name conflicts
3. MyDiploPlayMod events.txt contains mdp.3 (subject annexation)
4. ExpFightMod triggers commented out BIC/PRU/EGY/SAR/SWE (soft-remove)
5. Top40EcoBoostMod has oil/rubber + East Africa files
6. Error.log clear before test (optional)

Usage: python pretest_checklist.py [--clear-logs]
"""
import os, re, sys

try:                                  # Windows console is cp1252; the ticks need UTF-8
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
MOD1 = os.path.join(HERE, "..", "..", "..", "..", "mod1")
LOGS = os.path.join(HERE, "..", "..", "..", "..", "hk-config", "tools")

def check(condition, desc, fix_hint=""):
    """Print a check result."""
    status = "✓" if condition else "✗"
    print(f"  {status} {desc}")
    if not condition and fix_hint:
        print(f"    → {fix_hint}")
    return condition

def file_contains(path, pattern):
    """Check if file contains pattern (regex)."""
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            return bool(re.search(pattern, content, re.IGNORECASE))
    except:
        return False

def file_not_contains(path, pattern):
    """Check if file does NOT contain pattern."""
    if not os.path.exists(path):
        return True
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            return not bool(re.search(pattern, content))
    except:
        return True

def main():
    print("\n" + "="*70)
    print("PRE-TEST CHECKLIST (rebalance 2026-06-15)")
    print("="*70 + "\n")

    all_pass = True

    # 1. HISTORY + GENERATED FILES
    print("1. KEY FILES PRESENT:")
    present_files = {
        f"{MOD1}/Top40EcoBoostMod/common/history/buildings/zz_eco_starters_eastafrica.txt":
            "East Africa override (SHW/EGY fabric)",
        f"{MOD1}/Top40EcoBoostMod/common/scripted_effects/eco_setup_generated.txt":
            "EcoBoost 40-tag setups (generated)",
        f"{MOD1}/Top40EcoBoostMod/common/static_modifiers/eco_champ_tp_generated.txt":
            "EcoBoost 40 champ-throughput modifiers (generated)",
        f"{MOD1}/Top40EcoBoostMod/events/eco_oilrubber_events.txt":
            "Oil/rubber tech-event (ecoor.1/.2 — replaces deleted day-1 history)",
        f"{MOD1}/Top40EcoBoostMod/common/on_actions/eco_oilrubber_on_actions.txt":
            "Oil/rubber on_acquired_technology hook",
        f"{MOD1}/MyDiploPlayMod/common/history/diplomacy/zz_mdp_truces.txt":
            "Truces (region-filtered, ~30 pairs incl. OMA-NEJ/OMA-SHW)",
    }
    for path, desc in present_files.items():
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        all_pass &= check(exists and size > 100, f"{desc} (size={size})",
                         "Run the owning gen_*.py (see hk-config/scripts/MANIFEST.md)")

    # 1b. the WRONG oil/rubber day-1 history file must be GONE
    bad = f"{MOD1}/Top40EcoBoostMod/common/history/buildings/zz_eco_starters_oil_rubber.txt"
    all_pass &= check(not os.path.exists(bad),
                      "Old day-1 oil/rubber history file removed (discoverable RGOs can't build at 1836)",
                      "Delete it — oil/rubber is now tech-triggered via eco_oilrubber")

    # 2. EVENT & TRIGGER UPDATES
    print("\n2. EVENT & TRIGGER UPDATES:")
    mdp_events = f"{MOD1}/MyDiploPlayMod/events/mdp_events.txt"
    all_pass &= check(file_contains(mdp_events, r"mdp\.3.*subject.*annex"),
                     "mdp.3 event (subject annexation) present in mdp_events.txt")

    expfight_triggers = f"{MOD1}/ExpFightMod/common/scripted_triggers/expfight_triggers.txt"
    all_pass &= check(file_contains(expfight_triggers, r"#.*BIC.*PRU.*EGY.*SAR.*SWE"),
                     "ExpFightMod soft-removes (BIC/PRU/EGY/SAR/SWE commented out)")

    # 3. ON_ACTIONS
    print("\n3. ON_ACTIONS (mdp_on_actions.txt):")
    mdp_actions = f"{MOD1}/MyDiploPlayMod/common/on_actions/mdp_on_actions.txt"
    all_pass &= check(file_contains(mdp_actions, r"mdp_infamy_decay.*months = 36"),
                     "Infamy decay reduced to 36 months (was 120)",
                     "Check mdp_startup effect in mdp_on_actions.txt")
    all_pass &= check(file_contains(mdp_actions, r"NOT.*BIC.*PRU.*EGY.*SAR.*SWE"),
                     "Soft-remove guard in on_monthly_pulse (mdp.1 disabled for 5 tags)",
                     "Check on_monthly_pulse_country limit in mdp_on_actions.txt")
    all_pass &= check(file_contains(mdp_actions, r"mdp\.3.*annex"),
                     "mdp.3 trigger in on_monthly_pulse (subject annexation)")

    # 4. MOD CONFLICT CHECK (reuse conflict.py so per-mod boilerplate like CHANGELOG.md /
    #    metadata.json is excluded, and only real same-PATH overrides count as HARD)
    print("\n4. MOD CONFLICTS:")
    import conflict
    mods = [d for d in os.listdir(MOD1)
            if os.path.isdir(os.path.join(MOD1, d)) and not d.startswith('.')]
    cres = conflict.run([os.path.join(MOD1, m) for m in mods])
    all_pass &= check(cres["summary"]["hard"] == 0,
                      f"No hard path overrides across mods ({cres['summary']['soft']} soft advisory)")
    for h in cres["hard"]:
        print(f"    HARD {h['relpath']}: {h['mods']}")

    # 5. ERROR.LOG BASELINE
    print("\n5. ERROR.LOG BASELINE:")
    error_log = os.path.join(LOGS, "error.log")
    if os.path.exists(error_log):
        size = os.path.getsize(error_log)
        if size > 1000000:  # > 1MB
            all_pass &= check(False, f"error.log is large ({size/1e6:.1f}MB), clear it before test",
                             "Run: hk-config/tools/clear-vic3-logs.ps1 or delete error.log")
        else:
            all_pass &= check(True, f"error.log baseline OK (size={size} bytes)")
    else:
        print("  ~ error.log not found yet (will be created at game launch)")

    # 6. SUMMARY
    print("\n" + "="*70)
    if all_pass:
        print("✓ ALL CHECKS PASSED — ready to test!")
    else:
        print("✗ SOME CHECKS FAILED — fix above before launching game")
    print("="*70 + "\n")

    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
