---
name: worktree-add
description: Create (or reuse) an isolated git worktree for a branch, with this repo's standard symlinks. Wraps the deterministic tools/worktree-add tool.
---

# Worktree Add

Normative rules: `.claude/STANDARDS.md`. This skill is a capability, not a workflow.

## Purpose

Give a branch its own isolated working directory — a git worktree — instead of
checking it out over whatever is currently in the main clone. Idempotent: calling
it again for the same branch returns the same path.

## When to use

- A workflow is about to start work on a branch (new or existing) and needs a
  working directory that won't collide with whatever else is checked out in the
  main clone or another in-flight ticket.
- A later phase or a fresh session needs to get back to a branch's existing
  worktree rather than guessing its path.

## When not to use

- To decide *whether* the calling workflow should isolate its work in a worktree
  at all — that is the calling agent's or workflow's decision.
- To push the branch, run builds/tests, or do anything beyond creating the
  worktree and its symlinks — those are separate steps the caller owns.
- To pick the branch name — the caller supplies a fully-formed branch name.
- As a substitute for `git checkout` on a branch nobody intends to isolate (a
  one-line hotfix in the main clone doesn't need a worktree).

## Inputs

- Required: `branch` — the branch to check out. Created from the base branch if
  it doesn't exist locally, or from `origin/<branch>` if it exists remotely but
  not locally.
- Optional: `--from <base>` — override the base branch (default: this repo's
  `.claude/shared/project-config.md` "Branch base" row if present, else
  `origin/HEAD`'s default branch).
- Optional: `--name <override>` — override the derived worktree directory name.

## Procedure

1. Run `tools/worktree-add/worktree-add <branch> [--from <base>] [--name <override>]`
   (Linux/macOS), or `tools\worktree-add\worktree-add.cmd` on Windows — see
   `tools/worktree-add/README.md` for why the launcher matters over calling
   `python3`/`python` directly.
2. Capture stdout — the worktree's absolute path — as `{worktree_path}`.
3. Capture stderr for any `WARN:` lines (worktree already existed, a symlink
   couldn't be created) and surface them to the caller as warnings, not
   failures.
4. On non-zero exit, stop and report — do not retry with different arguments
   and do not fall back to a plain `git checkout` in the main clone.

## Outputs

- `{worktree_path}` — the absolute path to the created (or pre-existing)
  worktree. The caller runs its own subsequent git/build/test commands with
  this as the working directory.
- Exit code and any warnings, verbatim.

## Validation

- Exit code `0` and a non-empty path on stdout.
- The tool itself checks `git worktree list --porcelain` before creating
  anything; a caller with reason to distrust the result may re-run that check.

## Evidence

The tool's stdout (path), stderr (warnings/log) and exit code are the evidence.
A calling workflow should record `{worktree_path}` in its own durable run state
(alongside the branch name) so a resumed session — including a fresh one with no
conversation history — knows where the branch's work actually lives, rather than
re-deriving or guessing the path.

## Failure handling

- Exit `1` (base branch unresolved): report to the user and ask for
  `--from <base>` explicitly — do not guess a base.
- Exit `2` (error, e.g. `git worktree add` failed): report the captured
  output verbatim and stop. Do not delete or recreate an existing worktree
  without the user's confirmation — it may hold another session's in-progress,
  uncommitted work.

## Scope

Creates one worktree and its configured symlinks. Does not create commits
beyond what `git worktree add -b` itself makes for a new branch, does not push,
does not run any build/lint/test command, and does not decide what happens
inside the worktree afterward.

## Tools

`tools/worktree-add/worktree-add` (Linux/macOS launcher) and
`tools/worktree-add/worktree-add.cmd` (Windows launcher), both wrapping
`tools/worktree-add/worktree-add.py` and the shared `tools/_lib/` helpers. No
skill-local script — the tool is already generic and lives under `tools/`
per `.claude/STANDARDS.md` §3.
