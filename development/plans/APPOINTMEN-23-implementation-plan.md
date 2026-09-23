# Implementation Plan: FR-7 Day-only resolution — list that day's available slots

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-23` |
| Type | `Story` |
| Branch | `feature/APPOINTMEN-23-day-only-available-slots` |
| Assigned to | `unassigned` |

---

## Overview

When a Customer names a day but no specific time (e.g. "Thursday afternoon"), the Booking Agent must
list that day's actually-open slots so the Customer can pick one — never a slot that is blocked or
already booked, and, if a staff preference was stated, never a slot belonging to a different staff
member. This ticket builds the first real "compute open slots" logic in the codebase: a domain function
that queries `Availability` and `Booking` rows for the relevant bookable staff on a given day, resolves
each candidate slot's open/blocked/booked state, and renders the result into a Customer-facing message,
plus a Booking Agent hook function (`list_day_slots`) that exposes it — mirroring the hook-point pattern
already established by FR-6 (`confirm_exact_match`, APPOINTMEN-22) for a not-yet-built conversational
loop.

---

## Business Context

Per the Jira ticket description: *"As a Customer who named a day but no specific time, I want the
Booking Agent to list that day's available slots, so I can pick one."*

Acceptance criteria (FR-7, PRD §4.1):
- "The listed slots reflect only currently open Availability for the relevant Staff member(s) at the
  time of the request (excludes blocked time and already-booked Slots)."
- "If a Staff preference was stated, only that Staff member's open slots are listed."

User-facing outcome: a Customer who is vague about time still gets a concrete, bookable list of options
in the same turn, without the agent guessing a single time that might not be open (realizes UJ-1, PRD
§2.3).

---

## Technical Context

**Layering** follows the fixed convention already in place (`stack/rules/base-rules.md` — Architecture
Constraints, enforced tree under `B2B_BE/app/`): `agent/` → `domain/` → `repositories/`. No new API
route, LLM-callable tool, or DB table is introduced — this mirrors Story 2.5/FR-6's actual shape
(`app/agent/booking_agent.py::confirm_exact_match`, APPOINTMEN-22): a domain function plus an agent
hook-point function, not wired into a conversational loop that doesn't exist yet.

**Already-resolved inputs, same posture as FR-6.** `ResolvedBookingCandidate`
(`app/domain/appointments.py`) is explicitly documented as assuming "availability and staff assignment
are assumed already resolved by upstream (not-yet-built) logic." No dispatcher exists yet that decides,
from a `BookingIntent` (`app/agent/booking_intent.py`), whether the Customer's stated time has day-only
or exact-time precision — that decision belongs to a future conversational-loop story (Story 2.4's
dependency chain), not this one. This plan's hook function therefore takes an already-resolved `day:
date` and optional `staff_name: str | None` directly, exactly the same posture `ResolvedBookingCandidate`
takes for FR-6. Building the day/exact-time dispatch decision itself is out of scope (see Out of Scope).

**What must actually be built here, unlike FR-6.** FR-6's ticket could stub real availability-checking
because its AC only required a confirmation message for an already-resolved candidate. FR-7's AC
explicitly requires the listed slots to reflect *real* open/blocked/booked state — so, unlike FR-6, this
ticket must build the actual query/filter logic against `Availability` and `Booking`, not stub it.

**Domain-model gap this ticket must resolve with a documented assumption.** No working-hours, slot-
duration, or Service-duration concept exists anywhere in the code or PRD (`app/models/service.py` has no
duration column; `app/models/booking.py` has a single `start_time`, no `end_time`; `addendum.md` §3 item
3 explicitly leaves the data model "Architect-phase starting points, not locked"). Two minimal, explicitly
documented assumptions are introduced to make slot enumeration possible at all (flagged in Risks below
for confirmation at Gate 3, not silently guessed past):
1. **Slot grid.** A fixed salon-operating-hours window (09:00–18:00) and slot granularity (30 minutes)
   are added as module-level constants in `app/domain/availability.py` — not a config/env value, since
   this is a business rule with no existing settings precedent, and not a new DB entity, since the PRD's
   happy-flow-only scope (`stack/rules/base-rules.md` Testing Requirements) does not ask for a
   configurable per-salon schedule.
2. **Block/unblock resolution.** `Availability` rows are the append-only audit trail FR-27
   (`confirm_and_apply_availability_change`) already writes (`blocked=True` for a block, `blocked=False`
   for an unblock). A staff member is treated as blocked at a given instant when the most-recently-
   created `Availability` row whose `[start_time, end_time)` window covers that instant has
   `blocked=True`; with no covering row at all, the instant is open by default (consistent with UJ-4:
   Meena's Friday-morning block is meaningful precisely because she was open by default beforehand).
3. **Booked-slot exclusion.** Because `Booking` carries no duration, a slot is treated as booked only
   when an existing `Booking` with `status="confirmed"` has `start_time` exactly equal to that slot's
   start — the same single-time-field granularity already used everywhere else in the codebase.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/repositories/staff_repository.py` | Modify | Add `list_bookable_staff` to fetch all non-owner/admin `Staff` rows (salon-wide listing, FR-13's exclusion of Ramesh). |
| `B2B_BE/app/repositories/availability.py` | Modify | Add `list_availability_for_staff_on_day` to fetch the `Availability` rows relevant to computing a day's open/blocked state. |
| `B2B_BE/app/repositories/bookings.py` | Modify | Add `list_confirmed_bookings_for_staff_on_day` to fetch the day's confirmed `Booking` rows for exclusion. |
| `B2B_BE/app/domain/availability.py` | Modify | Add `OpenSlot`, the slot-grid/block-state pure helpers, `list_open_slots_for_day`, and `render_day_slot_list` — the actual FR-7 logic. |
| `B2B_BE/app/agent/booking_agent.py` | Modify | Add `list_day_slots` hook function, mirroring `confirm_exact_match`'s pattern for FR-6. |
| `B2B_BE/tests/test_availability_day_slots.py` | New | Unit coverage for the domain-layer slot-grid, block-state, and orchestration logic. |
| `B2B_BE/tests/test_booking_agent.py` | New | Unit coverage for the new `list_day_slots` hook function. |

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: Add day-scoped repository query helpers

**Description:** Add the three read-only repository functions needed to gather the raw data
`list_open_slots_for_day` will filter: which staff are bookable, what `Availability` rows exist for a
staff member overlapping a given day, and what confirmed `Booking`s exist for a staff member on that
day. All three are additive, read-only functions alongside existing repository functions — no existing
function signature changes.

**Files to modify:**
- `B2B_BE/app/repositories/staff_repository.py`
- `B2B_BE/app/repositories/availability.py`
- `B2B_BE/app/repositories/bookings.py`

**New files to create:** None

**Dependencies:** None

**Complexity:** `Low`

**Testing requirements:**
- No dedicated test for these thin query functions in this task — consistent with the existing repo
  convention (`create_availability`, `create_booking`, `get_staff_by_name` have no direct unit tests
  either) and with `stack/rules/base-rules.md`'s Testing Requirements priority order, which puts
  everything outside the confirm-before-write/conflict-detection paths at "time permitting." Correctness
  of these three functions is exercised indirectly through Task 3's orchestration tests (with the
  repository calls mocked) and, if a Postgres instance is available, manually via `docker compose up`
  (see Testing Strategy).

