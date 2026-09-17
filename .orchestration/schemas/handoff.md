# Handoff Schema

The durable artifact that transfers work between agents. Written to
`.orchestration/runs/<WORK-ID>/handoff.md`.

**Sufficiency test:** a fresh agent, in a new session, with no access to the
previous conversation and no knowledge of the previous agent's reasoning, must be
able to continue from this file plus the repository alone. If it cannot, the
handoff is defective and the `handoff-insufficient` breaker applies.

Carry the **minimum useful durable context**. A transcript is not a handoff.
Every evidence path referenced MUST exist.

---

## Template

```markdown
# Handoff

## Work ID
<WORK-ID>  (matches .orchestration/runs/<WORK-ID>/)

## Last Updated
<ISO-8601 timestamp, e.g. 2026-09-17T00:00:00+00:00 — stamped by the outgoing
agent at the moment this file is written>

## Objective
One sentence: what this work must achieve.

## Acceptance Criteria
1. Observable, checkable criterion.
2. ...

## Current State
Where execution actually is right now — phase, and what an agent would find on
disk (branch, uncommitted changes, partially applied work).

## Completed
- What is done, each with an evidence reference.

## Failed / Unresolved
- What failed, the observed failure signal, attempt count, and its evidence
  reference.
- Known unresolved questions.

## Constraints
Declared scope (files/areas in scope, and explicitly out of scope), technical
constraints, conventions that must be followed, applicable gates.

## Decisions
Decisions already taken and why — so the next agent does not relitigate or
accidentally reverse them.

## Evidence
Paths under evidence/, each with a one-line statement of what it proves.
Claims without evidence MUST be labelled as claims here.

## Next Action
Concrete enough to start immediately:
"Make <test> at <path:line> pass by changing <area>", not "continue".

## Completion Condition
How the next agent knows it is done — the check that must pass, and its scope.

## Escalation
What would require a human, who decides, and what has already been escalated.
```

---

## Rules

- Written by the outgoing agent **before** the transition, and at every stop.
- `Last Updated` MUST be stamped fresh (current time, ISO-8601, matching the
  format used in `run-record.md`'s `At` column) every time this file is
  written or overwritten — never left carried over from a prior write.
- The receiving agent MUST verify sufficiency before acting, and MUST escalate
  rather than guess when a required section is missing or vague.
- MUST NOT rely on "as discussed", "as usual", or any unnamed prior context.
- MUST NOT contain conversational history, reasoning narrative, or speculation
  presented as fact.
- Superseded handoffs SHOULD be kept under the run's `artifacts/` rather than
  deleted, so the trail survives.
