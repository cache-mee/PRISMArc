# Implementation Plan: Exact-Time Resolution — Direct Confirmation (FR-6)

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-22` |
| Type | `Story` (label: `backend`) |
| Branch | `feature/APPOINTMEN-22-exact-time-direct-confirm` |
| Assigned to | `sparc.team25@experionglobal.com` |

---

## Overview

Give the (not-yet-built) Booking Agent a working, testable rendering capability for the FR-6
direct-confirmation step (epics.md Story 2.5): given an already-resolved, already-available booking
candidate — Service, exact date/time, and assigned Staff member — produce the confirmation response that
names all three and explicitly asks the Customer to confirm before any Booking is created. This is a
narrow slice, mirroring how APPOINTMEN-17 built a narrow Manager-Agent-facing capability ahead of its
nominal dependencies: it does not build the upstream work this story nominally depends on (Story 2.2
intent parsing, Story 2.3 staff-preference limiting, Story 2.4's SM-4a checkpoint, or the Service/Booking/
Availability entities from APPOINTMEN-13/Story 1.1), all of which are still not implemented. Instead it
takes those inputs as an assumed-resolved `ResolvedBookingCandidate` and delivers exactly the FR-6 output:
the confirmation message plus an explicit "not yet confirmed" flag a future caller must honor before
writing anything.

---

## Business Context

From the ticket (verbatim): *"As a Customer who named an exact, available date/time (and staff, if named),
I want the Booking Agent to confirm that slot directly, so I don't have to pick from a list."*

**AC (FR-6):** *"agent's response names service, date/time, and assigned staff, and asks for explicit
confirmation before creating the booking."*

User-facing outcome: when a Customer's request already matches an open slot, the Booking Agent's reply is
a single, unambiguous confirmation naming all three details, rather than an unnecessary list of
alternatives — and no Booking is created until the Customer explicitly says yes.

---

## Technical Context

Stack: FastAPI + SQLAlchemy + Alembic + PostgreSQL, per `stack/rules/base-rules.md`. The enforced backend
tree names both `app/agent/booking_agent.py` and `app/domain/appointments.py` — neither exists yet
(verified against the current worktree: only `app/agent/manager_agent.py`,
`app/agent/{__init__,prompts/__init__,state/__init__}.py` exist under `app/agent/`, and `app/domain/`
contains only an empty `__init__.py`).

**Dependency-ordering decision (explicit, per user instruction, same pattern as APPOINTMEN-17):** this
story's nominal dependencies — Story 2.2 (FR-5 intent parsing), Story 2.3 (FR-13 staff-preference
limiting), Story 2.4 (SM-4a human-verification checkpoint), and the Service/Booking/Availability entities
from APPOINTMEN-13 (Story 1.1) — are all still not implemented. This plan does not build any of them. It
instead scopes FR-6 to exactly what it needs on its own: a pure function that takes an
already-resolved-and-available `(service, exact datetime, assigned staff)` tuple and renders the FR-6
confirmation response. Availability-checking itself is assumed to have already happened by the time this
function is called (it is out of scope here — it depends on the Availability entity, which does not
exist). Staff assignment (whether the Customer named a staff member, or one was auto-assigned) is likewise
assumed already resolved on the input — this ticket only renders the confirmation, it does not decide who
gets assigned.

Layering: `app/domain/appointments.py` (new) holds the `ResolvedBookingCandidate` input model and the pure
`render_direct_confirmation()` rendering function — this is domain logic (the content/shape of a
direct-confirmation message, including date/time formatting), not a DB-backed tool, so it needs no
repository, no model, and no migration. `app/agent/booking_agent.py` (new) is the Booking Agent module
named in the enforced tree; it exposes `confirm_exact_match()`, the hook point a future conversational
Booking Agent loop will call once intent parsing, staff-preference limiting, the SM-4a checkpoint, and an
actual availability check have all resolved to one candidate slot. No `app/tools/` file is added — there
is no DB access or LLM-callable side effect here (contrast with APPOINTMEN-17's `tools/staff.py`, which
does a DB lookup); this is a plain computation the agent module calls directly, matching the same
"declared, not silent" layering-deviation approach APPOINTMEN-17 used when a layer would be pure
indirection. Both new functions are synchronous — no I/O occurs, so `base-rules.md`'s async-for-I/O rule
does not apply, consistent with `manager_agent.py`'s existing (also synchronous) stub pattern.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/domain/appointments.py` | New | `ResolvedBookingCandidate` input model + `render_direct_confirmation()` — the FR-6 message-rendering logic. Named per the enforced tree; does not exist yet. |
| `B2B_BE/app/agent/booking_agent.py` | New | Booking Agent module named in the enforced tree (does not exist yet); exposes `confirm_exact_match()`, the FR-6 hook point a future conversational loop calls. |

No file outside `B2B_BE/` is touched. No `B2B_FE/` file is read or written. No model, repository, tool,
migration, or API route is added — none is needed for this narrow a slice (see Technical Context).

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: FR-6 confirmation-rendering domain logic

