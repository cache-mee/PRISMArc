# AI Development Standards

Normative standard for the AI development infrastructure of **salon-app**.
**MUST / MUST NOT / SHOULD / SHOULD NOT** carry their usual force.

Scope: this document governs how Claude Code agents develop and maintain the
salon booking application. It does **not** govern the application's product
architecture, which is authoritative and defined by the application itself.

Read this before changing anything under `.claude/` or `.orchestration/`.
Rationale lives in `docs/adr/ADR-0001-agent-owned-orchestration.md`.

Contents: 1. Agents · 2. Skills · 3. Tools · 4. Evidence · 5. Handoffs ·
6. Execution & validation loop · 7. Circuit breakers · 8. Human gates ·
9. Scope control · 10. Delegation · 11. Durable state · 12. Anti-patterns

---

## 1. Agent standard

Agents own orchestration for ad-hoc and cross-workflow work. An agent's
defining question is **"what should happen next?"** An agent that cannot
answer that question is not an agent — it is a skill with a title.

Within one of the four named SDLC workflows, that question is instead answered
by the workflow skill that owns the workflow (see §2, Workflow skills) — an
agent invoked for a phase of that workflow still decides within its own
phase-level responsibility, but does not decide which phase or agent comes
next.

Every agent definition (`.claude/agents/<name>.md`) MUST describe:

- **Purpose** — one sentence.
- **Responsibility** — the decisions it owns, and explicitly what it does not own.
- **Inputs** — what it needs to start, including which durable artifacts.
- **Outputs** — what it produces, including evidence and handoff.
- **Allowed skills** — the bounded capabilities it may invoke.
- **Evidence expectations** — what it MUST produce to claim an outcome.
- **Handoff expectations** — what it MUST write before transferring work.
- **Stop conditions** — when it MUST stop.
- **Escalation conditions** — when a human decides instead.
- **Scope boundaries** — what it MUST NOT touch.

Rules:

- An agent MUST decide what happens next within its responsibility.
- An agent MUST NOT be merely a persona. "You are a meticulous senior engineer"
  is not a contract.
- An agent MUST NOT be created because a technology or domain exists.
  `android-expert`, `kotlin-expert`, `api-expert`, `database-expert` are
  anti-patterns unless genuine independent workflow responsibility exists.
  Prefer workflow responsibilities: `lead`, `test`, `developer`, `reviewer`.
- An agent SHOULD invoke skills rather than restating their procedures inline.
  An agent that duplicates an entire skill has absorbed a capability it does not own.
- An agent MUST interpret results, not forward them. Passing raw output onward
  without a decision is not orchestration.
- Agent responsibilities SHOULD NOT overlap. Where two agents could both act,
  the contracts MUST say which one decides.

A conceptual agent MUST NOT be assumed to require a separate Claude Code
subagent. Use one when isolation, distinct permissions, independent context, or
repeatability justify it; otherwise the main session may act under the contract
directly. Independent review is the clearest justification in this repository:
the Reviewer's value comes from *not* sharing the Developer's context.

---

## 2. Skill standard

There are two kinds of skill: **capability skills** (the default — everything
below applies to these) and **workflow skills** (a narrow, explicitly named
exception, defined at the end of this section). A skill not named in the
Workflow skills list below is a capability skill.

A capability skill is **one bounded, reusable capability** — the procedural
knowledge for how something is done. Capability skills describe capabilities,
not workflows.

> GOOD: "Implement a bounded software change according to supplied acceptance criteria."
> BAD: "First call the Lead Agent, then the Test Agent, then the Developer."

Every skill (`.claude/skills/<skill>/SKILL.md`) MUST define:

- **Purpose** — the single capability.
- **When to use / when not to use.**
- **Inputs** — required and optional.
- **Procedure** — how the capability is performed.
- **Outputs** — what the caller receives.
- **Validation** — how the skill checks its own result.
- **Evidence** — the durable record it produces or enables.
- **Failure handling** — how it reports that it could not do its job.
- **Scope** — what it MUST NOT touch.
- **Tools** — the deterministic operations it may use.

A capability skill MUST NOT:

- orchestrate other agents,
- own the overall task lifecycle,
- decide which agent runs next,
- decide whether the *workflow* continues, stops or escalates,
- chain other skills into a fixed sequence (a hidden workflow engine),
- become a giant "do everything" capability.

A capability skill MAY report "this failed, here is the evidence, here are the
options." Choosing among the options belongs to the calling agent or, for a
workflow phase, the workflow skill that owns that phase.

