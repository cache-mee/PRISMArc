# Project Config

Machine-readable project configuration, parsed by `tools/_lib/config_parse.py`.
Rows are `| Label | Value |`; see that file's docstring for the exact lookup
functions and format each one expects. Human-facing rules stay in `CLAUDE.md`
and `stack/rules/` — this file exists only so scripts under `tools/` have one
place to read the same declared values from, instead of hardcoding them.

## Repository Layout

Mirrors `CLAUDE.md` → "Repository layout". Consumed by
`tools/scope-check/scope-check.py`. If this table ever changes, update it here
*and* in `CLAUDE.md` — this file is the value scripts read; `CLAUDE.md` is the
human-facing rule that explains why.

| Setting | Value |
|---|---|
| Backend folder | B2B_BE/ |
| Frontend folder | B2B_FE/ |

## Worktree Symlinks

Consumed by `tools/worktree-add/worktree-add.py`. Every new worktree gets these
symlinked back to the main clone instead of being created empty — without this,
each new ticket worktree would be missing local, gitignored files the app needs
to actually run.

| Path | Purpose |
|---|---|
| .env | Root env vars (gitignored, per-machine) — required for the app to connect to its configured services. Add a per-package row here (e.g. `B2B_BE/.env`) if/when one exists as a real file, not just `.env.example`. |
