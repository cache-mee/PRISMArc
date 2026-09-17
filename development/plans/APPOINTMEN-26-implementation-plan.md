# Implementation Plan: Booking Confirmation and Creation (FR-9)

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-26` |
| Type | `Story` (label: `backend`) |
| Branch | `feature/APPOINTMEN-26-booking-confirmation-creation` |
| Assigned to | `sparc.team25@experionglobal.com` |

---

## Overview

Add the minimum real persistence slice needed to prove FR-9: no `Booking` record exists until a Customer's
explicit confirmation follows a proposed slot. This introduces a `bookings` table/model, a repository
function that inserts a Booking row, and a domain function `confirm_and_create_booking()` that only writes
that row when handed a `DirectConfirmationPrompt` (APPOINTMEN-22, `app/agent/booking_agent.py`) whose
`confirmed` flag is `True` — rejecting the call outright otherwise. This is a narrow slice, following the
same dependency-ordering pattern as APPOINTMEN-17 and APPOINTMEN-22: it does not build the Service or
Availability entities FR-9 nominally sits on top of (still owned by APPOINTMEN-13), and it does not build
the read-side ACs (2.10 query-by-booking, 5.2 Dashboard visibility, 6.1 availability-check reflection) —
those are separate stories that read through the same repository/table this ticket writes.

---

## Business Context

From the ticket (verbatim): *"As a Customer, I want my Booking created only after I explicitly confirm a
proposed slot, so nothing is booked on my behalf without my say-so."*

**AC (FR-9):** *"no Booking record exists until an explicit confirmation follows a proposed slot; once
confirmed, immediately queryable (2.10), visible on Dashboard (5.2), and reflected in any subsequent
availability check (6.1)."*

User-facing outcome: a Customer's slot is never turned into a real Booking without them explicitly saying
yes — and once they do, the write is real and durable (not a stub), so any correctly-built read path
(query, Dashboard, availability check) will see it. This ticket delivers the write; it does not itself
build those read paths.

---

## Technical Context

Stack: FastAPI + SQLAlchemy + Alembic + PostgreSQL, per `stack/rules/base-rules.md`. The enforced backend
tree requires this to land as a model (`app/models/`), a migration (`alembic/versions/`), a repository
(`app/repositories/`), and a domain function (`app/domain/`) — mirroring exactly how `Customer` (APPOINTMEN-15)
and `Staff` (APPOINTMEN-17) were added.

**Dependency-ordering decision (explicit, same pattern as APPOINTMEN-17/22):** the Service and Availability
entities (APPOINTMEN-13 / Story 1.1) that FR-9 nominally depends on still do not exist. Per the established
pattern, this ticket does not wait for them. It builds only the real slice FR-9 itself needs:

- **`service_name` is stored as a plain string column, not a foreign key.** No `Service` entity exists yet.
  This is a deliberate simplification, called out explicitly here so it is reconciled (replaced with a
  `service_id` FK) when APPOINTMEN-13/the Service entity lands — not silently treated as final.
- **`customer_id` is a real FK to `customers.id`** (Customer is now real, merged from APPOINTMEN-15) and
  **`staff_id` is a real FK to `staff.id`** (Staff is real, from APPOINTMEN-17) — both entities already
  exist in this worktree, so both relationships are built as proper foreign keys, not string placeholders.
- **`status` defaults to `"confirmed"`.** By construction, a Booking row is only ever inserted through
  `confirm_and_create_booking()` after confirmation is asserted, so there is no unconfirmed/pending status
  to represent at the DB level yet — a status column is added now (as a plain string, mirroring
  `StaffRole`'s enum-in-a-column pattern would be premature here since there is exactly one value produced
  today) so it exists for future states (e.g. `cancelled`) without a migration churn later.
- **No Availability entity/conflict check.** `confirm_and_create_booking()` trusts that the caller (a
  future conversational Booking Agent loop) has already resolved availability before confirmation was ever
  offered to the Customer — consistent with `ResolvedBookingCandidate`'s existing contract from APPOINTMEN-22
  (assumed-available on construction). No double-booking/conflict detection is added here.

**The FR-9 guarantee itself — "no Booking record exists until an explicit confirmation follows a proposed
slot" — is enforced at the domain layer, not just by convention:** `confirm_and_create_booking()` takes a
`DirectConfirmationPrompt` (APPOINTMEN-22) and raises if `prompt.confirmed` is not `True`, rather than
inserting a row. There is no other code path in the repo that can construct a `Booking` row. This makes the
AC directly demonstrable: calling the function on an unconfirmed prompt is guaranteed to leave the
`bookings` table untouched.

**Deferred read-side work (explicit, out of scope here):** ACs 2.10 (query-by-booking), 5.2 (Dashboard
visibility), and 6.1 (availability-check reflection) all read data this ticket writes. Because the write
goes through a real repository against a real table, those ACs are *structurally* satisfiable once their
own stories build the corresponding read paths — but no query endpoint, Dashboard view, or availability
lookup is built in this ticket. This is a deliberate scope boundary, not an oversight.

Layering follows the enforced tree exactly, same shape as `Customer`/`Staff`: `app/models/booking.py` (new
model) → `app/repositories/bookings.py` (new repository, `create_booking()`) → `app/domain/appointments.py`
(extended with `confirm_and_create_booking()`, alongside the existing `ResolvedBookingCandidate`/
`render_direct_confirmation()` from APPOINTMEN-22) → Alembic migration chained after the latest head
(`1b9376ed1c01_add_customers_table`). No new `app/tools/` file is added — nothing in the existing `app/tools/`
layer calls into booking creation yet (there is no chat endpoint or Booking Agent tool registry to wire it
into), so a tool wrapper today would be unused indirection; this mirrors the same "declared, not silent"
layering call APPOINTMEN-22 made for its own new functions. `app/agent/booking_agent.py` is not modified —
`confirm_and_create_booking()` is the domain-layer hook a future Booking Agent loop calls once it holds a
confirmed `DirectConfirmationPrompt`; wiring that call site does not exist yet since no chat endpoint exists
(same gap already documented by APPOINTMEN-22 and APPOINTMEN-17).

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/models/booking.py` | New | `Booking` ORM model — `customer_id` (FK → `customers.id`), `staff_id` (FK → `staff.id`), `service_name` (plain string, see Technical Context), `start_time`, `status` (defaults to `"confirmed"`), `created_at`. |
| `B2B_BE/app/models/__init__.py` | Modify | Register `Booking` on `Base.metadata` (mirrors how `Customer`/`Staff` were registered). |
| `B2B_BE/alembic/versions/<new>_add_bookings_table.py` | New | Schema migration creating the `bookings` table, chained after `1b9376ed1c01_add_customers_table` (current head). |
| `B2B_BE/app/repositories/bookings.py` | New | `create_booking(db, ...) -> Booking` — the sole DB-insert path for a Booking row. |
| `B2B_BE/app/domain/appointments.py` | Modify | Add `confirm_and_create_booking(db, prompt: DirectConfirmationPrompt) -> Booking`, which rejects unconfirmed prompts and otherwise delegates to the new repository. |

