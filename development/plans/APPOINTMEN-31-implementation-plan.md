# Implementation Plan: Conflict Check Before Applying an Availability Change (FR-26)

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-31` |
| Type | `Story` |
| Branch | `feature/APPOINTMEN-31-32-fr-26-conflict-check-before-applying` |
| Assigned to | `unassigned` |
| Scope | `B2B_BE/` only (Jira label: `backend`) |

---

## Overview

Add the explicit, backend-only conflict-check mechanism required by FR-26: given a staff
member and a proposed availability-block window, determine whether any existing `Booking`
falls inside that window, and if so, return which booking(s) cause the conflict (never a
silent rejection). This is a pure domain function plus a supporting repository query — no
agent wiring, no NL parsing, no write path. Those belong to Story 3.1 (APPOINTMEN-30, not yet
built) and Story 3.4 (apply-the-block, not yet built), which will call into this mechanism
once they exist.

---

## Business Context

Jira description (APPOINTMEN-31):

> As Meena or Arjun, I want the Manager Agent to check my proposed block against existing
> bookings before applying it, so I don't accidentally block time I'm already committed to a
> customer for.
>
> AC (FR-26): if the proposed window contains an existing booking, the agent names which
> booking(s) cause the conflict — not a silent rejection; if no conflict, the block is
> confirmed and applied (Story 3.4).

Epic 3 planning artefact (`bmad-output/planning-artifacts/epics/epics-salon-app-2026-09-17.md`)
confirms Story 3.2's dependencies as Story 3.1 (FR-25) and Story 1.1 (Booking entity), and
states explicitly: "the check logic itself does not require Epic 2 to be 'done.'" — i.e. this
ticket is buildable now, standalone, against the existing `Booking` model.

`stack/rules/base-rules.md` already reserves the target module for this exact ticket:
`app/domain/conflicts.py — explicit conflict-check mechanism (FR-26)`, and names the function
`check_conflicts`, returning "the correct, specific conflicting booking(s) for an overlapping
window."

---

## Technical Context

Stack: FastAPI + SQLAlchemy 2.0 + Pydantic v2 (`B2B_BE/pyproject.toml`). Follows the existing
domain/repository split seen in `app/domain/appointments.py` /
`app/repositories/bookings.py` (FR-9's confirm-then-write precedent): a repository function
does the DB read, a domain function holds the business rule and returns a typed Pydantic
result, with no ORM leakage past the domain layer.

**Known schema gap (accepted, not fixed by this ticket):** `Booking` (`app/models/booking.py`)
has `start_time` but no `end_time`/duration — no `Service` FK to derive one from either. A true
time-window overlap check is therefore not possible today. This plan implements the check as
"does any existing booking's `start_time` fall within `[window_start, window_end)`" — which
satisfies the AC's literal wording ("the proposed window contains an existing booking") without
requiring a `Booking` schema migration or a `Service`-duration lookup, both of which are out of
scope for FR-26. Recorded as a Risk below, not silently assumed.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/repositories/bookings.py` | Modify | Add a query for a staff member's bookings inside a time window |
| `B2B_BE/app/domain/conflicts.py` | New | The FR-26 conflict-check mechanism (`check_conflicts`) and conflict-message rendering |

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: Repository query for a staff member's bookings in a time window

**Description:** Add `get_bookings_for_staff_in_window(db, *, staff_id, window_start,
window_end)` to `app/repositories/bookings.py`. Returns all `Booking` rows for `staff_id` whose
`start_time` is `>= window_start` and `< window_end`, ordered by `start_time`. This is the only
new DB read this ticket needs.

**Files to modify:**
- `B2B_BE/app/repositories/bookings.py`

**New files to create:** None

**Dependencies:** None

**Complexity:** `Low`

**Testing requirements:**
- Unit/integration test scenario (for the follow-up test workflow): staff with one booking
  inside the window, one outside — only the inside one returned.

---

### Task 2: `check_conflicts` domain function (FR-26 mechanism)

**Description:** Create `app/domain/conflicts.py` with:
- `ConflictingBooking` (Pydantic `BaseModel`): `booking_id`, `start_time`, `service_name` —
  enough to name the conflicting booking in a message.
- `ConflictCheckResult` (Pydantic `BaseModel`): `has_conflict: bool`,
  `conflicting_bookings: list[ConflictingBooking]`.
- `check_conflicts(db, *, staff_id, window_start, window_end) -> ConflictCheckResult`: calls
  Task 1's repository function; returns `has_conflict=False` with an empty list if none found,
  else `has_conflict=True` with one entry per conflicting booking. Never raises for the
  "conflict found" case — a conflict is a normal, expected result, not an error (this is what
  "not a silent rejection" in the AC means: the caller always gets the specific booking(s)
  back, never just a boolean).

