#!/usr/bin/env python3
"""
hkvault — encrypt private *.md notes on the hk/config branch with age.

Only *.md files are treated as secret (user decision). Plaintext .md is
gitignored; only the encrypted <name>.md.age is committed. The age PUBLIC key
(bin/vault.pub) is enough to seal; the PRIVATE key is only needed to unseal.

Commands
  seal     encrypt every changed *.md -> *.md.age, stop tracking plaintext,
           stage the .age files and commit (use --no-commit to stage only).
  unseal   decrypt every *.md.age -> *.md  (recovery on a new machine).
  verify   assert no plaintext *.md is tracked by git; optionally test-decrypt.

Cross-platform: shells out to the `age` binary (bin/age[.exe] or PATH).

Key locations
  public  : bin/vault.pub                         (committed, encrypt-only)
  private : --key PATH | $VIC3_VAULT_KEY | ~/.vic3-vault/identity.key
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

REQUIRE_BRANCH = "hk/config"      # seal refuses to run anywhere else
EXCLUDE_DIRS   = {".git", "bin", "node_modules"}
EXCLUDE_FILES: set[str] = set()   # add filenames here to keep them plaintext
SCRIPT_DIR = Path(__file__).resolve().parent


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def die(msg: str) -> "None":
    print(f"hkvault: error: {msg}", file=sys.stderr)
    sys.exit(1)


def repo_root() -> Path:
    r = run(["git", "rev-parse", "--show-toplevel"])
    if r.returncode != 0:
        die("not inside a git repository")
    return Path(r.stdout.strip())


def current_branch() -> str:
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()


def find_age() -> str:
    exe = "age.exe" if os.name == "nt" else "age"
    local = SCRIPT_DIR / exe
    if local.exists():
        return str(local)
    found = shutil.which("age")
    if found:
        return found
    die("age binary not found (looked in bin/ and PATH). Install age: "
        "https://github.com/FiloSottile/age/releases")


def recipient() -> str:
    pub = SCRIPT_DIR / "vault.pub"
    if not pub.exists():
        die(f"public key missing: {pub}")
    return pub.read_text(encoding="ascii").strip()


def identity_path(arg: str | None) -> Path:
    cand = arg or os.environ.get("VIC3_VAULT_KEY") or \
        str(Path.home() / ".vic3-vault" / "identity.key")
    p = Path(cand)
    if not p.exists():
        die(f"private key not found: {p}\n"
            f"  pass --key PATH, set VIC3_VAULT_KEY, or restore it from the "
            f"'VIC3-DR-KEY' email.")
    return p


def md_files(root: Path) -> list[Path]:
    out = []
    for p in root.rglob("*.md"):
        rel = p.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.name in EXCLUDE_FILES:
            continue
        out.append(p)
    return sorted(out)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cache_load(root: Path) -> dict:
    f = root / ".vaultcache.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            return {}
    return {}


def cache_save(root: Path, data: dict) -> "None":
    (root / ".vaultcache.json").write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------- commands

def cmd_seal(args) -> "None":
    root = repo_root()
    if not args.allow_any_branch and current_branch() != REQUIRE_BRANCH:
        die(f"refusing to seal on branch '{current_branch()}' "
            f"(expected '{REQUIRE_BRANCH}'; use --allow-any-branch to override)")
    age, rcpt = find_age(), recipient()
    cache = cache_load(root)
    files = md_files(root)
    if not files:
        print("hkvault: no *.md files to seal.")
        return

    sealed, skipped, new_cache = [], 0, {}
    for md in files:
        rel = str(md.relative_to(root)).replace("\\", "/")
        h = sha256(md)
        new_cache[rel] = h
        age_out = md.with_suffix(md.suffix + ".age")
        if cache.get(rel) == h and age_out.exists():
            skipped += 1
            continue
        r = run([age, "-r", rcpt, "-o", str(age_out), str(md)])
        if r.returncode != 0:
            die(f"age failed on {rel}: {r.stderr.strip()}")
        sealed.append(rel)

    cache_save(root, new_cache)

    # stop tracking any plaintext .md, stage encrypted outputs + housekeeping
    run(["git", "rm", "--cached", "--quiet", "--ignore-unmatch",
         *[f for f in (str(p.relative_to(root)) for p in files)]])
    age_paths = [str(p.with_suffix(p.suffix + ".age").relative_to(root))
                 for p in files]
    run(["git", "add", "--", *age_paths, ".gitignore"])

    print(f"hkvault: sealed {len(sealed)} changed, {skipped} unchanged, "
          f"{len(files)} total *.md")
    for rel in sealed:
        print(f"  + {rel}.age")

    if args.no_commit:
        print("hkvault: staged only (--no-commit).")
        return
    staged = run(["git", "diff", "--cached", "--name-only"]).stdout.strip()
    if not staged:
        print("hkvault: nothing to commit (all up to date).")
        return
    msg = args.message or f"vault: seal {len(sealed)} note(s)"
    c = run(["git", "commit", "-m", msg])
    print(c.stdout.strip() or c.stderr.strip())


def cmd_unseal(args) -> "None":
    root = repo_root()
    age = find_age()
    ident = identity_path(args.key)
    age_files = sorted(root.rglob("*.md.age"))
    if not age_files:
        print("hkvault: no *.md.age files to unseal.")
        return
    done, skipped = 0, 0
    cache = {}
    for enc in age_files:
        if any(part in EXCLUDE_DIRS for part in enc.relative_to(root).parts):
            continue
        out = enc.with_suffix("")  # drop .age -> foo.md
        if out.exists() and not args.force:
            skipped += 1
            continue
        r = run([age, "-d", "-i", str(ident), "-o", str(out), str(enc)])
        if r.returncode != 0:
            die(f"age decrypt failed on {enc.name}: {r.stderr.strip()}")
        rel = str(out.relative_to(root)).replace("\\", "/")
        cache[rel] = sha256(out)
        done += 1
        print(f"  + {rel}")
    # refresh cache so a subsequent seal doesn't needlessly re-encrypt
    if cache:
        merged = cache_load(root); merged.update(cache); cache_save(root, merged)
    print(f"hkvault: unsealed {done}, skipped {skipped} "
          f"(use --force to overwrite existing plaintext).")


def cmd_verify(args) -> "None":
    root = repo_root()
    tracked_md = run(["git", "ls-files", "*.md"]).stdout.strip()
    leaks = [l for l in tracked_md.splitlines() if l]
    ok = True
    if leaks:
        ok = False
        print("hkvault: FAIL — plaintext *.md tracked by git:")
        for l in leaks:
            print(f"  ! {l}")
    else:
        print("hkvault: OK - no plaintext *.md is tracked.")

    # optional decrypt test if a key is reachable
    key = args.key or os.environ.get("VIC3_VAULT_KEY") or \
        str(Path.home() / ".vic3-vault" / "identity.key")
    if Path(key).exists():
        age = find_age()
        bad = 0
        for enc in sorted(root.rglob("*.md.age")):
            if any(p in EXCLUDE_DIRS for p in enc.relative_to(root).parts):
                continue
            r = run([age, "-d", "-i", key, "-o", os.devnull, str(enc)])
            if r.returncode != 0:
                bad += 1
                print(f"  ! undecryptable: {enc.relative_to(root)}")
        print(f"hkvault: {'OK' if bad == 0 else 'FAIL'} - "
              f"decrypt-test on *.md.age ({bad} bad).")
        ok = ok and bad == 0
    else:
        print("hkvault: (skipped decrypt-test — no private key reachable)")
    sys.exit(0 if ok else 2)


def main() -> "None":
    ap = argparse.ArgumentParser(prog="hkvault", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("seal", help="encrypt changed *.md and commit")
    s.add_argument("-m", "--message", help="commit message")
    s.add_argument("--no-commit", action="store_true", help="stage only")
    s.add_argument("--allow-any-branch", action="store_true")
    s.set_defaults(func=cmd_seal)

    u = sub.add_parser("unseal", help="decrypt *.md.age -> *.md")
    u.add_argument("--key", help="path to age private key")
    u.add_argument("--force", action="store_true", help="overwrite existing .md")
    u.set_defaults(func=cmd_unseal)

    v = sub.add_parser("verify", help="check no plaintext .md is tracked")
    v.add_argument("--key", help="path to age private key (for decrypt-test)")
    v.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
