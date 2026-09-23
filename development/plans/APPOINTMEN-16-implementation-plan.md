# Implementation Plan: Web Chat Owner/Admin Identity Resolution (FR-14)

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-16` |
| Type | `Story` (label: `backend`) |
| Branch | `feature/APPOINTMEN-16-owner-admin-identity-resolution` |
| Assigned to | `sparc.team_25@experionglobal.com` |

---

## Overview

This ticket mirrors the already-merged APPOINTMEN-17 (FR-24, Staff identity resolution), which built the
entire phone-number → Staff lookup mechanism (model, repository, LLM-callable tool, and a
`manager_agent.py` stub) **generically across both `StaffRole` values** — `owner_admin` and `staff` — not
just for Meena/Arjun. Reading that code confirms the lookup/resolution mechanism itself needs no new
persistence or query logic for Ramesh: `resolve_speaker(phone_number)` already resolves any seeded Staff
row (including Ramesh, seeded as `owner_admin` by APPOINTMEN-17's own seed migration) to an unambiguous
`SpeakerContext`, and a non-matching number already falls through to `None` with no fallback flow — which
is exactly what the AC asks for on the "no match" side.

What is genuinely missing, per the UX spec
(`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/staff-owner-manager-chat.md` §2), is that the
Manager Agent's opening response after a match is supposed to be **role-differentiated** — Staff match:
"Hi Meena! Want to update your availability?"; **Owner/Admin match: "Hi Ramesh! Want to update the
service catalog?"** — and `manager_agent.py`'s current `describe_speaker` only renders one generic line
("Recognized as {name} ({role}).") regardless of role. That generic line does not represent the
role-specific, no-signup-step "recognized and granted the right permissions" experience FR-14 (and the
UX spec) describe for Ramesh. This plan's entire scope is adding that one missing rendering capability at
the same stub-function layer APPOINTMEN-17 established — no new endpoint, no new persistence, no
role-scoped tool registry (that still depends on an LLM tool-calling loop that does not exist anywhere in
the repo yet, exactly as APPOINTMEN-17's plan already noted and deferred).

---

## Business Context

From the ticket (verbatim): *"As Ramesh (Owner/Admin) using Web Chat, I want the Manager Agent to ask for
my phone number and match it against my pre-seeded record, so I'm recognized and granted the right
permissions."*

**AC (FR-14, Web Chat clause, epics.md Story 1.4):**
- "A Web Chat session with a matching pre-seeded number results in the Manager Agent granting
  Owner/Admin-permitted actions (FR-15–FR-17, FR-19) without a signup step."
- "A non-matching number is out of scope for this demo (no fallback flow defined — PRD explicit
  limitation, not a gap in this story)."

At the current stub layer (no chat endpoint, no LLM loop, no role-scoped tool registry exists yet — same
stage APPOINTMEN-17 left the repo at), the concrete, demonstrable slice of "recognized and granted the
right permissions... without a signup step" is: (a) a match resolves immediately with no interim
name-capture/signup step (already true — `resolve_speaker` returns a full identity or `None`, never a
partial/pending state), and (b) the Manager Agent's rendered response actually reflects that Ramesh was
recognized *as Owner/Admin*, using the role-specific opening line the UX spec defines for that role. (b)
is the one piece not yet built.

---

## Technical Context

Stack: FastAPI + SQLAlchemy + Alembic + PostgreSQL, per `stack/rules/base-rules.md`. All persistence
(`app/models/staff.py`, `app/repositories/staff_repository.py`), the LLM-callable tool
(`app/tools/staff.py`), and the Manager Agent stub (`app/agent/manager_agent.py` — `resolve_speaker` /
`describe_speaker`) already exist on `develop`, built by APPOINTMEN-17, and are already role-agnostic:
`StaffRole` covers both `OWNER_ADMIN` and `STAFF`, `get_staff_by_phone_number` has no role filter, and
`resolve_staff_identity` / `resolve_speaker` return whichever role matched. Ramesh's row
(`+15550000001`, `role=owner_admin`) is already seeded by APPOINTMEN-17's
`8aac3e937d39_seed_staff_records.py` migration. **No new migration, model, repository, or tool is needed
for this ticket.**

The one real gap is presentational: `describe_speaker` renders a single generic sentence regardless of
role, which does not implement the UX spec's §2 role-differentiated opening line. This plan adds a
second, purpose-built rendering function — `render_identity_greeting(context: SpeakerContext) -> str` —
in the same module, following the exact precedent of `booking_agent.confirm_exact_match` /
`render_direct_confirmation`: a pure, synchronous rendering function with no I/O, callable as the hook
point a future conversational Manager Agent loop will invoke immediately after `resolve_speaker` returns
a match. `describe_speaker` is left untouched (it is APPOINTMEN-17/FR-24's own deliverable, and changing
its output risks an unrelated regression against a closed ticket outside this ticket's scope) —
`render_identity_greeting` is additive, not a replacement.

No new `app/domain/` module is introduced: as APPOINTMEN-17's plan already noted for this exact module,
a short piece of presentation logic tied 1:1 to the agent stub does not warrant an intermediate domain
layer, and keeping the precedent of `describe_speaker` living directly in `manager_agent.py` keeps the
two closely-related rendering functions co-located.

**Note on branch state:** the branch was initially cut from a stale `main` (missing `B2B_BE/` entirely)
during Phase 2 branch setup; this was caught and corrected before this plan was finalized — the branch
has since been recreated from the current `develop` tip (`45c25d7`, which already contains APPOINTMEN-17's
`B2B_BE/` work this ticket builds on, plus everything merged since). No prerequisite branch work remains.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/agent/manager_agent.py` | Modify | Add `render_identity_greeting`, the role-differentiated opening-line function the UX spec (§2) and FR-14's AC require; update the module docstring to record this ticket's addition alongside APPOINTMEN-17's. |

