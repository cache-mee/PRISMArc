# Implementation Plan: Confirmation Required Before an Availability Change Applies (FR-27)

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-33` |
| Type | `Story` (label: `backend`) |
| Branch | `feature/APPOINTMEN-33-availability-change-confirmation` |
| Assigned to | `sparc.team25@experionglobal.com` |

---

## Overview

Add the minimum real persistence slice needed to prove FR-27: no `Availability` record exists until Meena or
Arjun's explicit confirmation follows the agent's restated block/unblock change. This introduces an
`availability` table/model (the entity itself does not exist anywhere in the repo yet), a repository
function that inserts an Availability row, and a domain function `confirm_and_apply_availability_change()`
that only writes that row when handed a `ProposedAvailabilityChange` whose `confirmed` flag is `True` —
rejecting the call otherwise. This is a narrow slice, following the exact dependency-ordering pattern
APPOINTMEN-26 used for the analogous Booking write-gate: it does not build the NL-parsing, conflict-check,
or human-verification-checkpoint stories (3.1/3.2/3.3) this ticket nominally sits on top of, and it does not
build the read-side ACs (2.6/2.7 Booking Agent reflection, 5.2 Dashboard visibility) — those read through
the same table/repository this ticket writes.

---

## Business Context

From the ticket (verbatim): *"As Meena or Arjun, I want no block/unblock to apply until I've explicitly
confirmed the agent's restated version, so nothing changes on my schedule without my say-so."*

**AC (FR-27):** *"availability record unchanged if the conversation ends before confirmation; once
confirmed and applied, immediately reflected in the Booking Agent's next check (2.6/2.7) and the Dashboard
(5.2), no separate sync step."*

User-facing outcome: a Staff member's block/unblock request never changes their schedule without them
explicitly confirming the agent's restated version — and once they do, the write is real and durable (not a
stub), so any correctly-built read path (Booking Agent availability check, Dashboard) sees it immediately,
with no separate sync step required. This ticket delivers the write-gate; it does not itself build those
read paths or the upstream conversational steps that produce a proposed change.

---

## Technical Context

Stack: FastAPI + SQLAlchemy + Alembic + PostgreSQL, per `stack/rules/base-rules.md`. The enforced backend
tree requires this to land as a model (`app/models/`), a migration (`alembic/versions/`), a repository
(`app/repositories/`), and a domain function (`app/domain/`) — mirroring exactly how `Booking`
(APPOINTMEN-26) was added, and how `Availability` is documented in `base-rules.md`'s domain model
(`availability` table name, singular-noun-as-uncountable, not pluralized further).

**Dependency-ordering decision (explicit, same pattern as APPOINTMEN-26):** Epic 3 (Staff Availability
Management, Stories 3.1–3.7 / APPOINTMEN-30..36) has not been implemented at all, including this ticket's
own nominal dependencies:

- **Story 3.1 (state availability change in NL)** — no NL parsing of a block/unblock request exists. This
  ticket does not build it; it takes an already-parsed `ProposedAvailabilityChange` as input, exactly as
  APPOINTMEN-26's `confirm_and_create_booking()` took an already-resolved `DirectConfirmationPrompt`.
- **Story 3.2 (conflict check)** — `base-rules.md` documents `check_conflicts` (`app/domain/conflicts.py`)
  as a mandatory, two-layered mechanism for a **later** ticket. It is not built or stubbed here, and
  `confirm_and_apply_availability_change()` does not call it — this write-gate trusts that any conflict
  check has already happened upstream before confirmation was ever offered, matching how
  `confirm_and_create_booking()` already trusts `ResolvedBookingCandidate`'s assumed-available contract.
- **Story 3.3 (SM-4c human-verification checkpoint)** — the "agent restates the change and asks for
  explicit confirmation" conversational step is not built here. `ProposedAvailabilityChange.confirmed`
  is the flag a future SM-4c implementation must set to `True` before calling this ticket's gate function,
  mirroring `DirectConfirmationPrompt.confirmed`'s existing role for FR-9/FR-6.

This ticket is therefore the **first** to introduce the `Availability` entity at all, ahead of Story 1.1's
nominal full shared-data-store buildout (APPOINTMEN-13) — narrowly scoped to exactly what FR-27's write-gate
needs: `staff_id` (FK), a `start_time`/`end_time` window, and a `blocked: bool` flag (not an enum/status
string — block/unblock is inherently binary, unlike `Booking.status`, which was kept open-ended for future
states). No validation that `end_time` is strictly after `start_time` is added — deferred to Story 3.1/3.2,
which is expected to already produce a sane window before confirmation is ever offered.

**`ProposedAvailabilityChange` carries `staff_name`, not `staff_id`** — mirroring
`ResolvedBookingCandidate`'s existing shape exactly — and `confirm_and_apply_availability_change()` resolves
`staff_id` via the existing `get_staff_by_name()` (`app/repositories/staff_repository.py`, added by
APPOINTMEN-26), reusing it as-is rather than adding a second lookup path. It reuses the existing
`StaffNotFoundError` (`app/domain/appointments.py`) for the same failure mode, rather than defining a
duplicate exception type for an identical condition — a new `AvailabilityChangeNotConfirmedError` is added
locally for the confirmation-gate failure, mirroring `BookingNotConfirmedError`.

**The FR-27 guarantee itself — "availability record unchanged if the conversation ends before
confirmation" — is enforced at the domain layer, not just by convention:**
`confirm_and_apply_availability_change()` raises `AvailabilityChangeNotConfirmedError` if
`change.confirmed` is not `True`, rather than inserting a row. There is no other code path in the repo that
can construct an `Availability` row. This makes the AC directly demonstrable: calling the function on an
unconfirmed change is guaranteed to leave the `availability` table untouched.

**Deferred read-side work (explicit, out of scope here):** ACs 2.6/2.7 (Booking Agent's next availability
check reflecting the change) and 5.2 (Dashboard visibility) both read data this ticket writes. Because the
write goes through a real repository against a real table, those ACs are *structurally* satisfiable once
their own stories build the corresponding read paths — but no availability-check lookup, Dashboard view, or
API route is built in this ticket. Same reasoning APPOINTMEN-26's plan used for its own deferred read-side
ACs (2.10/5.2/6.1).

Layering follows the enforced tree exactly, same shape as `Booking`: `app/models/availability.py` (new
model, `app.models.base.Base`) → `app/repositories/availability.py` (new repository,
`create_availability()`) → `app/domain/availability.py` (new domain module: `ProposedAvailabilityChange`,
`AvailabilityChangeNotConfirmedError`, `confirm_and_apply_availability_change()`) → Alembic migration
chained after the latest head of the `app.models.base.Base` chain, `c8354b5d4b5c_add_bookings_table`. No
new `app/tools/` file and no `app/agent/manager_agent.py`/`app/agent/booking_agent.py` change — no chat
endpoint or conversational loop exists yet to wire the gate function into (same gap already documented by
APPOINTMEN-17/22/26), and no Story 3.1/3.3 module exists yet to produce a `ProposedAvailabilityChange` for
this gate to consume.

**Observed, out-of-scope, pre-existing inconsistency (not touched by this ticket):** `app/models/service.py`
uses a separate `app.db.Base` rather than `app.models.base.Base` used by `Staff`/`Customer`/`Booking`, and
`alembic/versions/0001_create_services_table.py` is a second migration head (`down_revision = None`)
disconnected from the `Staff`/`Customer`/`Booking` chain. `Availability` joins the `app.models.base.Base`
chain (matching `Staff`/`Customer`/`Booking`), consistent with this ticket's own scope; the `Service`
inconsistency is recorded here as an observation, not fixed.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/models/availability.py` | New | `Availability` ORM model — `staff_id` (FK → `staff.id`), `start_time`, `end_time`, `blocked` (bool), `created_at`. |
| `B2B_BE/app/models/__init__.py` | Modify | Register `Availability` on `Base.metadata` (mirrors how `Booking`/`Customer`/`Staff` were registered). |
| `B2B_BE/alembic/versions/<new>_add_availability_table.py` | New | Schema migration creating the `availability` table, chained after `c8354b5d4b5c_add_bookings_table` (current head of this chain). |
| `B2B_BE/app/repositories/availability.py` | New | `create_availability(db, ...) -> Availability` — the sole DB-insert path for an Availability row. |
| `B2B_BE/app/domain/availability.py` | New | `ProposedAvailabilityChange`, `AvailabilityChangeNotConfirmedError`, and `confirm_and_apply_availability_change(db, change) -> Availability` — the FR-27 gate. |

