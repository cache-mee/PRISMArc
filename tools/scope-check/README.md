# scope-check

Fails if a single change touches both `B2B_BE/` and `B2B_FE/`. Mechanically
enforces the rule in `CLAUDE.md`'s "Repository layout" section: a ticket that
touches both backend and frontend MUST be two bounded changes, one per
folder — never one change that reaches across both. This is a check, not a
fixer — it reports violations, it never moves or edits files.

## Args

| Form | Behaviour |
|------|-----------|
| `scope-check [--base <ref>] [--head <ref>]` | Diff `base...head` (default: `base` = `origin/HEAD`'s branch, `head` = `HEAD`) |
| `scope-check --staged` | Check staged changes (`git diff --cached`) — for a pre-commit hook |
| `scope-check --files <path> [<path> ...]` | Check an explicit file list, bypassing git entirely |
| `scope-check --help` | Show help |

## Running it, on any OS

Same launcher pattern as `tools/agent-metrics` and `tools/worktree-add`:

| Platform | Launcher |
|---|---|
| Linux / macOS | `tools/scope-check/scope-check [args]` |
| Windows | `tools\scope-check\scope-check.cmd [args]` |

## Exits

| Code | Meaning |
|------|---------|
| 0 | No violation — touches at most one of `B2B_BE/` / `B2B_FE/`, or neither |
| 1 | Violation — files under both folders in the same change |
| 2 | Usage/error (bad ref, missing argument) |

## What it does not do

- Does not know or care about files outside both folders (`CLAUDE.md`,
  `docs/`, `.claude/`, `.orchestration/`, `stack/`, …) — those are orchestration
  infrastructure, not application code, and are never in scope for this check.
- Does not offer an override flag. `CLAUDE.md`'s rule has no exception for a
  genuinely cross-cutting ticket — it must be split into two changes, not
  waved through as one.
- Does not choose the base ref for you in CI. Passing an explicit `--base
  <target-branch>` is the reliable option for a PR check; the default
  (`origin/HEAD`) is a convenience for ad-hoc local use only.

## When the two folders change

`scope-check.py` reads the folder names from `.claude/shared/project-config.md`
→ "Repository Layout" (`Backend folder` / `Frontend folder` rows), falling
back to `B2B_BE/` / `B2B_FE/` if that file or those rows are absent. If
`CLAUDE.md`'s "Repository layout" table ever changes, update both: the config
row (so the check enforces the new names) and the table (so the documented
rule still matches what's enforced).

## Smoke test

```sh
# Should PASS — touches only tools/, neither B2B_BE/ nor B2B_FE/
tools/scope-check/scope-check --files tools/scope-check/README.md

# Should FAIL — one file in each folder
tools/scope-check/scope-check --files B2B_BE/api/foo.py B2B_FE/src/foo.tsx
```

## Source

@author Samson Paul, samson.paul@experionglobal.com
