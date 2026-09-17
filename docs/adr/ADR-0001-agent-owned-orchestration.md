# ADR-0001 — Agent-Owned Orchestration for AI-assisted development

## Status

Proposed / Experimental. Adopted for the AI development infrastructure of
salon-app; not yet validated by real use. Amended 2026-09-18 to recognize
Workflow Skills as a bounded exception — see **Amendment** below.

## Scope of this decision

**The salon booking application is the product.** Agent-owned orchestration is an
AI software-engineering mechanism used to develop and maintain that product.

This ADR does **not** prescribe the application's product architecture. The
application's own architecture and conventions remain authoritative. If this
document and the application ever appear to conflict about how the product should
be built, the application wins and this document is wrong.

This ADR explains **why** the mechanism exists. It is not the operational manual —
that is `.claude/STANDARDS.md`, with the entry point in `CLAUDE.md`.

## Context

Using an AI coding agent on a real application surfaces problems that prompt
quality alone does not solve:

- **Context is volatile.** Sessions end, compact, or are replaced. Work that
  exists only in a conversation is lost when the conversation is.
- **Claims are cheap.** An agent can report "tests pass" without having run
  anything meaningful. Without a record of what actually executed, a plausible
  summary is indistinguishable from a verified outcome.
- **Failure loops.** Without explicit bounds, an agent can retry indefinitely,
  making no measurable progress and consuming context.
- **Scope drift.** Agents opportunistically "improve" unrelated code, turning a
  small fix into an unreviewable change.
- **Consequential actions.** Merging, releasing, deploying and touching real
  booking or payment data must not happen because an agent judged it reasonable.
- **Orchestration has to live somewhere.** Something must decide what happens
  next. The question is which layer owns that decision.

The last point is the actual decision. Common answers put sequencing in a ticket
template, inside skills, or in a central workflow engine. Each moves the decision
away from the component that has the most information at the moment the decision
is made.

## Decision

Adopt **agent-owned orchestration** with bounded skills, deterministic tools,
durable evidence, durable handoffs, bounded recovery and explicit human gates.

```
Agent → Skill → Tool → Repository → Evidence → Handoff → Next Agent
```

Simple work: `Agent → Skill → Tool → Evidence`.
Complex work: a Lead delegating to Test, Developer and Reviewer.
Named SDLC workflow work: a Workflow Skill delegating to the applicable Agent
(see **Amendment** below).

### Agent responsibility

Agents own orchestration. An agent decides what happens next within its
responsibility: whether to delegate, what sequence to run, how to interpret a
result, whether to continue, recover, stop or escalate, and when the work is
complete. Agents are workflow roles with contracts — not personas, and not one
agent per technology.

### Skill responsibility

A skill owns one bounded, reusable capability: the procedural knowledge for how
something is done. Skills describe capabilities, not workflows. A skill does not
own the task lifecycle, does not decide which agent runs next, and does not chain
other skills into a fixed sequence — that would make it a hidden workflow engine.
This is the rule for **capability skills**. **Workflow skills** are a later,
narrow exception to it — see **Amendment** below.

### Tool responsibility

A tool performs a deterministic operation with predictable inputs and outputs and
an observable result. A tool makes no workflow decisions. Placement follows
ownership: skill-specific scripts live with the skill, genuinely shared ones in
`tools/`, and native Claude Code capabilities are used directly rather than
wrapped. Conceptual layers do not require mirrored directories, so there is no
`.claude/tools/`.

### Evidence

Evidence records what actually happened, and is deliberately distinct from an
agent's claim. "Tests passed" is a claim; a command with its scope, exit code,
result and artifact is evidence. Where deterministic validation is possible, an
assertion alone is not accepted as proof. This exists so the system can detect
the specific failure mode *agent says PASS, evidence says FAIL* — and stop.

### Handoffs

A handoff carries the minimum durable context needed for a fresh agent to
continue without the previous conversation and without reconstructing the
previous agent's reasoning. This is the answer to context volatility: execution
state and evidence live on disk under `.orchestration/runs/<WORK-ID>/`, and the
conversation is treated as disposable.

### Recovery

Execute → validate → on failure, bounded recovery → revalidate → otherwise stop
and escalate. A retry requires a stated reason, an allowed count, and measurable
progress. Repeating the same failure is not progress.

### Circuit breakers

Breakers are declared as data in `.orchestration/policy/breakers.json` with
triggers evaluable against durable state, rather than as prose like "don't retry
too much" — which cannot be checked or tested. This shape is chosen so that a
future deterministic check can *prove* a breaker stops execution.

### Human gates

Consequential and irreversible actions — merging, releasing, deploying,
destructive operations, changes to real booking or payment data, dependency
changes, scope expansion — stop at an explicit gate declared in
`.orchestration/policy/gates.json`. An agent reaching a gate stops; it may not
reinterpret the gate as optional or route around it.

### Delegation

Delegation is optional and has a real cost in context, latency and information
loss at each boundary. Simple work runs as a single agent through skills. A Lead
is used only when coordination provides genuine value — chiefly when independent
review matters, since the Reviewer's value comes from *not* sharing the
Developer's context. The architecture must support both shapes; optimising for
maximum orchestration would be a failure, not a success.

### Scope control

Agents solve the requested problem. Unrelated findings are recorded and reported,
never opportunistically fixed. Scope expansion is an explicit, recorded decision.

## Alternatives considered

