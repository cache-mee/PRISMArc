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

Pairs with `tools/env-check/` — a deterministic tool that reports whether an
env var is `SET`/`EMPTY`/`UNSET` without ever printing its value, for the case
where Claude needs to check a credential is configured rather than use it.

## Do I need to touch this?

No. It's wired up once in `.claude/settings.json` and runs in the background.
To disable it, comment out its entry in `settings.json`. To change what it
checks, edit `secret-leak-guard.py` directly — it has no project-specific
hardcoded values.

## Fail-safe philosophy

A hook that errors out or times out is equivalent to an empty response — the
tool call it was checking is let through. Hooks never cause a deadlock.

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