**Files to modify:** None

**New files to create:**
- `B2B_BE/app/domain/conflicts.py` — FR-26 conflict-check mechanism

**Dependencies:** Task 1

**Complexity:** `Low`

**Testing requirements:**
- No conflict: window with zero matching bookings → `has_conflict=False`, empty list.
- One conflict: single matching booking → `has_conflict=True`, that booking named.
- Multiple conflicts: two matching bookings → both named, in `start_time` order.

---

### Task 3: Conflict message rendering (mirrors FR-6's `render_direct_confirmation` pattern)

**Description:** Add `render_conflict_message(result: ConflictCheckResult) -> str` to
`app/domain/conflicts.py`. For `has_conflict=True`, names each conflicting booking's day/time
and service (matching the AC's own example phrasing style, e.g. "Friday 10am is already booked
with a customer for a haircut"). For `has_conflict=False`, returns a short confirmation-ready
message stating no conflict was found. This is message text only — it does not apply the block
(Story 3.4's job) and is not wired into the Manager Agent's conversation loop, which does not
exist yet (Story 3.1/Manager Agent conversational loop is unbuilt).

**Files to modify:**
- `B2B_BE/app/domain/conflicts.py`

**New files to create:** None

**Dependencies:** Task 2

**Complexity:** `Low`

**Testing requirements:**
- Message names every conflicting booking when `has_conflict=True` (not just the first).
- Message for `has_conflict=False` does not mention any booking.

---

## External Dependencies

- Story 3.1 (APPOINTMEN-30, FR-25 — natural-language extraction of the proposed block window)
  is not yet built. This ticket does not depend on it for the conflict-check logic itself (per
  the epic's own sequencing note) but nothing calls `check_conflicts` from a conversation yet —
  that wiring belongs to Story 3.1/3.4, out of scope here.
- Story 3.4 (FR-27, applying the block) is not yet built — this ticket produces the check only,
  not the write.

---

## Testing Strategy

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | `check_conflicts` (no/one/multiple conflicts) and `render_conflict_message` | `pytest` |
| Integration | `get_bookings_for_staff_in_window` against a real Postgres (window boundary correctness) | `pytest` + `docker-compose` Postgres |

Minimum coverage expectation: per `stack/rules/base-rules.md` Testing Requirements, FR-26's
conflict-detection mechanism is explicitly listed as **priority #2** (after the three
confirm-before-write behaviors) for testing time, ahead of general edge-case coverage — the
PRD is happy-flow-only for this hackathon build.

**Fast-mode note (hackathon time constraint, see project run history):** actual unit tests for
this ticket are deferred to `sdlc-unit-test-workflow`, which this run is configured to skip
chaining into automatically. Given base-rules' own priority ranking above, running the unit-test
workflow for this ticket specifically — even though the general fast-mode default skips it — is
flagged to the user as worth doing before merge, not silently dropped.

---

## Security Considerations

None beyond the project's existing baseline (no auth boundary in this build per PRD §7). No new
input surface — `check_conflicts` takes already-validated internal values (`staff_id`,
datetimes), not raw user input.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| No `end_time`/duration on `Booking` means the check is start-time-in-window, not true interval overlap | High (known gap) | Medium | Documented above as an accepted scope boundary; revisit if/when a `Service`-duration model lands |
| `check_conflicts` never gets called once built, since Story 3.1/3.4 (its only callers) don't exist yet | Medium | Low | Expected for this ticket's scope; function is unit-testable in isolation regardless of caller |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 | `Low` |
| Task 2 | `Low` |
| Task 3 | `Low` |
| **Overall** | `Low` |

---

## Out of Scope

- Story 3.1 (APPOINTMEN-30): natural-language parsing of the proposed block window.
- Story 3.4 (FR-27): actually applying the block/unblock once confirmed.
- Any Manager Agent conversational-loop wiring (none exists yet).
- Adding `end_time`/duration to `Booking` or a `Service`-duration lookup for true interval
  overlap — accepted as a known limitation, not fixed here.
- Unit/integration tests themselves (written under `sdlc-unit-test-workflow`, per this
  workflow's phase boundaries) — though flagged above as high-priority per base-rules.
- The pre-existing `app/models/service.py` vs `app/models/base.py` `Base` inconsistency noticed
  during research — unrelated to this ticket, not touched.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-31` · Branch: `feature/APPOINTMEN-31-32-fr-26-conflict-check-before-applying`*
