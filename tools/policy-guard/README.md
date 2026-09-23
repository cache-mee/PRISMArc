# policy-guard

Mechanically enforces the backend/frontend scope boundary **at write time**,
not just at commit time.

`tools/scope-check` already fails a change that touches both `B2B_BE/` and
`B2B_FE/` — but only when run explicitly (pre-commit hook, CI, or by hand).
By the time that runs, an agent may already have written several
cross-boundary files in one sitting. `policy-guard` closes that gap: it
shells out to `scope-check` the moment a `Write` or `Edit` tool call is about
to add one more file to the working tree, so the violation is caught at the
first offending write.

It does not duplicate `scope-check`'s logic, and it does not re-implement
anything the repo's other policy tools already own:

- Bash-command gates (merge, push-to-shared-branch, destructive-operation,
  release, dependency-change) are enforced by `.claude/hooks/gate-guard.py`.
- Retry/no-progress/budget breakers are enforced by `tools/breaker-check`.

`policy-guard`'s only job is pre-write scope.

## Subcommands

| Form | Behaviour |
|------|-----------|
| `policy-guard check-scope --files <path> [<path> ...]` | Would writing these paths (plus everything already touched in the working tree) violate CLAUDE.md's Repository layout rule? |
| `policy-guard hook` | Claude Code PreToolUse hook mode for `Write`/`Edit` — reads the tool-call JSON on stdin, emits `{"decision":"block",...}` or `{}` on stdout |
| `policy-guard --self-test` | Runs the checks in `_self_test()` against a scratch repo; exits 1 on any failure |

## Running it, on any OS

| Platform | Launcher |
|---|---|
| Linux / macOS | `tools/policy-guard/policy-guard [args]` |
| Windows | `tools\policy-guard\policy-guard.cmd [args]` |

## How it's wired in

`.claude/settings.json` → `PreToolUse` hooks for the `Write|Edit` matcher call
`tools/policy-guard/policy-guard hook`. This is the actual enforcement point —
a cross-boundary `Write`/`Edit` is blocked before it happens, not caught later
at commit.

## Fail-open by design

Unlike `.claude/hooks/gate-guard.py` (fail-closed — it protects irreversible
actions), `policy-guard`'s scope check fails **open** on any internal error
(missing `scope-check.py`, a `git status` failure, etc.) — a boundary
violation is still caught at commit time by the existing pre-commit hook and
CI, so this hook is defense-in-depth, not the only barrier. A hard failure
here should not block ordinary file edits.

## Smoke test

```sh
# Should PASS — nothing touched yet
tools/policy-guard/policy-guard check-scope --files B2B_BE/example.py

# Should BLOCK if a B2B_BE file is already touched in the working tree
tools/policy-guard/policy-guard check-scope --files B2B_FE/example.tsx
```

## Source

@author Samson Paul, samson.paul@experionglobal.com
