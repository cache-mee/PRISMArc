---
name: code-review
description: Independently review a bounded change to the salon booking application against acceptance criteria, quality and risk, checking the author's evidence rather than trusting it, and return a verdict with specific findings.
---

# Code Review

Normative rules: `.claude/STANDARDS.md`. This skill is a capability, not a workflow.

> **Name collision — resolved, but note the side effect.** Claude Code ships a
> built-in skill also named `code-review`. This project skill takes precedence,
> so `/code-review` in this repository resolves **here**, not to the built-in
> diff-reviewing skill. That is intended — but it means the built-in is no longer
> reachable by name. If you want both, rename this one (e.g. `change-review`).

## Purpose

Independently evaluate a change against its acceptance criteria, its quality
within scope, and the risk it introduces.

## When to use

- A change is complete enough to judge and needs judgement independent of its author.

## When not to use

- To fix defects found — report them; fixing is `implementation`.
- To audit the repository at large.

## Inputs

- Required: the change (diff or file set), declared scope, acceptance criteria.
- Optional: the author's evidence records and handoff.

## Procedure

1. Read the change in full. Establish what it actually does, not what it claims.
2. Check each acceptance criterion against the code.
3. Check the author's evidence: does each record correspond to a real command and
   result? Re-run the decisive check independently.
4. Identify defects with file and line, and state which criterion or expectation
   each violates.
5. Identify risks separately from defects — what could break outside the change.
6. Check scope: were files touched outside the declared scope?
7. Return a verdict, and state explicitly what was **not** reviewed.

## Outputs

- Verdict: pass / pass with findings / fail.
- Findings with location, severity and rationale.
- Risks, separate from defects.
- Scope check result.
- What was not reviewed.

## Validation

- Every finding names a location and a violated expectation.
- The verdict is consistent with the re-run evidence, not with the author's claim.
- A discrepancy between claim and observation is reported, never reconciled
  silently.

## Evidence

Record what was examined and any command re-run, per
`.orchestration/schemas/evidence.md`. Deterministic results are evidence;
quality opinions are **judgements** and MUST be labelled as such.

## Failure handling

If the change cannot be reviewed — too large, scope unstated, criteria missing,
evidence referencing paths that do not exist — stop and report why. Do not issue
a verdict on a change that could not be assessed.

## Scope

Reviews the change, not the repository. Pre-existing issues outside the change
are recorded as findings and do not block unless the change makes them materially
worse. Does not modify code.

## Tools

Native Read, Grep, Glob, Write, and Bash for `git diff` and re-running the
project's own checks. No scripts.
