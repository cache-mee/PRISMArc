# Hooks

> @author Samson Paul, samson.paul@experionglobal.com

## What is this folder?

Small Python scripts that Claude Code runs **automatically** at defined
lifecycle points — nobody invokes them by hand. They are wired up in
`.claude/settings.json` and read/write JSON on stdin/stdout, per the
[official hooks docs](https://docs.claude.com/en/docs/claude-code/hooks).

This is a distinct mechanism from the Agent → Skill → Tool model described in
`.claude/STANDARDS.md`: hooks are Claude Code's own lifecycle guardrails, not
agents, skills, or the deterministic `tools/` this repo otherwise uses. They
exist for one purpose here — a safety net Claude Code itself enforces,
independent of any agent's judgement.

## What's in here

| File | When it runs | What it does |
|------|--------------|--------------|
| `secret-leak-guard.py` | Before Claude runs a Bash command | Blocks commands that paste the raw value of an env var whose name looks like a secret (`*TOKEN*`, `*KEY*`, `*SECRET*`, `*PASSWORD*`, `*PAT*`, `*PRIVATE*`); tells Claude to use `$VAR_NAME` instead so only the variable name is ever displayed |
| `gate-guard.py` | Before Claude runs a Bash command | Mechanically enforces the Bash-detectable subset of `.orchestration/policy/gates.json` — blocks `merge`, `push-to-shared-branch`, `destructive-operation`, `release`, and `dependency-change` commands rather than relying on an agent to recognise and stop at the gate itself |

`tools/policy-guard/` is a related but separate control, wired as a
`Write`/`Edit` `PreToolUse` hook rather than living in this folder — see
`tools/policy-guard/README.md`. It enforces the backend/frontend scope
boundary at write time; this folder's hooks only see `Bash` commands.

Pairs with `tools/env-check/` — a deterministic tool that reports whether an
env var is `SET`/`EMPTY`/`UNSET` without ever printing its value, for the case
where Claude needs to check a credential is configured rather than use it.
`gate-guard.py` also pairs with `tools/breaker-check/`, which enforces the
non-Bash-detectable parts of `breakers.json`/`retry-limits.json` (retry
limits, no-progress, budget) against a run's `status.json`.

## Do I need to touch this?

No. It's wired up once in `.claude/settings.json` and runs in the background.
To disable it, comment out its entry in `settings.json`. To change what it
checks, edit `secret-leak-guard.py` directly — it has no project-specific
hardcoded values.

## Fail-safe philosophy

A hook that errors out or times out is equivalent to an empty response — the
tool call it was checking is let through. Hooks never cause a deadlock. This
is the default for `policy-guard.py` (scope is also re-checked at commit time
by `tools/scope-check`, so a hook failure here isn't the only barrier).

**Exception: `secret-leak-guard.py` and `gate-guard.py` fail closed on their
own internal errors.** Both exist specifically to stop something irreversible
(a leaked secret; a merge/push/destructive/release/dependency command run
without human approval) — silently allowing the command through on an
internal error would defeat their purpose. If either cannot parse its stdin
JSON, or hits any unexpected exception while scanning the command, it emits a
`block` decision instead of the usual `{}` pass-through — the general
fail-open default above does not apply to those two. This is narrower than it
might sound: it only covers errors *inside the script's own Python logic*,
and is not total invulnerability. If the hook process cannot start at all
(Python missing, or on Windows without Git Bash — see **Platform notes**
below), that failure happens before the script's own error handling ever runs,
and Claude Code's own fallback behavior applies — the general fail-open
philosophy still governs that outer case.

## Platform notes

The hook command is POSIX shell (`$VAR`, `[ -f ... ]`, `command -v`) and is
pinned to `"shell": "bash"` in `.claude/settings.json` so Claude Code always
runs it under bash — on Linux and macOS that's the default anyway; on Windows
it requires **Git Bash** to be installed. This is not a new requirement: Git
Bash (or WSL) is already needed for Claude Code's `Bash` tool to work at all
on Windows, so any machine that can run this repo's Bash-tool workflows
already satisfies it. Without Git Bash, Windows falls back to PowerShell,
which cannot parse this command's POSIX syntax — the hook then errors and,
per the fail-safe philosophy above, is silently skipped rather than blocking
anything.
