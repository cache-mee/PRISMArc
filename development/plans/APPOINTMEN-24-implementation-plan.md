# Implementation Plan: Exact-Time-Unavailable Resolution — Nearest Alternative(s) (FR-8)

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-24` |
| Type | `Story` (label: `backend`) |
| Branch | `feature/APPOINTMEN-24-exact-time-unavailable-alternatives` |
| Assigned to | `unassigned` |
| Scope | `B2B_BE/` only — pure Booking Agent/service logic, no UI change (see Business Context) |

---

## Overview

Add the FR-8 mechanism: when a Customer's exact requested date/time turns out to be unavailable for
the relevant staff (or, if no staff was named, unavailable salon-wide), the Booking Agent states *why*
(already booked vs. blocked) and names at least one nearest alternative slot within the same
staff-preference constraint (or salon-wide otherwise). This is a domain function plus a supporting pair
of repository queries and an agent-layer hook point — the same layering `confirm_exact_match` (FR-6,
APPOINTMEN-22) already established — reusing the FR-26 conflict-check mechanism
(`app/domain/conflicts.py::check_conflicts`, already merged to `develop`) rather than re-deriving
"is this staff member already booked at this time" a second time.

---

## Business Context

Jira description (APPOINTMEN-24, verbatim): *"As a Customer whose exact requested time is unavailable, I
want the Booking Agent to suggest the nearest alternative(s) with a reason, so I can still get booked
without re-stating my whole request."*

**Acceptance Criteria (FR-8):**
- The agent names at least one alternative slot when one exists within the same Staff-preference
  constraint (or salon-wide if none was stated).
- The agent's response states the reason the original time is unavailable (e.g., already booked,
  blocked).

Epic artefact confirmation (`bmad-output/planning-artifacts/epics/epics-salon-app-2026-09-17.md`, Story
2.7): dependencies are Story 2.2 (FR-5, intent parsing — `app/agent/booking_intent.py`, already merged),
Story 2.3 (FR-13, staff preference limited to bookable staff — **not yet merged to `develop`**, see
Technical Context), Story 2.4 (SM-4a human-verification checkpoint — a build-time/demo mechanism, no
Customer-visible UI), and Story 1.1 (Availability/Booking entities — already merged). Story 2.7 does
**not** list Story 2.6 (FR-7, day-only slot listing / APPOINTMEN-23) as a dependency, despite the
superficial similarity ("listing slots") — FR-7 solves a different sub-problem (day-named, no time
stated) and is a separate, independently-sequenced, currently-unmerged ticket. This plan does not depend
on or reuse anything from it.

UX spec (`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/customer-booking-chat.md` §3.3):
> **FR-8 — exact time unavailable (nearest alternative):**
> 1. Customer states service + exact time that turns out to be unavailable.
> 2. Agent names the reason, then offers alternative(s): *"Meena's 11am Saturday is already booked.
>    She's free at 1:00 PM or 2:30 PM Saturday — want one of these?"*
> 3. Customer selects an alternative (or types it) → proceeds to §3.4 (FR-9 confirmation).

The Customer-facing outcome delivered here: a rejected exact-time request never dead-ends the
conversation — it always comes back with a reason plus a concrete, bookable alternative, without asking
the Customer to restate their service/staff preference.

---

## Technical Context

Stack: FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2, per `stack/rules/base-rules.md`. Follows the
existing domain/repository split already used by `app/domain/appointments.py` (FR-6/FR-9) and
`app/domain/conflicts.py` (FR-26).

**Branch-staleness finding (must be resolved before Task 2 below, not silently worked around):** this
worktree's branch is currently 15 commits behind `origin/develop`. Among the commits missing are
`APPOINTMEN-31` (merged via PR #27), which added exactly the mechanism this ticket needs to reuse:
- `app/domain/conflicts.py` — `check_conflicts(db, *, staff_id, window_start, window_end)` →
  `ConflictCheckResult` (`has_conflict`, `conflicting_bookings`). This is the "already booked" half of
  FR-8's reason determination.
- `app/repositories/bookings.py` — `get_bookings_for_staff_in_window(db, *, staff_id, window_start,
  window_end)`, the query `check_conflicts` calls.

Neither file exists on this branch today. Task 1 below is to sync the branch with `origin/develop`
(merge or rebase — Developer's call, not prescribed here) before writing any new code, so this ticket
reuses the already-merged FR-26 mechanism instead of re-implementing "does this staff member have an
existing booking in this window" a second time under a different name.

**FR-13 (Story 2.3, staff-preference-limited-to-bookable-staff) is also not merged anywhere** (its own
feature branch, `feature/APPOINTMEN-20-23-fr-13-staff-preference-limited-to`, contains no unique commits
ahead of `develop` — it appears abandoned/stale, not in-flight). FR-8's AC needs a "salon-wide" search
scope (no staff named) that must exclude Ramesh (`Staff.role == StaffRole.OWNER_ADMIN`, "never bookable
per PRD Decision 1" — `stack/rules/base-rules.md` Database tables section). This plan adds only the
narrow query FR-8 itself needs (`list_bookable_staff`, Task 3) — it does **not** attempt to deliver
Story 2.3/FR-13's full scope (e.g., validating/rejecting a Customer-stated staff preference at
intent-parse time in `app/agent/booking_intent.py`), which is a separate, not-yet-scoped ticket.

**Reason determination and alternative search — new logic, since nothing in the codebase computes
either today.** `ResolvedBookingCandidate` (FR-6, APPOINTMEN-22) and `confirm_and_create_booking` (FR-9,
APPOINTMEN-26) both explicitly assume availability was "already resolved by upstream (not-yet-built)
logic." FR-8 is that "what if it wasn't available" branch, so this ticket is the first to actually
perform the determination:

- **"Already booked" reason:** `check_conflicts(db, staff_id=..., window_start=requested_time,
  window_end=requested_time + _SLOT_GRANULARITY)` (FR-26, reused as-is). `_SLOT_GRANULARITY` (a new
  `timedelta(minutes=30)` module constant) stands in for a per-service duration, since `Booking` has no
  `end_time`/duration column — the same accepted, documented gap FR-26's own plan already recorded ("a
  true interval-overlap check is not possible today"). Not re-litigated or fixed here.
- **"Blocked" reason:** no existing query checks the `availability` table (FR-27's staff block/unblock
  windows) for overlap with an arbitrary requested time — `app/repositories/availability.py` currently
  only has `create_availability`. Task 2 adds the read side this ticket needs:
  `get_blocking_availability_for_staff_in_window(db, *, staff_id, window_start, window_end)`, mirroring
  `get_bookings_for_staff_in_window`'s shape exactly.
- **Nearest-alternative search — hardcoded business-hours window, an explicit, documented
  simplification, not a modeled entity:** no working-hours/business-hours concept exists anywhere in the
  domain model (`stack/rules/base-rules.md`'s Database tables list has no such table, and no PRD/epic
  artefact defines one). This plan bounds the search to the same calendar day as `requested_time`,
  between two new module constants (`_BUSINESS_HOURS_START = time(9, 0)`, `_BUSINESS_HOURS_END =
  time(19, 0)`), stepping outward from `requested_time` in `_SLOT_GRANULARITY` increments (alternating
  earlier/later) until up to `_MAX_ALTERNATIVES = 2` free slots are found (2, to match the UX spec's own
  two-option example) or the business-hours bound is exhausted. This is flagged as a Risk below, not
  silently assumed — an Architect decision to model real salon/staff hours would supersede these
  constants.
- **Salon-wide (no staff preference) reason attribution:** when multiple bookable staff are candidates,
  this plan reports `already_booked` if *any* candidate staff has a conflicting booking at the exact
  requested time (more specific/actionable to the Customer than "blocked"), else `blocked` if all
  remaining candidates are blocked there. Documented as a deliberate simplification for the hackathon's
  happy-flow-only scope (`stack/rules/base-rules.md` Testing Requirements) — not a claim that every
  bookable staff member's individual reason is surfaced.

**Layering (mirrors FR-6's `ResolvedBookingCandidate` / `render_direct_confirmation` /
`confirm_exact_match` split exactly):**
`app/repositories/availability.py`, `app/repositories/staff_repository.py` (new queries) →
`app/domain/appointments.py` (new `AlternativeSlot` / `NearestAlternativesResult` models,
`find_nearest_alternatives()`, `render_alternative_slots()`) → `app/agent/booking_agent.py` (new
`present_nearest_alternatives()` hook point).

**One deliberate divergence from `confirm_exact_match`'s shape, stated explicitly:** `confirm_exact_match`
is synchronous and operates on an already-resolved `ResolvedBookingCandidate` — it does no DB work.
`find_nearest_alternatives()` (and its agent-layer wrapper) must be `async def` and take an `AsyncSession`,
because — unlike FR-6 — nothing upstream can hand this ticket a pre-resolved alternative; performing that
resolution against `bookings`/`availability`/`staff` is exactly this ticket's job.

**No live conversational loop exists to call any of this yet** — same accepted gap already documented by
APPOINTMEN-22/APPOINTMEN-26 (no chat endpoint wires `booking_intent.py` → `booking_agent.py` → a
resolution branch today). This ticket adds the callable mechanism and its hook point, not a live call
site.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/repositories/availability.py` | Modify | Add `get_blocking_availability_for_staff_in_window` — the "blocked" half of the reason determination. |
| `B2B_BE/app/repositories/staff_repository.py` | Modify | Add `list_bookable_staff` — the salon-wide candidate-staff set (excludes `StaffRole.OWNER_ADMIN`). |
| `B2B_BE/app/domain/appointments.py` | Modify | Add `AlternativeSlot`, `UnavailabilityReason`, `NearestAlternativesResult`, `find_nearest_alternatives()`, `render_alternative_slots()` — the FR-8 mechanism, alongside the existing FR-6/FR-9 booking-resolution logic already in this file. |
| `B2B_BE/app/agent/booking_agent.py` | Modify | Add `present_nearest_alternatives()` — the hook point a future conversational Booking Agent loop calls, mirroring `confirm_exact_match`; extend the module docstring to list this third FR alongside FR-1/FR-6. |

