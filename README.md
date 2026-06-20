# hk/config — Housekeeping branch

> ⚠️ **This is an ORPHAN branch. It has NO shared history with `master` and must NEVER be
> merged into `master` (or any release branch).** It exists only to version-control project
> housekeeping that doesn't belong in the shipped mod: planning notes, dev rules, ceremonies,
> analysis tooling, and disaster-recovery config — all kept out of the public mod history.

## 🆕 Setting up on a fresh clone / new machine?
**→ Follow [`BOOTSTRAP.md`](BOOTSTRAP.md)** — clone → restore configs/docs/tools → CWTools rules →
game junction → verify. `ENVIRONMENT.md` lists a worked reference of the original machine's paths.

## Privacy model — encrypted vault (age)
Notes and planning docs are **secret by default**. Git physically cannot commit plaintext `*.md`
(gitignored); only the age-encrypted `*.md.age` ciphertext is tracked, so this **public** repo is a
safe backup that browsers can't read. Encrypt with `git seal` (public key, no secret needed); decrypt
with `git unseal` (needs the private `identity.key`, never committed). See `bin/` for the tooling.

**The only plaintext, allowlisted files** (no `.age`, committed as-is — keep them PII-free):
- `README.md` (this file)
- `CHECKPOINTS.md` (the checkpoint/tag log — updated only at a master-PR merge; see Ceremony 4)

## Layout
```
bin/      age vault tooling (hkvault.py = git seal/unseal/vault; age binaries + vault.pub)
docs/     encrypted notes — PROGRESS, DEV-RULES, CEREMONIES, design_decisions, bugfix… (*.md.age)
roadmap/  encrypted planning notes (*.md.age)
tools/    self-locating analysis + housekeeping scripts; data CSVs + DATA_INDEX.md catalog
scripts/  orchestrators + ceremonies (compose tools/); MANIFEST.md script index; _oneoff/ throwaways
config/   de-usernamed editor snapshots; refpaths/gitidentity are *.example only (real ones gitignored)
data/     TODO.xlsx.age (age-encrypted task tracker; plaintext xlsx gitignored)
README.md, CHECKPOINTS.md   ← plaintext, allowlisted
```

## How to update / push
There is no single "sync" command anymore — edit notes in place, then run the **Pre-Push Ceremony**
(seal LAST) so only ciphertext reaches origin. See `docs/CEREMONIES.md` (read via `git unseal`):
- **Ceremony 5 — Pre-Push:** `tools/githk_seal_todo.ps1` (TODO.xlsx → .age) + `bin/hkvault.py seal`
  (`*.md` → `*.md.age`) + one commit. The helper `scripts/githk_seal_commit.ps1` does it in one shot.
- **Ceremony 6 — Worktree Health Check:** PII scan / seal freshness / no keys / manifest currency —
  run before pushing this branch OR `testbook`.

The push itself is done by the human from a real terminal (the sandbox can't complete the PAT prompt).

## Recreate the worktree (fresh clone / new machine)
```powershell
git -C <container>\mod1 worktree add <container>\hk-config hk/config
```

## Rules
- **NEVER merge `hk/config` (or any `hk/*`) to `master`.** Orphan history makes an accidental clean
  merge unlikely, but the rule stands regardless.
- **No PII anywhere** — Windows username, real name, private email must never be committed (the
  allowlisted plaintext files especially). Machine paths go through `config/refpaths.json` (gitignored)
  or self-locating script logic, never a literal `C:/Users/<name>/...`.
- Safe to force-update / rewrite history as needed — nothing depends on its history.
