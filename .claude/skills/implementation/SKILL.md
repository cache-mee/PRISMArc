---
name: implementation
description: Implement a bounded change to the salon booking application according to supplied acceptance criteria, using the smallest appropriate edit and the project's existing conventions.
---

# Implementation

Normative rules: `.claude/STANDARDS.md`. This skill is a capability, not a workflow.

## Purpose

Implement a bounded software change according to supplied acceptance criteria.

## When to use

- Acceptance criteria and scope are defined, and code must change.

## When not to use

- Criteria are unclear — use `requirements` first.
- The goal is to judge someone else's change — use `code-review`.

## Inputs

- Required: objective, acceptance criteria, declared scope.
- Optional: failing test(s) to satisfy; prior handoff and evidence.

## Procedure

1. Read the relevant code before editing it. Match existing conventions; the
   application's architecture is authoritative.
2. Identify the **smallest change** that satisfies the criteria.
3. Make the change. Keep edits inside the declared scope.
4. Run the relevant local validation (the project's own test/build/lint commands).
5. If validation fails: diagnose and report the failure signal with its evidence.
   Whether to attempt a fix again is the calling agent's decision, bounded by
   `.orchestration/policy/retry-limits.json`; this skill performs an attempt when
   asked and MUST NOT keep retrying on its own judgement.
6. Record every file touched and compare it against the declared scope.

## Outputs

- The change.
- Files touched vs declared scope.
- Decisions taken and their rationale.
- Anything deliberately not done.

## Validation

- The project's relevant checks were run and their real results recorded.
- The previously failing check now passes, where one existed.
- No test was weakened or removed to obtain green.
- No file outside declared scope was modified.

## Evidence

Record command, scope, exit code, result and artifact path for each run, per
`.orchestration/schemas/evidence.md`. Record the before (failing) and after
(passing) states where applicable. Never record a command that was not run.

## Failure handling

If the change cannot be completed within scope, if validation cannot run, or if
two attempts produce the same failure signal — stop and report state, attempts
and evidence. Do not broaden the change to force a pass.

## Scope

Implements the requested change only. Does not refactor unrelated code, reformat
files, upgrade dependencies, or alter application architecture. Unrelated issues
are recorded, not fixed. Never merges, releases or deploys — those are human gates.

## Tools

Native Read, Grep, Glob, Edit, Write, and Bash for the project's own build/test
commands. No scripts.
