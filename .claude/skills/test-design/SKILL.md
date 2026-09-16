---
name: test-design
description: Design and write tests that express acceptance criteria for the salon booking application, at the appropriate level, following the project's existing test conventions. Use when criteria need to become executable checks.
---

# Test Design

Normative rules: `.claude/STANDARDS.md`. This skill is a capability, not a workflow.

## Purpose

Turn acceptance criteria into executable checks at the right level, using the
project's existing testing conventions.

## When to use

- Acceptance criteria exist and need to become tests.
- Existing coverage must be analysed for a change.

## When not to use

- To make application code work — that is `implementation`.
- To run the full validation suite for a verdict — that is `verification`.

## Inputs

- Required: acceptance criteria; the repository's test setup and conventions.
- Optional: the change under consideration, known risk areas.

## Procedure

1. Discover the project's test framework, layout and command from the repository.
   If none exists, report that — do not invent one.
2. Analyse existing coverage of the affected behaviour.
3. Choose the level for each criterion: unit for logic, integration for
   collaboration, end-to-end only where the criterion is genuinely about the
   whole path.
4. Write the smallest tests that would fail if the criterion were violated.
5. Run the new tests and confirm they **fail for the right reason** before the
   implementation exists.
6. Map every criterion to a test; list criteria left uncovered, with the reason.

## Outputs

- Test files following existing conventions.
- Criterion → test mapping, including uncovered criteria.
- Observed pre-implementation failure output.

## Validation

- Each new test has been executed.
- Each new test fails for the intended reason, not by accident (import error,
  typo, wrong fixture).
- No existing test was weakened, skipped or deleted to accommodate the new ones.

## Evidence

For each execution record command, scope, exit code, pass/fail counts, timestamp
and artifact path per `.orchestration/schemas/evidence.md`. A test never observed
failing is not established as a meaningful check.

## Failure handling

If a criterion cannot be tested at any reasonable level, or the suite cannot run,
report it as *not validated* with the reason. Never report success for a test
that was not run.

## Scope

Tests for the requested change only. Does not modify application code. Does not
fix unrelated failing tests — those are reported as findings.

## Tools

Native Read, Grep, Glob, Write, Edit, and Bash to run the project's own test
command. No scripts.
