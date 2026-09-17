# worktree-add

Create an isolated git worktree for a branch, with the standard symlinks
listed in `.claude/shared/project-config.md` → "Worktree Symlinks" (if that
file exists — see "Optional config" below). Idempotent.

The tool and its two shared library files (`tools/_lib/common.py`,
`tools/_lib/config_parse.py`) are generic — no project-specific logic. Shared
tools live under top-level `tools/` in this repo, never `.claude/tools/`
(`.claude/STANDARDS.md` §3 forbids that directory).

## Args

| Form | Behaviour |
|------|-----------|
| `worktree-add <branch>` | Create worktree from configured base |
| `worktree-add <branch> --from <base>` | Override the base branch |
| `worktree-add <branch> --name <override>` | Override the auto-derived worktree name |
| `worktree-add --help` | Show help |

## Running it, on any OS

Use the launcher for your platform instead of guessing which `python` command
exists — each one probes for a real Python 3 by trying candidate names in
order and only accepting one that actually reports major version 3:

| Platform | Launcher | What it tries, in order |
|---|---|---|
| Linux / macOS | `tools/worktree-add/worktree-add <branch> …` | `python3`, `python`, `py`, `python3.13` … `python3.8` |
| Windows | `tools\worktree-add\worktree-add.cmd <branch> …` | `py -3`, then `python` — never `python3` (see below) |

Calling `worktree-add.py` directly with an explicit interpreter
(`python3 tools/worktree-add/worktree-add.py <branch>`) always works too; the
launchers exist only to remove the guesswork.

### Windows and macOS — what's different

- **macOS**: `python` may not exist; `python3` does on any machine with the
  Xcode command line tools. The launcher probes both, so use it rather than a
  hardcoded name.
- **Windows**: `python3` is deliberately not tried by `worktree-add.cmd` — on
  Windows it is usually a Microsoft Store stub that opens the app page instead
  of running anything. `py -3` is tried first, then `python`.
- **Windows symlinks**: a real symlink needs Developer Mode enabled or an
  elevated shell. Without either, the tool falls back automatically to a
  **directory junction** (`mklink /J`) for directory entries or a **hard
  link** (`os.link`) for file entries — neither needs admin rights or
  Developer Mode. Only a target on a different drive/volume than the
  worktree has no unprivileged option; that case is reported as a warning
  (`WARN: link failed: …`) and counted in the `failed=` total. The worktree
  itself is always created regardless.

## Worktree-name derivation

If `--name` isn't given:
- **Ticket-first branches** (`<PREFIX>-<id>/<slug>`) keep the id and convert the
  `/` to `-` (e.g. `PROJ-42/spike-server-costs` → `PROJ-42-spike-server-costs`).
- **Type-prefixed branches** (`feature/`, `fix/`, `hotfix/`, `epic/`, `chore/`,
  `release/`, `demo/`) drop the first segment (e.g. `hotfix/PROJ-99-crash` →
  `PROJ-99-crash`).
- Branches with no `/` keep their full name.

## Worktree path

`<parent-of-repo>/worktrees-<repo-dirname>/<worktree-name>`

## Optional config

This repo has no `.claude/shared/project-config.md` today, and the tool works
correctly without one — it falls back to `origin/HEAD`'s default branch
(`main`) when no base is configured, and creates zero symlinks when no
"Worktree Symlinks" section exists. If a future need arises (e.g. a build
file that must be symlinked into every worktree), add
`.claude/shared/project-config.md` with:

- a `| Branch base | <branch> |` row, to change the default base branch, and/or
- a `## Worktree Symlinks` section with one `| <path> | <purpose> |` row per
  file/directory to symlink into new worktrees.

## Exits

| Code | Meaning |
|------|---------|
| 0 | Worktree created (or already existed) — path emitted on stdout |
| 1 | Could not resolve base branch |
| 2 | Error |

## Smoke test

```sh
git fetch origin
tools/worktree-add/worktree-add chore/wt-smoke-test --from main
# → /…/worktrees-PRISMArc/wt-smoke-test

# Idempotent — second run returns the same path with a warning
tools/worktree-add/worktree-add chore/wt-smoke-test
# → same path, "WARN: worktree already exists at …"

# Cleanup
git worktree remove ../worktrees-PRISMArc/wt-smoke-test
git branch -D chore/wt-smoke-test
```

## Source

@author Samson Paul, samson.paul@experionglobal.com