No file outside `B2B_BE/` is touched. No `B2B_FE/` file is read or written. No `app/tools/` or
`app/agent/booking_agent.py` change — see Technical Context for why.

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: `Booking` ORM model

**Description:** Add the `Booking` model: `id` (PK), `customer_id` (FK → `customers.id`, not null),
`staff_id` (FK → `staff.id`, not null), `service_name` (`String`, not null — plain string simplification,
see Technical Context), `start_time` (`DateTime(timezone=True)`, not null), `status` (`String`, not null,
default `"confirmed"`), `created_at` (`DateTime(timezone=True)`, server default `now()`, not null). Register
it in `app/models/__init__.py` so it lands on `Base.metadata`.

**Files to modify:**
- `B2B_BE/app/models/__init__.py`

**New files to create:**
- `B2B_BE/app/models/booking.py` — `Booking` model.

**Dependencies:** None (Customer and Staff models already exist in the worktree).

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 2: `bookings` table migration

**Description:** New Alembic migration creating the `bookings` table with the columns from Task 1, both
foreign keys, and an index on `customer_id` (the expected lookup key for future read-side stories).
Chained after `1b9376ed1c01_add_customers_table` (current head).

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/alembic/versions/<generated-revision-id>_add_bookings_table.py` — exact filename/revision hash
  assigned by running `alembic revision -m "add bookings table"` at implementation time; this plan fixes
  its intent and `down_revision` (`1b9376ed1c01`), not its generated hash.

**Dependencies:** Task 1.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 3: Bookings repository — `create_booking`

**Description:** `app/repositories/bookings.py` — `create_booking(db: Session, *, customer_id: int,
staff_id: int, service_name: str, start_time: datetime, status: str = "confirmed") -> Booking`, doing the
insert and returning the persisted row (mirrors `app/repositories/customers.py::create_customer`'s
commit/refresh pattern). This is the only function in the codebase that inserts a `Booking` row.

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/app/repositories/bookings.py`

**Dependencies:** Task 1.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 4: `confirm_and_create_booking` domain function (the FR-9 gate)