---

### Task 2: Add pure slot-grid and block-state resolution helpers

**Description:** Add two private, DB-independent pure functions to `app/domain/availability.py`:
`_generate_slot_grid(day: date) -> list[datetime]` (every slot-duration boundary between the salon's
opening and closing hour on `day`) and `_is_blocked_at(rows: Sequence[Availability], instant: datetime)
-> bool` (resolves the latest-created-row-wins block/unblock state described in Technical Context). These
carry the actual business-rule risk flagged in Risks below, so they are isolated as pure functions
specifically so they can be exhaustively unit-tested without any DB dependency.

**Files to modify:**
- `B2B_BE/app/domain/availability.py`

**New files to create:** None

**Dependencies:** None

**Complexity:** `Medium`

**Testing requirements:**
- `_generate_slot_grid`: produces the expected number of slots at the expected boundaries for the fixed
  09:00–18:00/30-minute constants; does not produce a slot at or after closing time.
- `_is_blocked_at`: no covering `Availability` row → open (not blocked); one covering `blocked=True` row
  → blocked; a covering `blocked=True` row followed by a later-created covering `blocked=False` row →
  open (unblock supersedes); a covering row that does not actually span the instant → ignored.

---

### Task 3: Add `OpenSlot`, `list_open_slots_for_day`, and `render_day_slot_list`