No file outside `B2B_BE/` is touched. No `B2B_FE/` file is read or written — this ticket's AC is pure
Booking Agent/service logic with no stated or implied UI change (the UX spec's "slot-choice chips" are
existing `B2B_FE/` component scope, not this ticket's).

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: Sync feature branch with `origin/develop`

**Description:** Merge or rebase `origin/develop` into this feature branch before writing any new code,
so `app/domain/conflicts.py` (`check_conflicts`) and `app/repositories/bookings.py`
(`get_bookings_for_staff_in_window`) — both merged via PR #27 (APPOINTMEN-31, FR-26) — are present on
the branch. Without this, Task 4 would either fail to import them or re-implement conflict detection
under a new name, duplicating FR-26's mechanism.

**Files to modify:** None (branch-history operation only; no source edit).

**New files to create:** None

**Dependencies:** None

**Complexity:** `Low`

**Testing requirements:**
- After syncing, `app/domain/conflicts.py` and `get_bookings_for_staff_in_window` (in
  `app/repositories/bookings.py`) exist on the branch and import cleanly.

---

### Task 2: Repository query — blocked-availability windows for a staff member

**Description:** Add `get_blocking_availability_for_staff_in_window(db, *, staff_id, window_start,
window_end)` to `app/repositories/availability.py`. Returns all `Availability` rows for `staff_id` where
`blocked is True` and the row's `[start_time, end_time)` overlaps `[window_start, window_end)`, ordered
by `start_time`. Mirrors `get_bookings_for_staff_in_window`'s shape (FR-26) exactly, applied to the
`availability` table instead of `bookings`.

**Files to modify:**
- `B2B_BE/app/repositories/availability.py`

**New files to create:** None

**Dependencies:** None

**Complexity:** `Low`

**Testing requirements:**
- Staff with one blocked window overlapping the query window, one non-overlapping — only the
  overlapping one returned.
- An unblocked (`blocked=False`) `Availability` row inside the window is never returned.

---

### Task 3: Repository query — bookable staff for salon-wide search

**Description:** Add `list_bookable_staff(db)` to `app/repositories/staff_repository.py`. Returns all
`Staff` rows where `role != StaffRole.OWNER_ADMIN`, ordered by `name` (mirrors
`app/repositories/services.py::list_services`'s shape). Used only when the Customer stated no staff
preference — narrow scope, not a general staff-preference validator (see Technical Context re: FR-13).

**Files to modify:**
- `B2B_BE/app/repositories/staff_repository.py`

**New files to create:** None

**Dependencies:** None

**Complexity:** `Low`

**Testing requirements:**
- A `Staff` set containing one `OWNER_ADMIN` and two `STAFF` rows returns only the two `STAFF` rows,
  ordered by name.

---

### Task 4: `find_nearest_alternatives` — the FR-8 mechanism

**Description:** Extend `app/domain/appointments.py` with:
- `class UnavailabilityReason(str, Enum)`: `ALREADY_BOOKED = "already_booked"`, `BLOCKED = "blocked"`.
- `class AlternativeSlot(BaseModel)`: `staff_name: str`, `start_time: datetime`.
- `class NearestAlternativesResult(BaseModel)`: `requested_time: datetime`, `staff_name: str | None`
  (the stated preference, or `None` for salon-wide), `reason: UnavailabilityReason`,
  `alternatives: list[AlternativeSlot]`.
- `class NoAlternativeSlotFoundError(ValueError)`: raised only if the bounded business-hours search
  (see Technical Context) finds zero free slots — an explicit typed failure rather than returning an
  empty, misleading "success" result; not a defensive edge-case taxonomy, just not silently lying about
  the AC's "at least one" guarantee when it cannot be met.
- `async def find_nearest_alternatives(db, *, service_name: str, requested_time: datetime, staff_name:
  str | None = None) -> NearestAlternativesResult`:
  1. Resolve the candidate staff set: `staff_name` given → `[get_staff_by_name(db, staff_name)]`,
     raising the existing `StaffNotFoundError` if no match (reuses the exact exception
     `confirm_and_create_booking` already raises for the same failure mode); `staff_name` is `None` →
     `list_bookable_staff(db)` (Task 3).
  2. Determine `reason` for `requested_time` against the candidate set: `check_conflicts` (FR-26, via
     Task 1) first (`ALREADY_BOOKED` if any candidate has a conflict), else
     `get_blocking_availability_for_staff_in_window` (Task 2) (`BLOCKED` if all remaining candidates are
     blocked there). See Technical Context for the salon-wide attribution rule when candidates disagree.
  3. Search for alternatives: step outward from `requested_time` in `_SLOT_GRANULARITY` increments
     (alternating earlier/later), bounded to `[_BUSINESS_HOURS_START, _BUSINESS_HOURS_END)` on
     `requested_time`'s calendar date, checking each candidate staff member at each step against both
     Task 1's `check_conflicts` and Task 2's blocking-availability query; collect free `(staff, time)`
     pairs into `AlternativeSlot`s, nearest-first, up to `_MAX_ALTERNATIVES`.
  4. Raise `NoAlternativeSlotFoundError` if the search exhausts the business-hours bound with zero
     alternatives found; otherwise return the populated `NearestAlternativesResult`.

**Files to modify:**
- `B2B_BE/app/domain/appointments.py`

**New files to create:** None

**Dependencies:** Task 1, Task 2, Task 3.

**Complexity:** `Medium`

**Testing requirements:**
- Named staff, already booked at the exact time → `reason=ALREADY_BOOKED`, at least one alternative
  returned for that same staff member only.
- Named staff, blocked (not booked) at the exact time → `reason=BLOCKED`.
- No staff named, all bookable staff booked/blocked at the exact time but at least one free nearby →
  alternatives drawn from more than one staff member if that is where the nearest free slots are.
- Named staff not found → `StaffNotFoundError`.
- No free slot anywhere in the business-hours bound → `NoAlternativeSlotFoundError`.

---

### Task 5: `render_alternative_slots` — message rendering

**Description:** Add `render_alternative_slots(result: NearestAlternativesResult, service_name: str) ->
str` to `app/domain/appointments.py`, mirroring `render_direct_confirmation`'s and
`render_conflict_message`'s existing style (plain, human-readable sentences — no chip/UI markup, which
belongs to `B2B_FE/`, out of scope here). States the reason in plain language (e.g. "already booked" /
"blocked") and names every `AlternativeSlot` in `result.alternatives`, matching the UX spec's example
phrasing ("...is already booked. She's free at 1:00 PM or 2:30 PM Saturday — want one of these?").

**Files to modify:**
- `B2B_BE/app/domain/appointments.py`

**New files to create:** None

**Dependencies:** Task 4.

**Complexity:** `Low`

**Testing requirements:**
- Message names the stated reason exactly once and every alternative slot (not just the first) when
  more than one exists.
- Message reads correctly with exactly one alternative (singular phrasing, no trailing "or").

---

### Task 6: `present_nearest_alternatives` — Booking Agent hook point

**Description:** Extend `app/agent/booking_agent.py` with `async def present_nearest_alternatives(db,
*, service_name: str, requested_time: datetime, staff_name: str | None = None) -> str`, calling Task 4's
`find_nearest_alternatives` then Task 5's `render_alternative_slots` and returning the resulting message.
This is the FR-8 counterpart to the existing `confirm_exact_match` (FR-6) — the hook point a future
conversational Booking Agent loop calls once intent parsing (FR-5) and the SM-4a checkpoint have
determined the named exact time did not resolve directly. Extend the module's top docstring (which
currently enumerates `handle_message` for FR-1 and `confirm_exact_match` for FR-6) to also describe this
third piece, consistent with the file's existing documentation convention. No wiring into a live
conversational loop — none exists yet (see Technical Context).