**Description:** Extend `app/domain/appointments.py` with `confirm_and_create_booking(db: Session, prompt:
DirectConfirmationPrompt) -> Booking`. If `prompt.confirmed` is not `True`, raise (`ValueError`, no bare
`except` involved — this is the raise side, not a catch) rather than touching the database at all. If it
is `True`, call Task 3's `create_booking()` with fields taken from `prompt.candidate`
(`ResolvedBookingCandidate`: `service_name`, `start_time`) plus `customer_id`/`staff_id` supplied by the
caller (not yet resolvable from `ResolvedBookingCandidate` alone, which only carries `staff_name` — the
caller, i.e. a future Booking Agent loop, is expected to already hold the resolved `customer_id`/`staff_id`
by the time it calls this function). This function is the single place FR-9's guarantee is enforced:
"no Booking record exists until an explicit confirmation follows a proposed slot" is testable directly by
asserting no row is written when `confirmed=False`, and a row is written when `confirmed=True`.

**Files to modify:**
- `B2B_BE/app/domain/appointments.py`

**New files to create:** *(none)*

**Dependencies:** Task 3.

**Complexity:** `Low`

---

## External Dependencies

- **PostgreSQL**, reachable via `DATABASE_URL` — already provisioned (APPOINTMEN-12). Available now.
- **No new third-party packages.** `sqlalchemy`, `alembic`, `pydantic` are already in `B2B_BE/pyproject.toml`.
- **APPOINTMEN-13 (Service/Availability entities)** — nominal dependency, still not implemented. This plan
  does not wait for it; see the `service_name`-as-string simplification and no-conflict-check note in
  Technical Context for exactly what is deferred.
- **APPOINTMEN-22's `DirectConfirmationPrompt`/`ResolvedBookingCandidate`** (`app/agent/booking_agent.py`,
  `app/domain/appointments.py`) — already merged into `develop` and present in this worktree; this ticket
  consumes them as-is, without modification.

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

No new attack surface beyond what already exists for `Customer`/`Staff` writes: `create_booking()` is a
plain parameterized SQLAlchemy insert (no raw SQL, no string interpolation). `confirm_and_create_booking()`
is the sole gate on writing a Booking row and is itself a defensive check (rejects on `confirmed=False`),
directly implementing the ticket's core requirement rather than merely documenting it.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `service_name` as a plain string (no `Service` FK) will need to be replaced with `service_id` once APPOINTMEN-13 lands, requiring a follow-up migration and possibly a data-backfill decision | Med | Low | Called out explicitly in Technical Context and here rather than left implicit; additive migration expected, not a rewrite of this one. |
| No Availability/conflict check means two confirmed prompts for an overlapping slot could both be written | Med | Low | Out of scope per FR-9 itself (conflict detection is FR-7/FR-8/FR-26, a separate story); `ResolvedBookingCandidate` already documents availability as assumed-resolved upstream — this ticket does not change or relax that assumption. |
| ACs 2.10/5.2/6.1 cannot be end-to-end demonstrated (no query endpoint, Dashboard, or availability-check exists) | High | Med | Explicitly scoped as write-side only, per Technical Context and Out of Scope; the read paths are separate, not-yet-built stories that will read through this same repository/table. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — `Booking` ORM model | `Low` |
| Task 2 — `bookings` table migration | `Low` |
| Task 3 — Bookings repository (`create_booking`) | `Low` |
| Task 4 — `confirm_and_create_booking` domain function | `Low` |
| **Overall** | `Low` |

---

## Out of Scope

- **Unit tests and integration tests** — explicitly not written this cycle, per direct user instruction
  (to be recorded as a bypass note in Jira, separately from this plan; this plan does not edit any
  workflow/orchestration file to reflect that bypass).
- **Service and Availability entities (APPOINTMEN-13 / Story 1.1)** — no `services` or `availability`
  table; `service_name` remains a plain string column on `bookings` until that ticket lands (see Technical
  Context).
- **AC 2.10 — query-by-booking** — no read/query endpoint or repository lookup-by-id function is added for
  Booking; this ticket only writes. A future story reads through the same table.
- **AC 5.2 — Dashboard visibility** — no Dashboard, API route, or `B2B_FE/` change of any kind. Out of the
  backend/frontend split entirely for this ticket per its `backend` label.
- **AC 6.1 — availability-check reflection** — no availability-check logic exists yet (depends on
  APPOINTMEN-13); not built or stubbed here.
- **Availability/conflict detection (FR-7, FR-8, FR-26)** — `confirm_and_create_booking()` trusts the
  caller that the slot was already available; no double-booking check is added.
- **Booking cancellation, rescheduling, or any status transition beyond the initial `"confirmed"` insert**
  — `status` exists as a column for future use but no transition logic is built here.
- **A working chat endpoint, LLM tool registration, or wiring `confirm_and_create_booking()` into
  `app/agent/booking_agent.py`'s conversational flow** — no chat endpoint or LLM loop exists anywhere in
  the repo yet (same gap already documented by APPOINTMEN-17/22); this ticket adds the callable domain
  function, not its live call site.
- **WhatsApp-channel behavior** — channel-agnostic persistence logic only.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-26` · Branch: `feature/APPOINTMEN-26-booking-confirmation-creation`*
