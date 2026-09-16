---
name: verification
description: Execute the project's deterministic checks for the salon booking application and produce evidence — command, scope, exit code, result — rather than an assertion of success.
---

# Verification

Normative rules: `.claude/STANDARDS.md`. This skill is a capability, not a workflow.

## Purpose

Run deterministic checks and turn their real output into evidence.

## When to use

- A claim about the state of the code needs to be established or refuted.
- Before a verdict, a handoff, or a stop.

## When not to use

- To decide what happens after the result — that is an agent decision.
- To fix what the checks reveal — that is `implementation`.

## Inputs

- Required: what is being verified, and against which criteria.
- Optional: a specific scope (test path, package, changed files).

## Procedure

1. Determine the project's real check commands from the repository (manifests, CI
   config, scripts). If none exist, stop and report — do not invent a command.
2. Run each check, capturing the full command, exit code and output.
3. Record the **scope**: what was covered and, explicitly, what was not.
4. Write an evidence record per `.orchestration/schemas/evidence.md`, storing
   captured output under the run's `evidence/` directory.
5. Compare the result against the acceptance criteria and state which criteria are
   satisfied, which are not, and which remain unverified.
6. Where a prior claim exists, compare it with the observed result and report any
   discrepancy explicitly.

## Outputs

- Evidence records with commands, exit codes, results and scope.
- Criterion-by-criterion status: verified / failed / not verified.
- Any claim-vs-evidence discrepancy found.

## Validation

- Every reported result came from a command actually executed in this run.
- Exit codes are reported as observed, not inferred from output text.
- Scope is stated. "All tests pass" without scope is not acceptable.

## Evidence

This skill is the primary producer of deterministic evidence. It MUST NOT
summarise from memory, and MUST NOT convert a missing or unrunnable check into a
PASS. Unrun checks are reported as *not verified*.

## Failure handling

A failing check is a normal, reportable outcome — report it with evidence and
stop. Deciding whether to retry belongs to the calling agent, within
`.orchestration/policy/retry-limits.json`.

## Scope

Runs and records checks. Does not modify code or tests. Does not judge whether
the work should proceed.

## Tools

Native Bash (the project's own commands), Read, Glob, Write. If capturing
evidence ever needs a repeatable script, it belongs in
`.claude/skills/verification/scripts/` — none exists yet, and one should only be
written when real use demonstrates the need.