**Files to modify:**
- `B2B_BE/app/agent/booking_agent.py`

**New files to create:** None

**Dependencies:** Task 4, Task 5.

**Complexity:** `Low`

**Testing requirements:**
- Given a `NearestAlternativesResult`-producing scenario (via Task 4), the returned string contains both
  the stated reason and every alternative slot's time.

---

## External Dependencies

- **PostgreSQL**, reachable via `DATABASE_URL` — already provisioned (APPOINTMEN-12). Available now.
- **`origin/develop`'s FR-26 mechanism** (`app/domain/conflicts.py::check_conflicts`,
  `app/repositories/bookings.py::get_bookings_for_staff_in_window`, merged via PR #27) — available on
  `origin/develop` today, but **not yet on this feature branch** (Task 1 is the prerequisite sync; see
  Technical Context).
- **No new third-party packages.** `sqlalchemy`, `pydantic` are already in `B2B_BE/pyproject.toml`.
- **Story 2.3 / FR-13** (staff-preference validation against the bookable-staff set) — not built anywhere
  yet; this plan does not wait for it and adds only the narrow `list_bookable_staff` query it needs
  itself (see Technical Context).
- **Story 2.6 / FR-7 / APPOINTMEN-23** (day-only slot listing) — separate, unmerged, not a dependency of
  this ticket per the epic artefact; not reused here.