No file outside `B2B_BE/` is touched. No `B2B_FE/` file is read or written. No `app/tools/` or
`app/agent/` change — see Technical Context for why.

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: `Availability` ORM model

**Description:** Add the `Availability` model: `id` (PK), `staff_id` (FK → `staff.id`, not null, indexed),
`start_time` (`DateTime(timezone=True)`, not null), `end_time` (`DateTime(timezone=True)`, not null),
`blocked` (`Boolean`, not null — `True` for a block, `False` for an unblock), `created_at`
(`DateTime(timezone=True)`, server default `now()`, not null). Register it in `app/models/__init__.py` so it
lands on `Base.metadata`.

**Files to modify:**
- `B2B_BE/app/models/__init__.py`

**New files to create:**
- `B2B_BE/app/models/availability.py` — `Availability` model.

**Dependencies:** None (Staff model already exists in the worktree).

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 2: `availability` table migration

**Description:** New Alembic migration creating the `availability` table with the columns from Task 1, the
`staff_id` foreign key, and an index on `staff_id` (the expected lookup key for the future Booking Agent
availability check and Dashboard read paths). Chained after `c8354b5d4b5c_add_bookings_table` (current head
of the `app.models.base.Base` chain).

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/alembic/versions/<generated-revision-id>_add_availability_table.py` — exact filename/revision
  hash assigned by running `alembic revision -m "add availability table"` at implementation time; this plan
  fixes its intent and `down_revision` (`c8354b5d4b5c`), not its generated hash.

**Dependencies:** Task 1.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 3: Availability repository — `create_availability`

**Description:** `app/repositories/availability.py` — `create_availability(db: Session, *, staff_id: int,
start_time: datetime, end_time: datetime, blocked: bool) -> Availability`, doing the insert and returning
the persisted row (mirrors `app/repositories/bookings.py::create_booking`'s commit/refresh pattern). This is
the only function in the codebase that inserts an `Availability` row.

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/app/repositories/availability.py`

