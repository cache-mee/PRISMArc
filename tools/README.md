# tools/

Shared deterministic tools for developing and maintaining **salon-app**.

## Currently here

| Tool | What it does | Consumer |
|---|---|---|
| `agent-metrics/` | Measures per-agent-run cost, tokens and process facts (rework, human interventions, outcome) | Run manually by developers; `runrecord` is read by the `sdlc-*-workflow` skills' Run Record steps |
| `worktree-add/` | Creates an isolated git worktree with standard symlinks | The `worktree-add` skill |
| `scope-check/` | Fails if a change touches both `B2B_BE/` and `B2B_FE/` | Enforces CLAUDE.md's Repository layout rule; run manually, from the local pre-commit hook (`.githooks/pre-commit`), in CI (`.github/workflows/scope-check.yml`), explicitly in `sdlc-dev-workflow` Phase 4/6, and delegated to by `policy-guard check-scope` for pre-write enforcement |
| `env-check/` | Reports whether an env var is `SET`/`EMPTY`/`UNSET` without ever printing its value | Pointed to by `.claude/hooks/secret-leak-guard.py`'s block message as the safe way to check a credential is configured |
| `policy-guard/` | Mechanically enforces the backend/frontend scope boundary at write time — delegates to `scope-check`, extended to cover everything already touched in the working tree | Wired as a `PreToolUse` hook in `.claude/settings.json` for the `Write\|Edit` matcher |
| `breaker-check/` | Evaluates `.orchestration/policy/breakers.json` / `retry-limits.json` (and, with `--ticket`, `budget-limits.json` against the `agent-metrics` ledger) against a run's `status.json`; `record-attempt` is the deterministic writer for that file's `attempts[]` | Called by `.claude/agents/lead.md` and all four `sdlc-*-workflow` skills' Bounded Recovery steps, before granting any retry |
| `aws-deploy-check/` | Read-only `aws` CLI checks: account/region match, security-group port exposed to `0.0.0.0/0`/`::/0`, S3 public-access-block state, CloudFront origin OAC — never creates/modifies/destroys a resource | `.claude/agents/deploy.md`'s `aws` environment lifecycle (preflight/security-gate and post-deploy verification) |
| `_lib/` | Shared helpers (git/path utilities, config-table parsing) used by `worktree-add`, `scope-check`, `env-check`, `policy-guard` and `breaker-check` | All of the above |

Bash-command gates (`merge`, `push-to-shared-branch`, `destructive-operation`,
`release`, `dependency-change`) are enforced separately by
`.claude/hooks/gate-guard.py` — a Claude Code hook, not a `tools/` script,
since it only runs as a `PreToolUse` lifecycle hook rather than being invoked
by any skill. See `.claude/hooks/README.md`.

None of these arrived through the "two or more skills need it" rule below in
the strict sense — they're general-purpose developer tools ported/installed
whole, not scripts factored out of a second skill consumer. That's a
deliberate, narrow exception: reject a **new** script here on that rule, but
don't block a complete, independently-useful tool a developer explicitly
wants available project-wide.

## What belongs here

A script belongs in `tools/` only when **all** of these hold:

1. It performs a deterministic operation — predictable inputs, predictable
   outputs, observable result via exit status.
2. It is genuinely needed by **two or more** skills. One real second consumer,
   not an anticipated one.
3. Claude Code does not already provide the capability natively.

## What does not belong here

- **Skill-specific scripts.** If only one skill needs it, it lives in
  `.claude/skills/<skill>/scripts/`. Move it here later if a second consumer
  actually appears.
- **Wrappers around native capabilities.** Read, Write, Edit, Bash, Grep, Glob
  and git-via-Bash already exist. Wrapping them adds indirection and a
  maintenance burden without adding determinism.
- **Wrappers around the project's own commands.** If the application already has
  a test or build command, agents call it directly.
- **Workflow logic.** A tool performs an operation. It MUST NOT decide which
  agent runs next, own business workflow, silently expand scope, or become an
  agent. Those decisions belong to agents (see `.claude/STANDARDS.md`).
- **Speculative utilities.** No helper libraries, no "might be useful later"
  scripts, no framework scaffolding.
- **Application code.** The salon application lives in the application's own
  source tree, not here.

## Placement rule, in short

```
Only one skill needs it        →  .claude/skills/<skill>/scripts/
Two or more skills need it     →  tools/
Claude Code already does it    →  use the native capability
```

There is deliberately no `.claude/tools/` directory. Conceptual layers
(Agent → Skill → Tool) do not require mirrored physical directories.

## If you add something here

State in its header what it does, its inputs, its outputs, its exit codes, and
which skills consume it. A tool nobody can identify a consumer for should be
deleted.
