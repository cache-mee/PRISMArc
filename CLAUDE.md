# CLAUDE.md

## The project

This repository is **salon-app**, a salon booking application. The application is
the product. Everything under `.claude/` and `.orchestration/` is *AI development
infrastructure* used to build and maintain that product — it is not part of the
product and must never be presented as such.

**The existing application architecture and project structure are authoritative.**
Orchestration serves the application; it does not reshape it.

### Application status

As of this scaffold, the repository contains no application source code beyond
the `B2B_BE/` and `B2B_FE/` root folders (see **Repository layout** below), this
file, `README.md`, and the orchestration infrastructure. When application code
lands, record the real stack, commands, and any layout detail beyond the
backend/frontend split in the table below rather than assuming them.

| | |
|---|---|
| Stack | See `stack/stack-proposal.md` and `stack/rules/base-rules.md` |
| Source layout | Backend → `B2B_BE/` · Frontend → `B2B_FE/` (see **Repository layout** below and `stack/rules/base-rules.md` §3.9) |
| Test command | *not yet established* |
| Build command | *not yet established* |
| Lint/format command | *not yet established* |

Until the commands above are filled in, an agent MUST discover them from the
repository (package manifests, CI config, existing scripts) and MUST report
"not validated" rather than inventing a command that does not exist.

### Repository layout

The application is split into two independently-owned top-level folders. This
split is authoritative and fixed — it is not something any agent re-derives or
re-proposes per ticket.

| Folder | Owns |
|---|---|
| `B2B_BE/` | Backend — APIs, services, data access, business logic, backend tests |
| `B2B_FE/` | Frontend — UI, client-side logic, frontend tests |

Rules every agent MUST follow:

1. **Classify before writing.** Determine whether a ticket is backend,
   frontend, or both — from its stated component/label/type first, and from
   what the acceptance criteria actually change (API/DB/service logic →
   backend; UI/client behaviour → frontend) if none is stated.
2. **Confine every file to the matching folder.** All files created or edited
   for a backend ticket MUST live under `B2B_BE/`; all files for a frontend
   ticket MUST live under `B2B_FE/`. Do not create a new top-level folder for
   application code, and do not place backend files in `B2B_FE/` or vice versa.
3. **Split cross-cutting tickets.** A ticket that genuinely touches both (e.g.
   a new endpoint plus the UI that calls it) MUST be treated as two bounded
   changes, one per folder — not one change that reaches across both.
4. **Ambiguity is a stop condition, not a guess.** If a ticket's classification
   is genuinely unclear, stop and prompt the user to confirm which folder (or
   both, as two bounded changes) the ticket belongs to — never guess, and never
   write to both folders "to be safe." Proceed only once the user confirms.

This governs every agent that reads or writes application code — Developer,
Test, Reviewer, and Architect alike.

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
| Application code | `B2B_BE/` (backend), `B2B_FE/` (frontend) — see **Repository layout** above |

## Before changing the orchestration layer

- Read **`.claude/STANDARDS.md`** first. It is normative (MUST / MUST NOT / SHOULD).
- For the rationale, read **`docs/adr/ADR-0001-agent-owned-orchestration.md`**. If
  you are reversing a decision recorded there, write a new ADR — do not edit it
  silently.

This file states the operating rules and points at the detail. It deliberately
does not restate the standards.

`CLAUDE.md` is the canonical instruction file here. There is intentionally no
`AGENTS.md`; duplicated instruction sources are a failure mode this design avoids.
