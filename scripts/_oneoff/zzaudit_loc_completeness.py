#!/usr/bin/env python3
r"""zzaudit_loc_completeness.py — find loc keys REFERENCED by each mod but missing from its
*_l_english.yml (modifier names, bare debug_log markers, event title/desc). One-off audit that
prototypes the GEN-LOC testbook check. Prints MISSING per mod."""
import os, re, glob

# self-locating (no machine path / username): scripts/_oneoff -> container (victoria-3-mod) -> mod1.
# Override VIC3_MOD_ROOT to audit a different mod1 worktree (mod1-inov, mod1-bpp, ...).
_CONTAINER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MOD_ROOT = os.environ.get("VIC3_MOD_ROOT") or os.path.join(_CONTAINER, "mod1")


def yml_keys(base):
    keys = set()
    for yf in glob.glob(os.path.join(base, "localization", "**", "*.yml"), recursive=True):
        for line in open(yf, encoding="utf-8-sig", errors="replace"):
            m = re.match(r'\s*([A-Za-z0-9_.]+):\d*\s+"', line)
            if m:
                keys.add(m.group(1))
    return keys


def referenced(base):
    ref = {}
    # modifier display names = top-level defs in static_modifiers
    for mf in glob.glob(os.path.join(base, "common", "static_modifiers", "*.txt")):
        t = open(mf, encoding="utf-8-sig", errors="replace").read()
        for m in re.finditer(r'(?m)^([a-z_][a-z0-9_]*)\s*=\s*\{', t):
            ref.setdefault(m.group(1), "modifier")
    # bare debug_log markers (skip quoted strings + $interp$)
    for tf in glob.glob(os.path.join(base, "**", "*.txt"), recursive=True):
        t = open(tf, encoding="utf-8-sig", errors="replace").read()
        for m in re.finditer(r'debug_log\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\b', t):
            k = m.group(1)
            if "$" in k or k.endswith("_"):
                continue
            ref.setdefault(k, "debug_log")
    # visible-event title/desc (hidden events have none)
    for ef in glob.glob(os.path.join(base, "events", "*.txt")):
        t = open(ef, encoding="utf-8-sig", errors="replace").read()
        for m in re.finditer(r'\b(?:title|desc)\s*=\s*([A-Za-z_][A-Za-z0-9_.]*)', t):
            ref.setdefault(m.group(1), "event")
    return ref


def main():
    for mod in sorted(d for d in os.listdir(MOD_ROOT)
                      if os.path.isdir(os.path.join(MOD_ROOT, d)) and not d.startswith(".")):
        base = os.path.join(MOD_ROOT, mod)
        yk = yml_keys(base)
        ref = referenced(base)
        miss = {k: v for k, v in ref.items() if k not in yk}
        print(f"=== {mod} === yml={len(yk)} ref={len(ref)} MISSING={len(miss)}")
        for k, v in sorted(miss.items()):
            print(f"   MISS [{v}] {k}")


if __name__ == "__main__":
    main()