**Description:** Add the `OpenSlot` Pydantic model (`staff_name: str`, `start_time: datetime`) and the
orchestration function `list_open_slots_for_day(db, day, staff_name=None) -> list[OpenSlot]`, which:
resolves candidate staff (a single named staff via `get_staff_by_name`, restricted to
`StaffRole.STAFF`, raising the existing `StaffNotFoundError` — reused from `app.domain.appointments`,
the same reuse pattern FR-27's `confirm_and_apply_availability_change` already follows — if unmatched or
not bookable; otherwise all bookable staff via the new `list_bookable_staff`); for each candidate staff,
builds the day's slot grid (Task 2), excludes slots blocked per `_is_blocked_at` against that staff's
`Availability` rows (Task 1), and excludes slots matching a confirmed `Booking`'s `start_time` (Task 1);
returns the remaining `OpenSlot`s sorted by `start_time` then `staff_name`. Also adds
`render_day_slot_list(day, slots) -> str`, the Customer-facing rendering (mirrors
`render_direct_confirmation`'s shape in `app/domain/appointments.py`), including a minimal literal
fallback string when `slots` is empty.

**Files to modify:**
- `B2B_BE/app/domain/availability.py`

**New files to create:** None

**Dependencies:** Task 1, Task 2

**Complexity:** `Medium`

**Testing requirements:**
- Salon-wide listing (no `staff_name`) returns only bookable staff's open slots, excluding a blocked
  window and excluding a slot matching an existing confirmed `Booking`.
- A stated `staff_name` limits the result to that staff member only (FR-7's second AC).
- An unresolvable or non-bookable `staff_name` raises `StaffNotFoundError`.
- `render_day_slot_list` names the day and each slot's time/staff; the empty-list case renders the
  fallback string rather than an empty message.
- Repository calls are mocked/monkeypatched (per `unittest.mock`) so this task's tests exercise
  orchestration logic only, independent of Task 1's actual query correctness — consistent with there
  being no DB test fixture in this codebase yet (see Testing Strategy). Async functions are invoked via
  `asyncio.run(...)` inside plain `pytest` test functions, avoiding a new `pytest-asyncio` dependency
  (there is no existing precedent for it in `pyproject.toml`).

---

### Task 4: Add the `list_day_slots` Booking Agent hook function

**Description:** Add `list_day_slots(db, day, staff_name=None)` to `app/agent/booking_agent.py`,
mirroring `confirm_exact_match`'s hook-point shape for FR-6: it calls
`app.domain.availability.list_open_slots_for_day`, renders the result with `render_day_slot_list`, and
returns a small `DaySlotListing` model (`day`, `slots`, `message`) for a future conversational loop to
consume. Not wired into `handle_message` — same explicitly-documented, not-yet-connected posture the
module's docstring already states for `confirm_exact_match`.

**Files to modify:**
- `B2B_BE/app/agent/booking_agent.py`

**New files to create:** None

**Dependencies:** Task 3

**Complexity:** `Low`

**Testing requirements:**
- `list_day_slots` calls into `list_open_slots_for_day` and `render_day_slot_list` (mocked) and returns
  a `DaySlotListing` carrying their results unchanged — this task tests wiring only, not the
  already-covered domain logic underneath it.

---

## External Dependencies

- No new third-party package is required for the application code (Task 2/3's pure-function design
  deliberately avoids needing `pytest-asyncio`).
- A running Postgres instance (via `docker compose up`, per `stack/rules/base-rules.md` Stack table) is
  needed for any manual/integration-level verification of Task 1's actual SQL against real data; not
  available in this planning/implementation environment, so Task 1 will be validated at the unit level
  only (via Task 3's mocked orchestration tests) and reported as *not validated* at the integration
  level, per `CLAUDE.md`'s instruction to report "not validated" rather than inventing evidence.
- No other team's in-flight work is depended on. FR-8 (nearest alternative, not yet built) and the
  conversational dispatch/routing logic are both independent of this ticket, per Technical Context above.

---

## Testing Strategy

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | `_generate_slot_grid`, `_is_blocked_at` (Task 2); `list_open_slots_for_day`, `render_day_slot_list` with repositories mocked (Task 3); `list_day_slots` with the domain layer mocked (Task 4) | `pytest`, run from `B2B_BE/` (`stack/rules/base-rules.md` Testing Requirements) |
| Integration | Task 1's repository functions against a real Postgres via `docker-compose` | Not executed in this environment — no Postgres instance available; reported as *not validated* rather than assumed passing, per `stack/rules/base-rules.md`'s stated preference for integration tests hitting a real DB where DB write-ordering/correctness is at stake. FR-7 is a read-only path, not one of the two priority items (confirm-before-write, conflict-detection) `base-rules.md` calls out, so this gap is accepted as "time permitting" rather than blocking. |
| End-to-End | Not applicable — no conversational loop exists yet to drive this end-to-end (see Technical Context); would be exercised once the future dispatch story wires `list_day_slots` into `handle_message`. | n/a |

Minimum coverage expectation: every new pure function and orchestration function gets at least one
success-path unit test and, where the AC states an exclusion (blocked, booked, staff-filtered), at least
one test proving the exclusion actually happens — consistent with `stack/rules/base-rules.md`'s
happy-flow-only bar (no exhaustive edge-case/defensive test matrix is expected).

---

## Security Considerations

No new authentication, authorization, or secrets-handling surface. `list_bookable_staff`'s exclusion of
`StaffRole.OWNER_ADMIN` is the same business-level filter FR-13 already establishes elsewhere (not a
security boundary — per `stack/rules/base-rules.md` Security Baselines, role-scoping in this codebase is
explicitly "not a hard security boundary"). No new input crosses a trust boundary: `day` and
`staff_name` are treated here exactly as `ResolvedBookingCandidate.staff_name`/`start_time` already are
elsewhere — plain function arguments from an already-resolved caller, not raw external input.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The 09:00–18:00/30-minute slot grid is an assumption, not a sourced requirement — the real salon hours/granularity may differ. | `Med` | `Med` | Documented explicitly as module-level constants with a comment naming this as an assumption; flagged here for confirmation at Gate 3 (Plan Review) before implementation proceeds. |
| The "latest-created-row-wins" block/unblock resolution rule is this plan's own interpretation of the `Availability` audit-trail shape, not an explicit PRD/architecture statement. | `Med` | `Med` | Documented explicitly in Technical Context; consistent with UJ-4's "open by default until blocked" framing; flagged for confirmation at Gate 3. |
| `Booking` has no duration, so booked-slot exclusion is exact-start-time-only; a service that actually spans multiple slot-grid slots would not correctly block its later slots. | `Low` | `Med` | Documented assumption matching the rest of the codebase's single-time-field treatment of bookings; not a regression this ticket introduces — recorded, not fixed, per Developer scope discipline (no `Booking.end_time`/`Service.duration` migration is in this ticket's scope). |
| No DB test fixture (Postgres or otherwise) exists in this repo for domain-layer tests; Task 1's actual SQL correctness is unverified beyond manual/mocked coverage. | `Med` | `Low` | Accepted per `stack/rules/base-rules.md`'s explicit "time permitting" tier for non-write, non-conflict-detection paths; reported as *not validated* at the integration level rather than claimed as tested. |
| `list_day_slots` has no caller yet (no conversational dispatch loop exists) — the feature is not customer-reachable until a future story wires it in, same as FR-6 today. | `Low` | `Low` | Matches the already-accepted FR-6 precedent (APPOINTMEN-22); not a regression or gap unique to this ticket. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — Repository query helpers | `Low` |
| Task 2 — Pure slot-grid/block-state helpers | `Medium` |
| Task 3 — `list_open_slots_for_day` / `render_day_slot_list` | `Medium` |
| Task 4 — `list_day_slots` Booking Agent hook | `Low` |
| **Overall** | `Medium` |

---

## Out of Scope

- **FR-6 (exact-time direct confirmation, APPOINTMEN-22)** and **FR-8 (nearest-alternative resolution)** —
  already-merged and not-yet-built respectively; this ticket touches neither's behavior.
- **FR-9 (booking confirmation and creation, APPOINTMEN-26)** — this ticket only lists candidate slots;
  it creates no `Booking` row and calls none of `confirm_and_create_booking`'s write path.
- **The conversational dispatch/routing decision** of whether a Customer's stated time is day-only vs.
  exact vs. unavailable — not built by any story yet; `list_day_slots`/`list_open_slots_for_day` take an
  already-resolved `day`/`staff_name`, exactly like FR-6's `ResolvedBookingCandidate`.
- **Any new HTTP API route or LLM-callable tool registration** — not required by the AC; matches FR-6's
  own shape (domain function + agent hook only).
- **A real, configurable, per-salon operating-hours or per-service duration model** — a fixed constant is
  introduced only to make slot enumeration possible now; a proper settings/entity-backed model is future,
  Architect-owned work (flagged in Risks).
- **FR-13's staff-preference acceptance/validation at the intent-parsing layer (Story 2.3)** — this
  ticket defensively rejects an unresolved/non-bookable `staff_name` via `StaffNotFoundError`, but does
  not build the upstream UX that prevents such a name from reaching this function in the first place.
- **FR-11/FR-12 (cancel/reschedule freeing a slot)** — not yet built; this ticket's booked-slot exclusion
  only considers currently-modeled `status="confirmed"` `Booking` rows.
- **Any dedicated zero-availability UX beyond a single literal fallback string** — explicitly a known,
  unhandled limitation per the PRD's happy-flow-only scope (§6.2).
- **Frontend/UI (`B2B_FE/`)** — this ticket is classified backend-only; no frontend file is read or
  written.
- **Chained unit-test/QA workflows** beyond this ticket's own Developer-phase tests — per current
  workflow configuration, `sdlc-dev-workflow` runs standalone here without invoking the separate
  unit-test/QA workflows.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-23` · Branch: `feature/APPOINTMEN-23-day-only-available-slots`*