Capability skills MUST be independently understandable: readable and usable
without knowing which agent or workflow invoked them. Skills SHOULD follow
Agent Skills conventions — a `SKILL.md` with `name` and `description`
frontmatter, with detail progressively disclosed into sibling files rather than
inlined.

### Workflow skills (named exception)

A **workflow skill** is the one deliberate, bounded exception to "a skill MUST
NOT orchestrate": it owns the fixed phase sequence of exactly one named SDLC
workflow, end to end. This repository currently has exactly four:
`sdlc-planning-workflow`, `sdlc-dev-workflow`, `sdlc-qa-workflow`, and
`sdlc-unit-test-workflow` (`.claude/skills/<name>/SKILL.md`).

A workflow skill MAY:

- sequence that workflow's predefined phases,
- decide which agent (or capability skill) to invoke for the current phase,
- own that workflow's human gates and bounded per-phase retries,
- maintain that workflow's progression and durable status artifacts.

A workflow skill MUST NOT:

- invent or reorder phases outside its own documented pipeline,
- decide the sequencing of a *different* named workflow,
- override the judgement an invoked agent owns within its own phase,
- become a general-purpose orchestrator for work outside its one named
  workflow.

This exception does not extend to any other skill. Every other skill — including
sibling skills a workflow skill invokes, such as `worktree-add`,
`workflow-status`, `code-review`, `test-design`, `verification`,
`implementation`, and `requirements` — is a capability skill and remains bound
by "A capability skill MUST NOT" above.

---

## 3. Tool standard

A tool performs a deterministic operation.

A tool MUST:

- perform a concrete operation,
- have predictable inputs and outputs,
- expose observable results (exit status, readable output),
- avoid workflow decisions.

A tool MUST NOT:

- decide which agent runs next,
- own business workflow,
- silently expand scope,
- become an agent.

**Placement is by ownership:**

1. Deterministic operations specific to one skill MUST live in
   `.claude/skills/<skill>/scripts/`.
2. Genuinely shared deterministic operations — needed by two or more skills —
   belong in `tools/`.
3. Where Claude Code already provides the capability natively (Read, Edit, Write,
   Bash, Grep, Glob, git via Bash), the native capability MUST be used rather
   than a wrapper.

A tool SHOULD be promoted from a skill to `tools/` only after a **second real
consumer** exists, not in anticipation of one.

MUST NOT create a `.claude/tools/` directory to mirror the conceptual
Agent → Skill → Tool model. Conceptual layers do not require physical directories.

MUST NOT add an MCP server, dependency, or database for an operation a short
script or a native tool already performs.

There are no scripts in this repository yet. That is deliberate — the first one
should be written when real work demonstrates the need.

---

## 4. Evidence standard

Agents MUST distinguish **claim** from **evidence**.

| | |
|---|---|
| **Claim** | "Tests passed." |
| **Evidence** | command, scope, exit code, result, artifact path, timestamp |

Rules:

- An agent MUST NOT mark work PASS solely because it believes it passed.
- Where deterministic validation is possible, an agent assertion alone MUST NOT
  be treated as proof.
- Evidence MUST record what actually happened, not what was intended.
- Evidence MUST be attributable to a work ID, an action and an agent.
- Evidence MUST be durable — written under
  `.orchestration/runs/<WORK-ID>/evidence/`, not left in conversation.
- Evidence SHOULD be captured from a command's real output, not summarised from
  memory.
- An agent MUST NOT record evidence for a command it did not run.
- Where no deterministic validation exists (design review, requirement
  interpretation), the record MUST be labelled a **judgement** with its
  reasoning, and MUST NOT be presented as deterministic evidence.
- Absence of validation MUST be reported as *not validated*, never as PASS.

Field-level contract: `.orchestration/schemas/evidence.md`.

**Known weakness, stated openly:** an agent that writes its own evidence files can
fabricate them. This scaffold mitigates by convention — evidence must quote a real
command and exit code, and the Reviewer re-runs the decisive check independently.
Whether that is sufficient is an open question this infrastructure exists to
test. If it proves insufficient, evidence capture must move into a script the
acting agent does not author per run.

---

## 5. Handoff standard

Handoffs are first-class orchestration artifacts. A handoff MUST contain enough
information for a fresh agent or session to continue **without reconstructing the
previous agent's reasoning** and without access to the previous conversation.

A handoff MUST contain:

- Work ID · Objective · Acceptance Criteria · Current State · Completed ·
  Failed/unresolved · Constraints · Decisions · Evidence · Next Action ·
  Completion Condition · Escalation

Rules:

- A handoff MUST NOT depend on conversation history remaining available.
- A handoff MUST NOT rely on "as discussed" or "the usual approach".
- A handoff MUST reference evidence by path, and those paths MUST exist.
- The Next Action MUST be concrete enough to start — "make the failing test at
  `path:line` pass", not "continue".
- A handoff SHOULD carry the **minimum useful durable context**. Transcript dumps
  are not handoffs.
- The receiving agent MUST verify sufficiency before proceeding and MUST escalate
  rather than guess when the handoff is inadequate.

Canonical structure: `.orchestration/schemas/handoff.md`.

---

## 6. Execution and validation loop

```
Execute
  ↓
Validate
  ↓
PASS → continue
FAIL
  ↓
bounded recovery  (diagnose → change one thing → retry if permitted)
  ↓
Validate again
  ↓
PASS → continue
still FAIL → STOP / ESCALATE
```

- There MUST NOT be infinite retries.
- A retry MUST have: a stated reason, an allowed retry count
  (`.orchestration/policy/retry-limits.json`), and **measurable progress or a
  changed condition**.
- Progress means an observable change in the failure signal — fewer failing
  tests, a different error signature, a different failing assertion. The same
  failure twice is not progress.
- Re-running an unchanged command is verification, not recovery.
- Every attempt MUST be recorded in `status.json` with its evidence.
- On exhaustion the agent MUST stop and escalate with: what was attempted, what
  the evidence showed, and what decision the human now owns.

**Validation is not a word.** "PASS" without scope is a claim. Validation MUST
state what was run, over what, and what was not covered. The system MUST be able
to detect *agent says PASS, evidence says FAIL*; when it does, evidence wins and
the workflow MUST NOT proceed.

---

## 7. Circuit breakers

Circuit breakers MUST be explicit and testable. Natural-language instructions
such as *"don't retry too much"* are insufficient because they cannot be checked.

Breakers are declared in `.orchestration/policy/breakers.json`. Each MUST have a
trigger evaluable against durable state, and an action.

| Breaker | Trips when | Action |
|---|---|---|
| `attempt-limit` | attempts exceed the applicable retry limit | stop, escalate |
| `no-progress` | two consecutive attempts with an unchanged failure signal | stop, escalate |
| `scope-expansion` | changes touch files outside declared scope | stop, request decision |
| `evidence-conflict` | a claim of PASS conflicts with evidence of FAIL | stop, escalate |
| `gate-encountered` | a human gate is reached | stop, await human |
| `handoff-insufficient` | required handoff fields missing or referencing missing paths | stop, request repair |
| `budget-exceeded` | cumulative ticket cost exceeds `.orchestration/policy/budget-limits.json`'s ceiling | stop, escalate |

- A tripped breaker MUST stop the current line of work.
- An agent MUST NOT edit policy files to get past a breaker. Changing a limit is
  a human decision and a separate change.
- Any new breaker MUST come with a way to evaluate it from durable state.

**Mechanical enforcement.** `tools/breaker-check` evaluates `attempt-limit`,
`no-progress`, `evidence-conflict`, `gate-encountered`, `handoff-insufficient`
and `budget-exceeded` against a run's `status.json` (and, for the budget
breaker, `tools/agent-metrics`) — a deterministic pass/fail, not an agent's
own say-so. `status.json` is written by `breaker-check record-attempt`
(never by hand — a malformed hand-edit would break every later check), called
from `.claude/agents/lead.md` and all four `sdlc-*-workflow` skills before any
retry is granted. Separately, `.claude/hooks/gate-guard.py` mechanically blocks
the Bash-detectable subset of human gates (`merge`, `push-to-shared-branch`,
`destructive-operation`, `release`, `dependency-change`) before the command
ever runs. `scope-expansion`, `production-deploy`, `external-action` and
`architecture-change` remain judgement calls no regex or state check can make
— those still depend on an agent recognising them and a human deciding.

---

## 8. Human gates

A human gate is a point where a consequential or irreversible decision belongs to
a person. Gates are declared in `.orchestration/policy/gates.json` and include
merging, releasing/publishing, production deployment, destructive operations,
irreversible data changes (including customer bookings and payment data),
dependency additions, and scope expansion.

- An agent reaching a required gate MUST stop and surface the decision.
- An agent MUST NOT reinterpret a gate as optional, advisory, or pre-approved.
- An agent MUST NOT route around a gate by another command, tool or ordering.
- Approval of one gate instance MUST NOT be treated as standing approval.
- The stop MUST leave durable state: what is done, what is pending, exactly what
  the human is being asked to decide, and what happens after each answer.