---

## Testing Strategy

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | `find_nearest_alternatives` (reason determination: already-booked / blocked / staff-not-found; alternative search: named-staff-only vs. salon-wide; exhaustion → `NoAlternativeSlotFoundError`) and `render_alternative_slots` | `pytest` |
| Integration | `get_blocking_availability_for_staff_in_window` and `list_bookable_staff` against a real Postgres (window-overlap and role-exclusion correctness) | `pytest` + `docker-compose` Postgres |

Minimum coverage expectation, per `stack/rules/base-rules.md` Testing Requirements: the PRD is
happy-flow-only for this hackathon build, and FR-8 is not itself one of the three top-priority
confirm-before-write behaviors (FR-9/FR-18/FR-27) nor the FR-26 conflict-detection mechanism directly —
but it is a direct new caller of that priority-#2 mechanism, so its own reason-determination path is
worth the same "everything else, time permitting" priority-3 attention, ahead of exhaustive edge-case
coverage (zero-availability salon-wide, malformed input) that base-rules explicitly says is not required.

**Per this run's current configuration** (sdlc-dev-workflow only; no unit-test/QA workflow chaining until
the user resumes it — recorded project instruction), actual test files are not written in this
implementation cycle. The scenarios above are the target coverage once that workflow resumes, and are
flagged here so they are not silently dropped, mirroring how APPOINTMEN-31's plan flagged the same
priority-#2 adjacency.

