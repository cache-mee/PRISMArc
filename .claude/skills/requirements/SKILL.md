---
name: requirements
description: Turn a request about the salon booking application into a bounded objective, testable acceptance criteria, and an explicit scope statement. Use before implementation or test design when criteria are missing, vague, or untestable.
---

# Requirements

Normative rules: `.claude/STANDARDS.md`. This skill is a capability, not a workflow.

## Purpose

Convert a request into a bounded objective, **testable** acceptance criteria, and
an explicit in-scope / out-of-scope statement.

## When to use

- Acceptance criteria are missing, vague, or cannot be checked.
- Scope is unclear or the request contains several changes bundled together.

## When not to use

- Criteria already exist and are testable — read them, don't rewrite them.
- To decide who works on it next. That is an agent decision.

## Inputs

- Required: the request in the requester's own words.
- Optional: existing tickets/notes, the relevant application code, prior handoffs.

## Procedure

1. Restate the request as one objective sentence.
2. Inspect the relevant part of the application to ground the request in what
   actually exists. Do not assume behaviour — read it.
3. Write acceptance criteria that are **observable**: each one must be checkable
   by a command, a test, or a specific inspection.
4. State scope explicitly: files/areas in scope, and what is deliberately out.
5. List assumptions and open questions separately from criteria.
6. Flag any criterion that cannot be made testable — do not quietly soften it.

## Outputs

- Objective (one sentence).
- Acceptance criteria (numbered, each observable).
- In scope / out of scope.
- Assumptions and open questions.

## Validation

Each criterion must survive: *"what command, test or inspection would show this
is false?"* A criterion with no answer is not a criterion.

## Evidence

Requirements work is **judgement**, not deterministic evidence. Record it as a
judgement per `.orchestration/schemas/evidence.md`, citing the code or documents
read. Do not present it as verified behaviour.

## Failure handling

If the request cannot be made testable — conflicting requirements, missing
product decision, unknown expected behaviour — stop and report the open question.
Do not invent an acceptance criterion to fill the gap.

## Scope

Defines *what* should be true. Does not design the solution, choose the
implementation, write tests, or decide the workflow.

## Tools

Native Claude Code Read, Grep, Glob. No scripts.