No other file is touched. No file outside `B2B_BE/` is read or written.

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: Role-differentiated identity greeting

**Description:** Add `render_identity_greeting(context: SpeakerContext) -> str` to
`B2B_BE/app/agent/manager_agent.py`. Given an already-resolved `SpeakerContext` (from `resolve_speaker`),
returns the UX-spec-mandated opening line for the matched role:
- `StaffRole.OWNER_ADMIN` → `"Hi {name}! Want to update the service catalog?"` (this ticket's concrete
  FR-14 deliverable — Ramesh's case).
- `StaffRole.STAFF` → `"Hi {name}! Want to update your availability?"` (included because the UX spec
  presents both lines together as one resolution step in §2, and the function would otherwise need an
  incomplete/partial role match; this branch does not change or replace FR-24/APPOINTMEN-17's own
  `describe_speaker` deliverable, which is left as-is).

This is the hook point a future conversational Manager Agent loop calls immediately after a successful
`resolve_speaker(phone_number)` match, in place of (or alongside) `describe_speaker`, to produce the
actual user-facing greeting FR-14/FR-24 describe. It does not call any tool, touch the database, or
depend on a role-scoped tool registry — consistent with the stub-layer scope APPOINTMEN-17 established
(no chat endpoint or LLM loop exists yet to wire this into).

**Files to modify:**
- `B2B_BE/app/agent/manager_agent.py`

**New files to create:** *(none)*

**Dependencies:** None (all upstream pieces — `SpeakerContext`, `resolve_speaker`, `StaffRole` — already
exist on `develop` from APPOINTMEN-17).

**Complexity:** `Low`

**Testing requirements:**
- Unit test: given a `SpeakerContext` with `role=StaffRole.OWNER_ADMIN` and `name="Ramesh"`, returns
  `"Hi Ramesh! Want to update the service catalog?"`.
- Unit test: given a `SpeakerContext` with `role=StaffRole.STAFF` and `name="Meena"`, returns
  `"Hi Meena! Want to update your availability?"`.
- No integration test needed — this function performs no I/O; a real DB is not required to exercise it.

**Documentation updates:** *(optional)*
- None beyond the module docstring update described above.

---

## External Dependencies

- **None new.** No new package, environment variable, or infrastructure dependency. The Postgres
  instance, `staff` table, and Ramesh's seeded row already exist on `develop` (APPOINTMEN-17). This
  ticket depends only on the feature branch being brought up to date with `develop` first (see Technical
  Context note above) — a repository-state prerequisite, not an external dependency.

---

## Testing Strategy

Per `stack/rules/base-rules.md` Testing Requirements: the PRD is happy-flow-only for this build, and test
priority is ordered (1) the three confirm-before-write behaviors (FR-9/FR-18/FR-27), (2) conflict
detection (FR-26), (3) everything else, time permitting. This ticket's change is a pure, synchronous
rendering function with no write path and no conflict-detection involvement, so it falls in tier 3 — a
cheap, low-risk unit test is appropriate if testing time is spent here at all; it is not one of the
prioritized items and its omission would not violate base-rules.md's stated priorities.

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | `render_identity_greeting` — one case per `StaffRole` value, asserting the exact rendered string | `pytest` |
| Integration | Not applicable — no DB/tool call is involved in this ticket's change | `pytest` (available, not invoked for this ticket) |
| End-to-End | Not applicable — no chat endpoint/LLM loop exists yet to exercise end-to-end | N/A |

Minimum coverage expectation: consistent with APPOINTMEN-17's own precedent (no test files exist yet for
`app/agent/manager_agent.py`, `app/tools/staff.py`, or `app/repositories/staff_repository.py` on
`develop`), whether to add the unit test above is a decision for the human gate reviewing this plan, not
one this plan presumes either way.