**1. Ticket-owned orchestration.** The ticket or issue template encodes the
sequence of steps. Rejected: the sequence is fixed before anything is known about
what the work will actually require, and the ticket cannot react to a result. It
also pushes process detail into a system that has no visibility into the
repository.

**2. Skill-owned orchestration.** Skills call each other in sequence. Rejected:
this turns skills into hidden workflow engines, destroys their reusability
(each becomes coupled to a specific flow), and scatters the "what happens next"
decision across many components with no single owner. *Amended 2026-09-18:* a
narrow, bounded version of this alternative — one skill owning the sequence of
exactly one named SDLC workflow, not skills chaining each other ad hoc — was
later adopted; see **Amendment** below. Unbounded skill-owned orchestration for
arbitrary skills remains rejected.

**3. Large hierarchical agent systems.** Many specialised agents — per
technology, per layer, per domain — under a deep coordinator tree. Rejected:
cost and information loss grow at every boundary, most such agents own no real
decision (they are personas), and the hierarchy tends to exist for its own sake.
Four workflow roles is already close to the upper bound of what this project can
justify.

**4. Centralised workflow engine.** A runtime that executes a declared workflow
and calls agents as steps. Rejected for now: it is a substantial piece of
infrastructure to build and maintain, it moves decisions away from the component
with the most context, and it would be built before we know which decisions are
even worth encoding. It remains a legitimate future option if agent-owned
sequencing proves unreliable.

**5. Agent-owned orchestration (chosen).** The decision sits with the component
that holds the most information at the moment of the decision, while skills stay
bounded and reusable, tools stay deterministic, and the risky parts — retries,
scope, consequential actions — are constrained by explicit policy rather than by
the agent's judgement alone.

## Amendment (2026-09-18) — Workflow skills

Real use produced four fixed, high-value SDLC pipelines — planning, development,
unit testing, and QA — each with a stable, well-understood phase sequence and
its own human gates. Encoding that known sequence once, in a dedicated skill, is
cheaper and less error-prone than re-deriving it by agent judgement on every
run, and there is one skill owner per pipeline rather than none.

`sdlc-planning-workflow`, `sdlc-dev-workflow`, `sdlc-qa-workflow`, and
`sdlc-unit-test-workflow` (`.claude/skills/<name>/SKILL.md`) are recognized as
**workflow skills**: each owns the phase sequencing, agent invocation, and
human gates for exactly one named workflow. This is narrower than Alternative 2
above — it does not let arbitrary skills chain each other, only these four
skills sequence their own one named pipeline. Full rules are normative in
`.claude/STANDARDS.md` §2 ("Workflow skills").

This does not change anything else in this ADR: capability skills remain
bounded and non-orchestrating, agents still own orchestration for ad-hoc and
cross-workflow work, and the `lead` agent does not participate in any of the
four workflow skills' execution paths — none of their phases invoke it.

## Consequences

**Positive**

- Work survives context loss; a new session can resume from disk.
- "It passed" becomes checkable rather than asserted.
- Retry behaviour, scope and consequential actions are bounded by explicit,
  reviewable policy files.
- Skills stay small and reusable across agents.
- Simple tasks stay cheap — no mandatory orchestration overhead.
- The infrastructure is small enough to delete or change if it proves wrong.

**Negative**

- Real overhead: writing evidence and handoffs costs time and context on work
  that would otherwise be a quick edit. If the ceremony exceeds the value on
  small tasks, the thresholds are wrong and must be adjusted.
- **Enforcement is conventional, not mechanical.** Nothing evaluates the policy
  files today; agents read and obey them. A non-compliant agent is not stopped by
  the repository.
- **Self-reported evidence is forgeable.** An agent writing its own evidence can
  fabricate it. Independent re-runs by the Reviewer are a mitigation, not a proof.
- Judgement calls remain: "smallest appropriate change", "measurable progress"
  and "genuine value from delegation" are not fully mechanical tests.
- More files to keep consistent; documentation can drift from practice.

## Non-goals

This decision does **not** introduce, and the repository must not grow:

- an orchestration framework, agent runtime or workflow engine;
- a database, message bus or vector store for agent state;
- unnecessary MCP servers or wrappers around native Claude Code capabilities;
- autonomous merging, releasing, or production deployment;
- large agent hierarchies, or an agent per technology or domain;
- a mandatory Lead for every task;
- persona-based agents;
- demo or placeholder application code;
- any change to the salon application's architecture as part of orchestration work.

## Validation plan

The scaffold proves nothing. It is a foundation to be falsified against real
salon-app development work.

Validation is by running actual tasks through this infrastructure and recording
what breaks:

1. **A small bug fix** — does simple work stay simple, or does the model impose
   unnecessary orchestration?
2. **A feature with a Lead** — is delegation worth its cost?
3. **A deliberately failing validation** — does recovery stay bounded and stop?
4. **A fresh session resuming from a handoff only** — can it continue without the
   prior conversation? This is the load-bearing test.
5. **A claimed PASS contradicted by evidence** — is the conflict detected, and
   does work stop?
6. **Unrelated problems present in the repository** — is scope held?
7. **A consequential action** — does the agent stop at the gate?

Each run should record: whether the boundaries held, what the overhead cost, and
which rule was ambiguous in practice.

The architecture is not proven by existing. **If real use shows a boundary is
wrong — a skill too broad, an agent unnecessary, a gate misplaced, evidence
insufficient, or the whole model too expensive for its benefit — change the
architecture and record it in a new ADR. Do not defend this design because it was
written first.**
