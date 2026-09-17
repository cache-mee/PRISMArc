# env-check

> @author Samson Paul, samson.paul@experionglobal.com

Reports whether an environment variable is set — **never prints its value**.

Exists because hand-writing a shell one-liner to test a credential's presence
can leak it: `${VAR:-UNSET}` expands to the variable's *value* when `VAR` is
set, since `:-` is the default-value operator, not a presence check. This tool
cannot emit a value at all — it only ever prints `SET`, `EMPTY`, or `UNSET`.

Consumer: `.claude/hooks/secret-leak-guard.py` points here as the safe
alternative whenever it blocks a Bash command for embedding a raw secret
value.

## Args

| Form | Behaviour |
|------|-----------|
| `env-check <VAR> [<VAR> ...]` | Print `<NAME>: SET\|EMPTY\|UNSET` per var |
| `env-check --help` | Show help |

## Running it, on any OS

| Platform | Launcher |
|---|---|
| Linux / macOS | `tools/env-check/env-check <VAR> [<VAR> ...]` |
| Windows | `tools\env-check\env-check.cmd <VAR> [<VAR> ...]` |

Each launcher probes for a real Python 3 instead of guessing which `python`
command exists on this machine (see `tools/worktree-add/README.md` → "Windows
and macOS — what's different" for why `python3`/`python` can't be assumed).

## Exits

| Code | Meaning |
|------|---------|
| 0 | Every named variable is `SET` |
| 1 | At least one is `EMPTY` or `UNSET` |
| 2 | Error (no variable names given) |

## Smoke test

```sh
tools/env-check/env-check PATH NONEXISTENT_VAR_XYZ
# → PATH: SET
#   NONEXISTENT_VAR_XYZ: UNSET
# exit 1
```
