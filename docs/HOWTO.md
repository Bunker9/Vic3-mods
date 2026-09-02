# HOWTO — recreate this project from GitHub on any machine

**Plaintext on purpose.** Every other `*.md` on this branch is age-encrypted, and you cannot read
them until you have done step 3 below. This file is the one that tells you how, so it stays
readable (allowlisted in `.gitignore` + `EXCLUDE_FILES` in `bin/hkvault.py`, alongside
`README.md` and `CHECKPOINTS.md`). **Keep it free of usernames, real names and private emails.**

Written 2026-09-02 at project close-out. Paths use `<PLACEHOLDERS>`; machine-specific values are
in the sealed `BOOTSTRAP.md` and `ENVIRONMENT.md` once you can read them.

> **Reading this as Claude?** Do steps 1 to 6 in order, then run the `hello` command. Do not start
> task work before the session-opening ritual. Everything you need to know about how to work in
> this project is in `docs/DEV-RULES.md` and the restored memory set, not in this file.

---

## What this project is

A Victoria 3 (Paradox) modding workspace. **13 released mods** live on `master`. One GitHub repo,
`Bunker9/Vic3-mods`, holding **three branches with UNRELATED histories** that never merge:

| branch | worktree folder | what it is |
|---|---|---|
| `master`, `dev/*` | `mod1\` | the mods themselves — one folder per mod |
| `hk/config` | `hk-config\` | housekeeping: docs, vault, tools, trackers (this branch) |
| `testbook` | `testbook\` | the test + debug framework (v2 active, v1 archive) |

The **container folder is NOT a git repo**. It holds only `CLAUDE.md`, `.claude\`, the three
worktrees, and a `cwtools\` clone. That is why the container files are backed up inside
`hk-config\config\` — see step 5.

---

## 0. Prerequisites

- Git 2.42+, Python 3 (with `openpyxl`), Victoria 3 on Steam
- VS Code + the CWTools extension (optional but assumed by the workspace file)
- A GitHub account with access to `Bunker9/Vic3-mods`, and a Personal Access Token
- The age vault **private key** — see step 3. Without it every note stays encrypted.

Set these for your machine:
```powershell
$PROJECT = "<path>\victoria-3-mod"     # container folder; any path you like
$GAME    = "C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game"
$DOCS    = [Environment]::GetFolderPath('MyDocuments')   # may be OneDrive-redirected
```
> On Windows, Documents is often redirected to OneDrive, sometimes under a localized folder name.
> Always resolve it with `GetFolderPath('MyDocuments')`, never a literal `...\Documents\...` path —
> the game reads the real one.

## 1. Clone and add the two other worktrees

The username-in-URL form is deliberate: it makes Git Credential Manager key this repo's credential
separately from any other GitHub account on the machine.

```powershell
git clone https://<gh-user>@github.com/Bunker9/Vic3-mods.git "$PROJECT\mod1"
git -C "$PROJECT\mod1" config user.name  "<gh-user>"
git -C "$PROJECT\mod1" config user.email "<gh-user>@users.noreply.github.com"
git -C "$PROJECT\mod1" worktree add "$PROJECT\hk-config" hk/config
git -C "$PROJECT\mod1" worktree add "$PROJECT\testbook"  testbook
```

**One-time per clone**, so a machine-wide gh credential helper cannot shadow GCM for this repo
(lives in the shared `.git/config`, so every future worktree inherits it):
```powershell
git -C "$PROJECT\mod1" config --local 'credential.https://github.com.helper' ''
git -C "$PROJECT\mod1" config --local --add 'credential.https://github.com.helper' 'manager'
```

Never use `gh` for PRs or merges in this project — create and merge them in the browser.

## 2. Clone the CWTools rules

```powershell
git clone https://github.com/cwtools/cwtools-vic3-config.git "$PROJECT\cwtools\cwtools-vic3-config"
```

## 3. Unseal the vault (do this before reading any other doc)

Full detail is in `RECOVERY.txt` at the `hk-config` root, which is also plaintext.

1. The **private key is not in the repo.** Retrieve it from email — search for the subject token
   **`VIC3-DR-KEY`** — and save it to `<home>\.vic3-vault\identity.key`.
2. Decrypt everything:
   ```powershell
   cd "$PROJECT\hk-config"
   python bin\hkvault.py unseal
   ```
3. Re-enable the `git seal` / `git unseal` / `git vault` shorthands: `bin\install.bat`.

Plaintext `*.md` is gitignored forever; only the `.age` ciphertext is ever committed. After editing
notes, `git seal` re-encrypts them.

## 4. Restore the machine-local config files

These are gitignored by design; copy each from its committed `.example` twin and edit:

| create | from | set |
|---|---|---|
| `hk-config\config\refpaths.json` | `refpaths.example.json` | `game_files_path`, `vic3_user_dir` |
| `hk-config\config\gitidentity.json` | `gitidentity.example.json` | your default vs Vic3 identities |
| `testbook\v2\tools\Framework-common\config_game.toml` | `config_game.example.toml` | log + save dirs |

Nothing in the project may hardcode a machine path — analysis scripts read `refpaths.json`.

## 5. Restore the container and the Claude assets

The container is not a repo, so these live only as backups inside `hk-config\config\`. Copy them
back out:

```powershell
Copy-Item "$PROJECT\hk-config\config\container-CLAUDE.md" "$PROJECT\CLAUDE.md"
```

Claude Code assets (paths are for Claude Code on Windows):
- `config\claude-command-hello.md` → `<home>\.claude\commands\hello.md`
  (the session-opening ritual command; it is directory-aware and routes on the folder name)
- `config\claude-memory\*.md` → `<home>\.claude\projects\<PROJECT-SLUG>\memory\`
  — 66 files including `MEMORY.md`, the auto-loaded index. **This is the project's accumulated
  dev-rule enforcement layer**; without it a new session will repeat mistakes the project already
  learned. The `<PROJECT-SLUG>` is derived by Claude Code from the container path with separators
  replaced by dashes, so **it changes if you put the project somewhere else** — check what folder
  Claude Code actually creates under `.claude\projects\` and use that one.
- `config\claude-settings\settings.local.container.example.json` → `$PROJECT\.claude\settings.local.json`,
  replacing every `<USER>` with your Windows username. This one carries the **SessionStart hook**
  that forces the hello ritual, plus the permission allowlist and the `git push` / `gh pr merge`
  denials. The other four `settings.local.*.example.json` are per-worktree and optional.

## 6. Unseal the trackers, then read yourself in

```powershell
cd "$PROJECT\hk-config"
powershell -ExecutionPolicy Bypass -File tools\githk_seal_todo.ps1 -Unseal -Path data\TODO.xlsx
powershell -ExecutionPolicy Bypass -File tools\githk_seal_todo.ps1 -Unseal -Path data\testbook_status.xlsx
```

`data\TODO.xlsx` is the **single tracker** for this project — tasks, musings, per-patch re-work.
Sheets named `dump_*` are archived reference folded in from retired trackers; never scan them for
open work.

Then read, in order: `CLAUDE.md`, `docs\DEV-RULES.md`, `docs\PROGRESS.md` (tail), `CHECKPOINTS.md`,
`docs\CEREMONIES.md`, `docs\DOC-INDEX.md`, and `data\TODO.xlsx`. That is exactly what the `hello`
command automates.

## 7. Link the mods into the game

The launcher loads each mod through a directory junction, so edits hotload from the repo:
```powershell
powershell -ExecutionPolicy Bypass -File hk-config\tools\link-mod-to-launcher.ps1 -All
```
`-All` assumes every mod lives in `mod1\`. If you ever check a mod out into its own dev worktree,
junction that one by hand — `-All` would yank it back to `mod1`.

**Two CWTools gotchas** that otherwise stop vanilla from indexing: map the Paradox file extensions
to the `vic3` language, and point the rules cache at the `\game` subfolder, not the install root.

---

## State of the project at close-out (2026-09-02)

- **13 mods released** on `master`; the last release was the `rebal-Aug2026-Mid` branch, which the
  author played end to end (1836 to 1936) with no crashes, no debug loops and no balance problems.
- **Static verification is complete**: `chk_structure` 214/214, zero active `debug_log`, zero active
  `_fingerprint_`.
- **What was never proven**: about 40 TODO rows are per-feature in-game checks that the full
  playthrough covers only in aggregate. They are deliberately left `open` and annotated. If
  development ever resumes, start there.
- **Three things to know before you touch the tooling:**
  1. `tools\githk_build_todo_xlsx.py` is a **hazard** — its source `data\TODO.csv` no longer
     exists, so running it emits a single-sheet workbook and destroys the Musings, `dump_*` and
     `re-work-*` sheets. Tracked as T229. Hand-maintain the xlsx with `openpyxl`.
  2. Ceremony 3 step 5 (runtime debug silence on a promoted build) has never been run — three
     releases now. Tracked as T205.
  3. The debug framework (`testbook\v2\tools\`) is the ONLY place mod debugging happens. Do not
     write ad-hoc analysis scripts; extend the framework.
- **Branches are never deleted**; inactive ones auto-delete after 90 days. `archive/*` branches
  preserve two rejected/WIP stashes, and `dev/betterpoppromo` carries an unfinished mod plus the
  HappyHalloween stub (its research lives in `roadmap\ROADMAP-happyhalloween.md`).