---

## Security Considerations

None beyond the project's existing baseline (no auth boundary in this build, per PRD §7). No new input
surface: `find_nearest_alternatives` takes already-validated internal values (a resolved `staff_name` or
`None`, a `datetime`), not raw user input — the same posture `check_conflicts` already documents for
itself.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Branch is 15 commits behind `origin/develop`, missing the FR-26 mechanism this ticket reuses | High (confirmed) | Medium | Task 1 — sync before any new code is written. |
| No working-hours/business-hours entity exists; alternative search uses hardcoded module constants (`09:00`–`19:00`, same calendar day) | Medium | Low–Medium | Documented explicitly here and in code comments, not silently assumed; an Architect decision to model real salon/staff hours would supersede these constants without changing `find_nearest_alternatives`'s external contract. |
| `Booking` has no `end_time`/duration (inherited FR-26 gap) — conflict/free-slot checks use a fixed `_SLOT_GRANULARITY` approximation, not true per-service duration | High (known, inherited) | Medium | Same accepted scope boundary FR-26's own plan already recorded; not fixed here. |
| Salon-wide reason attribution (already-booked prioritized over blocked when candidates disagree) is a simplification, not a per-staff breakdown | Low | Low | Acceptable for happy-flow-only scope; documented in Technical Context. |
| No live conversational loop calls `present_nearest_alternatives` yet | Medium (expected) | Low | Same accepted gap as APPOINTMEN-22/26; function is unit-testable in isolation regardless of caller. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — Sync branch with `origin/develop` | `Low` |
| Task 2 — Blocked-availability repository query | `Low` |
| Task 3 — Bookable-staff repository query | `Low` |
| Task 4 — `find_nearest_alternatives` domain mechanism | `Medium` |
| Task 5 — `render_alternative_slots` message rendering | `Low` |
| Task 6 — `present_nearest_alternatives` Booking Agent hook | `Low` |
| **Overall** | `Medium` |

