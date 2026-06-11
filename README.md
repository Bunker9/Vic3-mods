# hk/config — Housekeeping branch

> ⚠️ **This is an ORPHAN branch. It has NO shared history with `master` and must NEVER be
> merged into `master` (or any release branch).** It exists only to version-control project
> housekeeping that doesn't belong in the shipped mod: tool settings, editor config,
> environment setup notes, and snapshots of the planning docs.

## 🆕 Setting up on a fresh clone / new machine?
**→ Follow [`BOOTSTRAP.md`](BOOTSTRAP.md)** — the full step-by-step (clone → restore configs/
docs/tools → CWTools rules → game junction → verify). `ENVIRONMENT.md` lists the original
machine's exact paths as a worked reference.

## Why this exists
A lot of valuable project state is otherwise unversioned or outside the mod repo:
- `mod1\Top40EcoBoostMod\.vscode\settings.json` and `mod1\TODO-CI.md` are **gitignored**.
- `Top40EcoBoostMod.code-workspace`, the `roadmap\`, `PROGRESS.md`, `CLAUDE.md`, and the
  `tools\` scripts live in the **container** (`victoria-3-mod\`), which is not a git repo.

This branch is a safety net + version history for all of it, pushed to GitHub.

## What's here (snapshots)
```
config/   vscode-settings.json, Top40EcoBoostMod.code-workspace, TODO-CI.md
docs/     PROGRESS.md, MOD-ROADMAP.md, CLAUDE.md   (copies of the container originals)
tools/    parse_country_stats.py, country_stats.csv
ENVIRONMENT.md   machine setup (paths, junction, OneDrive Documents, cwtools, debug flow)
```
These are **point-in-time copies**. The live originals remain in the container / mod repo;
re-sync periodically (see below).

## How to update (one command)
This branch is checked out as a **git worktree** at `…\victoria-3-mod\hk-config`, so it
coexists with the dev working tree (no branch-switching). To refresh + push, just run:
```powershell
powershell -ExecutionPolicy Bypass -File tools\sync-hk.ps1
```
It copies the current `.vscode` settings, `.code-workspace`, `TODO-CI.md`, **all** project
`.md` docs (container root + `roadmap\`), and the `tools\` scripts into here, then commits +
pushes only if something changed. (The script lives in `…\victoria-3-mod\tools\sync-hk.ps1`
and is itself snapshotted to `tools/` here.)

## Recreate the worktree (e.g. on a fresh clone / new machine)
```powershell
git -C C:\Users\user\Projects\victoria-3-mod\mod1 worktree add `
  C:\Users\user\Projects\victoria-3-mod\hk-config hk/config
```

## Rules
- **NEVER merge `hk/config` (or any `hk/*`) to `master`.** Orphan history makes an
  accidental clean merge unlikely, but the rule stands regardless.
- Safe to force-update / rewrite as needed — nothing depends on its history.