---

## Security Considerations

- No change to the identity-resolution or auth model: phone-number lookup remains the entire mechanism,
  per PRD §7/`base-rules.md` Security Baselines — no password, OTP, or session token is introduced.
- `render_identity_greeting` only formats a string from an already-resolved, already-validated
  `SpeakerContext`; it introduces no new input-validation surface.
- Actual enforcement of "Owner/Admin-permitted actions" (FR-15–FR-17, FR-19) via a role-scoped tool
  registry remains out of scope here, exactly as it was out of scope for APPOINTMEN-17 — no LLM
  tool-calling loop exists anywhere in the repo yet for either role's registry to attach to.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AC's "granted the right permissions" reads as broader than a greeting-string change | Med | Med | Explicitly scoped down in Overview/Technical Context to what the current stub layer can demonstrate; the full permission-grant (role-scoped tool registry) depends on not-yet-built LLM/chat-loop infrastructure, out of scope for both this ticket and its APPOINTMEN-17 predecessor. |
| No chat endpoint/LLM loop exists to demonstrate this end-to-end | High | Low | Same accepted limitation as APPOINTMEN-17; demonstrated at the function level only, called out here rather than silently claimed as end-to-end. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — Role-differentiated identity greeting | `Low` |
| **Overall** | `Low` |

---

## Out of Scope

- **The full role-scoped tool registry / permission enforcement** (FR-15–FR-17, FR-19 actually being
  callable) — depends on an LLM tool-calling loop that does not exist anywhere in the repo yet; out of
  scope for this ticket exactly as it was for APPOINTMEN-17.
- **A working chat endpoint or WebSocket surface** (`app/api/chat.py`) — not created by this ticket.
- **The "ask for a phone number" conversational turn itself** — this ticket (like APPOINTMEN-17) only
  adds the rendering capability used once a phone number has already been resolved; the turn that
  solicits it depends on the not-yet-built chat endpoint/LLM loop.
- **Any change to `describe_speaker`, `resolve_speaker`, the `Staff` model, the repository, or the
  `resolve_staff_identity` tool** — all already correctly generic across roles per APPOINTMEN-17; no
  modification is needed or made.
- **Catalog CRUD (FR-15–FR-19)** — a separate, not-yet-built set of future tickets; this ticket is
  identity-resolution only.
- **Staff-side (FR-24) behavior changes** — already delivered and closed by APPOINTMEN-17; this plan adds
  the Staff-role branch of `render_identity_greeting` only because the UX spec presents both lines
  together, not to modify FR-24's existing, already-accepted behavior.
- **WhatsApp-channel identity resolution** for Owner/Admin — Web Chat only, per this ticket's stated
  scope.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-16` · Branch: `feature/APPOINTMEN-16-owner-admin-identity-resolution`*
