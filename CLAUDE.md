# CLAUDE.md

## The project

This repository is **salon-app**, a salon booking application. The application is
the product. Everything under `.claude/` and `.orchestration/` is *AI development
infrastructure* used to build and maintain that product — it is not part of the
product and must never be presented as such.

**The existing application architecture and project structure are authoritative.**
Orchestration serves the application; it does not reshape it.

### Application status

As of this scaffold, the repository contains no application source code — only
this file, `README.md`, and the orchestration infrastructure. When application
code lands, record the real stack, layout and commands in the table below rather
than assuming them.

| | |
|---|---|
| Stack | *not yet established* |
| Source layout | *not yet established* |
| Test command | *not yet established* |
| Build command | *not yet established* |
| Lint/format command | *not yet established* |

Until these are filled in, an agent MUST discover project commands from the
repository (package manifests, CI config, existing scripts) and MUST report
"not validated" rather than inventing a command that does not exist.

## How Claude Code works in this repository

Development runs through an **agent → skill → tool** model:

```
AGENT    owns workflow decisions: what happens next, delegate or not, continue,
  |      recover, stop, or escalate
SKILL    one bounded, reusable capability — how a thing is done
  |
TOOL     deterministic operation with predictable inputs and outputs
  |
REPOSITORY
  |
EVIDENCE   what actually happened (distinct from an agent's claim)
  |
HANDOFF    durable state, sufficient for a fresh agent with no conversation history
  |
NEXT AGENT
```

Simple work: `Agent → Skill → Tool → Evidence`.
Complex work: `Lead → (Test, Developer, Reviewer)`, each producing evidence and handoffs.

Operating rules:

1. **Agents own orchestration.** Skills do not decide what runs next; tools do not
   make workflow decisions.
2. **Evidence, not claims.** "Tests passed" is a claim. A command, its scope, its
   exit code and its output are evidence. Where deterministic validation is
   possible, an agent's assertion alone MUST NOT be accepted as proof.
3. **Handoffs must survive context loss.** Durable state lives in
   `.orchestration/runs/<WORK-ID>/`, never only in the conversation. A run
   directory is required once work spans agents, sessions, gates, or recovery —
   not for a single-agent fix done in one sitting (`.claude/STANDARDS.md` §11).
4. **Recovery is bounded.** Execute → validate → bounded recovery → revalidate →
   stop and escalate. No infinite retries; no retry without measurable progress.
   Limits: `.orchestration/policy/retry-limits.json`, `breakers.json`.
5. **Human gates stop work.** `.orchestration/policy/gates.json`. An agent
   reaching a gate stops and asks. It MUST NOT reinterpret a gate as optional or
   route around it.
6. **Scope stays bounded.** Solve the requested problem. Unrelated findings get
   recorded, not fixed.
7. **Delegate only when it helps.** Do not route simple work through a Lead
   because a Lead exists.

## Where things live

| Concern | Location |
|---|---|
| Normative AI-development rules | `.claude/STANDARDS.md` |
| Agent contracts | `.claude/agents/` |
| Skill contracts | `.claude/skills/<skill>/SKILL.md` |
| Skill-specific scripts | `.claude/skills/<skill>/scripts/` (none yet) |
| Shared deterministic tools | `tools/` (empty by design — see `tools/README.md`) |
| Retry / breaker / gate policy | `.orchestration/policy/` |
| Handoff, evidence, status contracts | `.orchestration/schemas/` |
| Durable run state | `.orchestration/runs/<WORK-ID>/` |
| Why this model exists | `docs/adr/ADR-0001-agent-owned-orchestration.md` |
| Application code | wherever the application defines — authoritative |

## Before changing the orchestration layer

- Read **`.claude/STANDARDS.md`** first. It is normative (MUST / MUST NOT / SHOULD).
- For the rationale, read **`docs/adr/ADR-0001-agent-owned-orchestration.md`**. If
  you are reversing a decision recorded there, write a new ADR — do not edit it
  silently.

This file states the operating rules and points at the detail. It deliberately
does not restate the standards.

`CLAUDE.md` is the canonical instruction file here. There is intentionally no
`AGENTS.md`; duplicated instruction sources are a failure mode this design avoids.