---

## 9. Scope control

- An agent MUST remain within the task's declared scope.
- Unrelated issues discovered along the way MUST be recorded and reported, and
  MUST NOT be opportunistically fixed.
- Scope expansion MUST be an explicit, recorded decision — and, per
  `gates.json`, a human one.
- The declared scope MUST appear in the handoff so "out of scope" is checkable
  rather than arguable.
- A change genuinely required to make the requested change work is in scope, and
  the agent MUST say so explicitly rather than smuggling it in.

---

## 10. Delegation

Delegation is optional. The architecture optimises for **appropriate**
orchestration, not maximum orchestration.

```
Simple work:   Agent → Skill → Tool → Evidence

Complex work:  Lead ── Test
                   ├── Developer
                   └── Reviewer

Named SDLC workflow work (see §2, Workflow skills):
               Workflow Skill → Agent → Capability Skill / Tool → Evidence
```

The named-workflow shape is a separate, parallel path for the four workflow
skills' own domains, not a variant of Lead delegation — a workflow skill
invokes agents directly and does not itself invoke, or get invoked by, the
`lead` agent contract.

- Simple work SHOULD NOT be routed through a Lead. An agent MUST NOT delegate
  merely because a Lead exists.
- Delegation SHOULD be used when work needs independent judgement, isolated
  context, different permissions, or genuine parallelism.
- Delegation SHOULD NOT be used when it only adds a handoff, a context copy, and
  a summary of a summary.
- The cost of delegation — context, latency, information loss at each boundary —
  MUST be justified by the value of the separation.
- Both shapes MUST remain supported. A model that only works with four agents has
  failed one of its requirements.

---

## 11. Durable state

Execution state lives on disk under `.orchestration/runs/<WORK-ID>/`:

```
status.json     machine-readable current state (schema: .orchestration/schemas/status.json)
handoff.md      the current baton
evidence/       evidence records and captured output
decisions/      decisions and rationale
artifacts/      diffs, reports, logs
```

### When a run is required

Durable state has a cost. It MUST be paid where context loss would destroy work,
and SHOULD NOT be paid where it would not.

A run directory MUST be created when any of these is true:

- more than one agent is involved,
- the work will plausibly cross a session boundary,
- a human gate or circuit breaker is reached,
- recovery has begun (a first attempt failed),
- the work is stopped or escalated for any reason.

A run directory is NOT required for single-agent work completed within one
session with no handoff. In that case the acting agent MUST still report evidence
to the requester in the same form — command, scope, exit code, result — because
the evidence standard applies regardless of where the record lives.

If work that began without a run later needs to continue, stop, or escalate, the
agent MUST create the run directory **before** stopping, and write `status.json`
and `handoff.md` at that point. Discovering this too late is itself the failure
mode the standard exists to prevent.

### State rules

- State MUST be updated at agent transitions, at gate stops, and at failures.
- State MUST stay small and machine-readable. It MUST NOT grow into a workflow
  database, queue, or event log needing its own runtime.
- Conversation transcripts are NOT state.
- Where state and a claim disagree, state wins.
- On unrecoverable failure the final state MUST be resumable: a fresh agent
  reading `status.json` and `handoff.md` knows exactly where things stand.

---

## 12. Anti-patterns

Each of these is a MUST NOT.

**Shape** — agent hierarchy for its own sake; every task requiring a Lead;
persona-driven agents; an agent per technology or domain; premature abstraction;
a physical directory for every conceptual box.

**Layer violations** — a capability skill that orchestrates or owns the task
lifecycle (the four named workflow skills are the sole exception — see §2);
tools that make workflow decisions; agents that duplicate a whole skill inline.

**Tooling** — a `.claude/tools/` mirror directory; a giant shared `tools/`
dumping ground; wrappers around native Claude Code capabilities; unnecessary MCP
servers, databases, message buses, vector stores, agent runtimes or workflow
engines.

**Instructions** — duplicated instruction sources (`CLAUDE.md` vs `AGENTS.md`);
restating the whole standard inside `CLAUDE.md`; duplicating `CLAUDE.md` into
every agent file.

**Execution** — infinite retries; retrying without measurable progress; accepting
PASS without evidence; treating a claim as evidence; conversation-dependent
handoffs; scope creep.

**Autonomy overreach** — autonomous merging; autonomous production release or
deployment; bypassing, reinterpreting or routing around a human gate; editing
policy to escape a breaker.

**Product overreach** — modifying the salon application's architecture as part of
orchestration work; creating demo or placeholder application code; letting the
orchestration layer dictate product design.