---

## Out of Scope

- **Actually booking the chosen alternative.** Once a Customer picks an alternative, wiring it into a
  `ResolvedBookingCandidate` + `confirm_exact_match` (FR-6) → `confirm_and_create_booking` (FR-9,
  APPOINTMEN-26) is future conversational-loop work — this ticket only produces and presents the
  alternative(s), consistent with the UX spec's own step boundary ("→ proceeds to §3.4").
- **Story 2.6 / FR-7 / APPOINTMEN-23** (day-only slot listing) — separate, unmerged ticket; not a
  dependency of FR-8 per the epic artefact, not reused here.
- **Story 2.8 / SM-4b** (human-verification checkpoint on the alternative-slot reasoning before it is
  offered) — a separate build-time/demo mechanism ticket; zero Customer-visible UI either way, and this
  plan does not add any operator-facing hook for it.
- **Story 2.3 / FR-13's full scope** (validating/rejecting a Customer-stated staff preference at
  intent-parse time) — this plan adds only the narrow `list_bookable_staff` query FR-8 itself needs, not
  a general staff-preference validator.
- **Adding a working-hours/business-hours domain entity or table.** Hardcoded module constants are used
  instead (see Risks) — revisiting this is an Architect decision, not made here.
- **Adding `end_time`/duration to `Booking` or a `Service`-duration lookup** for a true interval-overlap
  conflict check — inherited FR-26 scope boundary, not revisited here.
- **Any `B2B_FE/` change** — no UI change is stated or implied by this ticket's AC; the UX spec's
  "slot-choice chips" affordance is existing `B2B_FE/` component scope.
- **A live conversational Booking Agent loop** wiring FR-5 → FR-6/FR-7/FR-8 branch selection — no chat
  endpoint or LLM tool-calling loop exists anywhere in the repo yet (same gap already documented by
  APPOINTMEN-14/22/26); this ticket adds the callable mechanism and hook point, not its live call site.
- **Unit/integration test-writing itself** — deferred per this run's current configuration (see Testing
  Strategy); scenarios are specified above for when that workflow resumes.
- **WhatsApp-channel-specific behavior** — this is channel-agnostic domain/agent logic only, consistent
  with the base-rules "channel logic stays a thin adapter" constraint.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-24` · Branch: `feature/APPOINTMEN-24-exact-time-unavailable-alternatives`*
