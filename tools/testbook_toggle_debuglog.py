#!/usr/bin/env python3
"""testbook_toggle_debuglog — turn every mod's debug_log / debug_log_scopes statements ON
(for dev/test) or OFF (before promoting to master), across all mods under mod1\\.

Why: debug_log lines feed the testbook report tables during in-game tests, but must be
commented out for the released master playset (real users generate no logs). This is the
scripted toggle for that (advances TODO T08).

- Matches only real STATEMENTS:  ^<indent>[#] debug_log[_scopes] = ...
  (so prose like "# Logging: debug_log = $B$ ..." is left alone — debug_log isn't at stmt start).
- Preserves UTF-8 BOM and CRLF/LF exactly (only adds/removes the leading '#').
- Idempotent. Use --dry-run to preview.

Usage:
    python tools/testbook_toggle_debuglog.py --on     [--dry-run]
    python tools/testbook_toggle_debuglog.py --off    [--dry-run]
"""
import os, re, sys, argparse

HERE = os.path.dirname(os.path.abspath(__file__))                 # hk-config/tools
MOD1 = os.path.normpath(os.path.join(HERE, "..", "..", "mod1"))   # container/mod1
BOM = b"\xef\xbb\xbf"

# leading indent, optional existing '#', the debug_log[_scopes] = statement start
ON_RE = re.compile(r"(?m)^([ \t]*)#([ \t]*debug_log(?:_scopes)?[ \t]*=)")
OFF_RE = re.compile(r"(?m)^([ \t]*)(debug_log(?:_scopes)?[ \t]*=)")


def toggle_text(text, on):
    if on:
        return ON_RE.subn(r"\1\2", text)        # strip one leading '#'
    return OFF_RE.subn(r"\1#\2", text)          # add '#'


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--on", action="store_true", help="uncomment debug_log (dev/test)")
    g.add_argument("--off", action="store_true", help="comment out debug_log (master)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    on = a.on

    total, touched = 0, 0
    for dp, _, fns in os.walk(MOD1):
        if ".git" in dp.replace("\\", "/").split("/"):
            continue
        for fn in fns:
            if not fn.endswith(".txt"):
                continue
            path = os.path.join(dp, fn)
            raw = open(path, "rb").read()
            had_bom = raw.startswith(BOM)
            text = raw.decode("utf-8-sig", errors="replace")
            new, n = toggle_text(text, on)
            if n:
                total += n
                touched += 1
                rel = os.path.relpath(path, MOD1).replace("\\", "/")
                print(f"  {'[dry] ' if a.dry_run else ''}{rel}: {n} line(s)")
                if not a.dry_run:
                    out = new.encode("utf-8")
                    if had_bom:
                        out = BOM + out
                    open(path, "wb").write(out)
    state = "ON" if on else "OFF"
    print(f"debug_log -> {state}: {total} line(s) across {touched} file(s)"
          f"{' (dry-run, nothing written)' if a.dry_run else ''}")


if __name__ == "__main__":
    main()