**Dependencies:** Task 1.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 4: `confirm_and_apply_availability_change` domain function (the FR-27 gate)

**Description:** Add `app/domain/availability.py` with:
- `AvailabilityChangeNotConfirmedError(ValueError)` — raised when an Availability write is attempted
  without an explicit confirmation (mirrors `BookingNotConfirmedError`).
- `ProposedAvailabilityChange(BaseModel)` — `staff_name: str`, `start_time: datetime`, `end_time: datetime`,
  `blocked: bool`, `confirmed: bool = False` (mirrors `DirectConfirmationPrompt`'s shape).
- `confirm_and_apply_availability_change(db: Session, change: ProposedAvailabilityChange) -> Availability` —
  if `change.confirmed` is not `True`, raises `AvailabilityChangeNotConfirmedError` rather than touching the
  database at all. If `True`, resolves `staff_id` via the existing `get_staff_by_name()`
  (`app/repositories/staff_repository.py`), raising the existing `StaffNotFoundError`
  (`app/domain/appointments.py`, reused as-is) if no match, then calls Task 3's `create_availability()`.

This function is the single place FR-27's guarantee is enforced: "availability record unchanged if the
conversation ends before confirmation" is testable directly by asserting no row is written when
`confirmed=False`, and a row is written when `confirmed=True`.

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/app/domain/availability.py`

**Dependencies:** Task 3.

**Complexity:** `Low`

---

## External Dependencies

- **PostgreSQL**, reachable via `DATABASE_URL` — already provisioned (APPOINTMEN-12). Available now.
- **No new third-party packages.** `sqlalchemy`, `alembic`, `pydantic` are already in `B2B_BE/pyproject.toml`.
- **Stories 3.1/3.2/3.3 (APPOINTMEN-30/31/32 — NL parsing, conflict check, SM-4c checkpoint)** — nominal
  dependencies, not implemented. This plan does not wait for them; see Technical Context for exactly what
  is deferred and how the gate function's input contract (`ProposedAvailabilityChange.confirmed`) stands in
  for the missing checkpoint.
- **APPOINTMEN-26's `get_staff_by_name()`/`StaffNotFoundError`** (`app/repositories/staff_repository.py`,
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

Minimum coverage expectation: none beyond what already exists, which this ticket does not touch or regress.

---

## Security Considerations

No new attack surface beyond what already exists for `Booking`/`Customer`/`Staff` writes:
`create_availability()` is a plain parameterized SQLAlchemy insert (no raw SQL, no string interpolation).
`confirm_and_apply_availability_change()` is the sole gate on writing an Availability row and is itself a
defensive check (rejects on `confirmed=False`), directly implementing the ticket's core requirement rather
than merely documenting it.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| No conflict check (3.2/`check_conflicts`) means a confirmed change could overlap an existing booking or another availability window | Med | Low | Out of scope per FR-27 itself (conflict detection is Story 3.2, a separate ticket); the gate function does not relax or claim to enforce that check — documented explicitly in Technical Context. |
| No validation that `end_time` is strictly after `start_time` | Low | Low | Deferred to Story 3.1/3.2, expected to produce a sane window before confirmation is offered; not enforced at this layer. |
| ACs 2.6/2.7/5.2 cannot be end-to-end demonstrated (no availability-check lookup, Dashboard, or chat endpoint exists) | High | Med | Explicitly scoped as write-side only, per Technical Context and Out of Scope; the read paths are separate, not-yet-built stories that will read through this same repository/table. |
| `ProposedAvailabilityChange` uses `staff_name`, which will need reconciling once Story 3.1's NL parsing and Story 3.3's checkpoint define their own actual input/output shapes | Med | Low | Kept intentionally minimal and consistent with `ResolvedBookingCandidate`'s existing precedent; documented here as expected to be revisited, not final. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — `Availability` ORM model | `Low` |
| Task 2 — `availability` table migration | `Low` |
| Task 3 — Availability repository (`create_availability`) | `Low` |
| Task 4 — `confirm_and_apply_availability_change` domain function | `Low` |
| **Overall** | `Low` |

---

## Out of Scope

- **Unit tests and integration tests** — explicitly not written this cycle, per direct user instruction (to
  be recorded as a bypass note in Jira, separately from this plan; this plan does not edit any
  workflow/orchestration file to reflect that bypass).
- **Story 3.1 — stating an availability change in natural language** — no NL parsing of a block/unblock
  request; this ticket assumes an already-parsed `ProposedAvailabilityChange` is handed to the gate.
- **Story 3.2 — conflict check (`check_conflicts`, `app/domain/conflicts.py`)** — not built or stubbed here;
  `base-rules.md` flags this as a mandatory two-layered mechanism for a later ticket. Not called by this
  ticket's gate function.
- **Story 3.3 — SM-4c human-verification restatement checkpoint** — the "agent restates the change and asks
  for confirmation" conversational step is not built; `ProposedAvailabilityChange.confirmed` is the flag a
  future implementation of that checkpoint must set.
- **AC 2.6/2.7 — Booking Agent's next availability check reflecting the change** — no availability-check
  lookup exists yet; not built or stubbed here. A future story reads through the same table.
- **AC 5.2 — Dashboard visibility** — no Dashboard, API route, or `B2B_FE/` change of any kind. Out of the
  backend/frontend split entirely for this ticket per its `backend` label.
- **Availability update/cancellation of an existing block/unblock, or overlap resolution between two
  Availability rows** — this ticket only inserts new rows; no update/delete path is added.
- **A working chat endpoint, LLM tool registration, or wiring `confirm_and_apply_availability_change()`
  into `app/agent/manager_agent.py`'s conversational flow** — no chat endpoint or LLM loop exists anywhere in
  the repo yet (same gap already documented by APPOINTMEN-17/22/26); this ticket adds the callable domain
  function, not its live call site.
- **The pre-existing `Service`/`app.db.Base` and second-migration-head inconsistency** — observed in
  Technical Context, not fixed; unrelated to this ticket's scope.
- **WhatsApp-channel behavior** — channel-agnostic persistence logic only.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-33` · Branch: `feature/APPOINTMEN-33-availability-change-confirmation`*