**Description:** Add `ResolvedBookingCandidate` (Pydantic: `service_name: str`, `start_time: datetime`,
`staff_name: str` — all required, since by the time this function runs, staff assignment is assumed
already resolved by upstream, not-yet-built logic) and `render_direct_confirmation(candidate) -> str`,
which formats a human-readable confirmation string naming the service, date/time, and staff member, and
ends with an explicit yes/no confirmation question. No DB access, no repository, no model.

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/app/domain/appointments.py` — `ResolvedBookingCandidate` model + `render_direct_confirmation()`.

**Dependencies:** None.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 2: Booking Agent direct-confirmation stub

**Description:** Add `app/agent/booking_agent.py` (named in the enforced tree, does not exist yet),
exposing `DirectConfirmationPrompt` (Pydantic: `message: str`, `awaiting_confirmation: bool = True`) and
`confirm_exact_match(candidate: ResolvedBookingCandidate) -> DirectConfirmationPrompt`, which calls Task
1's rendering function and returns the prompt. `awaiting_confirmation=True` is the explicit signal a future
caller must check before any Booking write proceeds — directly satisfying FR-6's "asks for explicit
confirmation before creating the booking." This module is explicitly a stub: it is not wired into any
chat endpoint, LLM provider call, or conversation-state persistence (none of which exist in the repo yet),
mirroring `manager_agent.py`'s existing stub pattern.

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/app/agent/booking_agent.py` — `DirectConfirmationPrompt` + `confirm_exact_match()`.

**Dependencies:** Task 1.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

## External Dependencies

- None. No new third-party packages — `pydantic` is already in `B2B_BE/pyproject.toml`. No database,
  migration, or external service is touched.

---

## Testing Strategy

**Unit and integration test-writing is intentionally out of scope for this cycle, by explicit user
instruction** (batch/time-constrained delivery; bypass to be recorded in Jira separately from this plan).
No test tasks are planned above, and none should be added during implementation.

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | Not planned this cycle | `pytest` (available, not invoked for new coverage here) |
| Integration | Not planned this cycle | `pytest` against real Postgres (available, not invoked for new coverage here) |

Minimum coverage expectation: none beyond what already exists, which this ticket does not touch or
regress.

---

## Security Considerations

No new attack surface: both new functions are pure, in-process computations with no DB access, no
external call, and no LLM-callable tool registration. Pydantic validates the shape of
`ResolvedBookingCandidate` at construction (standard type/shape validation, consistent with the
happy-flow-only scope) — no deep defensive handling is added.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| No chat endpoint, LLM loop, intent-parsing (FR-5), staff-preference limiting (FR-13), SM-4a checkpoint, or availability check exists yet, so FR-6 can only be demonstrated at the function level, not end-to-end in a live conversation | High | Med | Explicitly scoped as a stub/hook point, per the same pattern as APPOINTMEN-17; called out here and in Out of Scope rather than silently claimed as end-to-end done. |
| `ResolvedBookingCandidate`'s shape may need to change once Story 2.2/2.3 and APPOINTMEN-13 land (e.g. typed `service_id`/`staff_id` instead of names) | Med | Low | Kept intentionally minimal (names only, no IDs) since no Service/Staff-with-ID-lookup path exists yet from the Booking Agent side; documented here as expected to be revisited, not final. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — FR-6 confirmation-rendering domain logic | `Low` |
| Task 2 — Booking Agent direct-confirmation stub | `Low` |
| **Overall** | `Low` |

---

## Out of Scope

- **Unit tests and integration tests** — explicitly not written this cycle, per direct user instruction
  (to be recorded as a bypass note in Jira, separately from this plan; this plan does not edit any
  workflow/orchestration file to reflect that bypass).
- **Service/Booking/Availability entities and the full shared-data-store buildout (APPOINTMEN-13 / Story
  1.1)** — no new model, repository, migration, or table. `ResolvedBookingCandidate` takes plain
  service/staff names and a datetime, not references to any persisted entity.
- **Booking-intent parsing (Story 2.2 / FR-5)** — extracting service, date/time, and staff preference from
  free text is not built here; this ticket assumes a resolved candidate is already available.
- **Staff-preference limiting (Story 2.3 / FR-13)** — not built; this ticket does not decide who is a
  valid/bookable staff member.
- **Staff auto-assignment when the Customer did not name one** — the ticket's own tuple is `(service, exact
  datetime, optional staff)`; by the time `confirm_exact_match()` is called, staff assignment (named or
  auto-assigned) is assumed already resolved upstream. No auto-assignment logic is built here.
- **The SM-4a human-verification checkpoint (Story 2.4)** — not built; not wired as a precondition here.
- **Availability checking / conflict detection (FR-7, FR-8, FR-26, `check_conflicts`)** — the candidate is
  assumed already known-available by the caller; no Availability lookup or conflict check runs in this
  ticket.
- **Actual Booking creation** — no write occurs; the Booking entity/table does not exist yet
  (APPOINTMEN-13). `awaiting_confirmation` only signals that a write must not proceed without it.
- **A working chat endpoint, WebSocket surface, or LLM provider integration** — `app/api/chat.py` and any
  LLM tool-calling wiring do not exist yet and are not created by this ticket; `confirm_exact_match()` is a
  callable function, not a reachable endpoint.
- **Conversation-state persistence** (`messages` table / `app/agent/state/`) — not touched.
- **WhatsApp-channel behavior** — not addressed; this is channel-agnostic rendering logic only, with no
  channel adapter wired to it yet.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-22` · Branch: `feature/APPOINTMEN-22-exact-time-direct-confirm`*
