# Implementation Plan: Staff Preference Limited to Bookable Staff (FR-13)

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-20` |
| Type | `Story` (label: `backend`) |
| Branch | `feature/APPOINTMEN-20-23-fr-13-staff-preference-limited-to` |
| Assigned to | `sparc.team_25@experionglobal.com` |

---

## Overview

Enforce PRD FR-13 / epics.md Story 2.3: a Customer's optional staff preference (parsed by
`parse_booking_intent`, APPOINTMEN-19 / Story 2.2, FR-5) must only ever resolve to a Staff member who
actually takes appointments — currently Meena and Arjun — and must never resolve to Ramesh, who is seeded
as `role = owner_admin` and is confirmed non-bookable (PRD §9.1 Decision 1; `stack/rules/base-rules.md`
Database tables). This plan adds a single, reusable "bookable staff" query at the repository layer, a
tool-layer wrapper exposing bookable staff names, and validation in `parse_booking_intent` that silently
drops (never raises on) a stated preference that does not match a bookable staff name — matching the
ticket's explicit instruction that an unmatched preference (e.g. "Ramesh") is a known, unmodeled limitation,
not a rejection flow to build.

---

## Business Context

From the ticket (verbatim): *"As a Customer, I want my staff preference limited to staff who actually take
appointments, so I only get offered a provider who can be booked."*

**Acceptance Criteria (PRD FR-13 Consequences, epics.md Story 2.3):**
- Only Meena and Arjun are accepted/offered as a staff preference; Ramesh is never offered or accepted
  (PRD §9.1 Decision 1).
- A stated preference for "Ramesh" as a service provider is a known, unmodeled limitation in this
  happy-flow-only demo — no rejection flow or error path is built for it.

User-facing outcome: when a Customer names a staff member in free text, the Booking Agent only ever
treats that as a valid preference if the named person can actually be booked. Naming Ramesh does not
crash or produce a bespoke "Ramesh isn't bookable" message (that flow is explicitly not being built) — it
simply does not resolve to a valid staff preference, exactly as if no preference had been stated at all.

---

## Technical Context

Stack: FastAPI + SQLAlchemy + Alembic + PostgreSQL, per `stack/rules/base-rules.md`.

**What already exists (verified by reading the current worktree), and is reused, not reinvented:**
- `B2B_BE/app/models/staff.py` — `Staff` model with `role: StaffRole` (`OWNER_ADMIN` | `STAFF`). Seed data
  (`B2B_BE/alembic/versions/8aac3e937d39_seed_staff_records.py`) confirms Ramesh = `owner_admin`, Meena and
  Arjun = `staff`. This is the existing, authoritative signal for "bookable" — no new column or table is
  needed.
- `B2B_BE/app/repositories/staff_repository.py` — `get_staff_by_phone_number`, `get_staff_by_name`. Neither
  filters by role today; both are left untouched (used elsewhere, e.g. `app/domain/appointments.py`'s
  `confirm_and_create_booking`, for resolving an *already-agreed* staff name to an ID after FR-13 has
  already limited what could be agreed to).
- `B2B_BE/app/tools/staff.py` — existing tool-layer pattern: a Pydantic result model + an `async def` tool
  function that calls a repository function, never touching the DB directly from the tool. Mirrored here.
- `B2B_BE/app/tools/services.py` / `B2B_BE/app/repositories/services.py` — the closest existing analogue
  (`get_service_catalog(session)` wrapping `list_services(session)`): a tool function that takes an
  explicit `AsyncSession` argument (rather than opening its own `SessionLocal`, which
  `resolve_staff_identity` does instead, since that one has no request-scoped session available to it).
  This plan follows the `get_service_catalog` shape, since a bookable-staff listing is the same kind of
  read-only, request-scoped lookup as the service catalog.
- `B2B_BE/app/agent/booking_intent.py` (APPOINTMEN-19) — `parse_booking_intent(text, *, known_services,
  now=None)` already has the exact pattern this ticket extends: `known_services: list[str]` is a
  caller-supplied hook-point argument (no live caller/conversation loop exists yet — same documented gap
  as APPOINTMEN-22's `confirm_exact_match`), the system prompt names the known catalog to the LLM, and
  `_resolve_known_service` does a case-insensitive match against it after extraction. `staff_preference` is
  currently extracted with **no validation at all** — this is the exact gap FR-13 closes.

**Design decision — filter by `role`, not by a hardcoded name list.** Both "offering" (a future slot-list
render, Story 2.6/FR-7, not yet built) and "accepting" (this ticket's `parse_booking_intent` validation)
must agree on one definition of "bookable staff." That definition already exists in the schema
(`role != owner_admin`) per `base-rules.md`'s own domain-model note ("Ramesh is a `staff` row with `role =
owner_admin` ... never bookable"). Filtering by `role` here — rather than hardcoding `["Meena", "Arjun"]` —
means this logic stays correct if the seeded roster ever changes, and it is the same query any future
offering call site will need, so it is added once, at the repository layer, as the single source of truth.

**Layering:**
1. `app/repositories/staff_repository.py` — add `list_bookable_staff(db) -> list[Staff]`, filtering
   `Staff.role == StaffRole.STAFF`. Pure data-access, matching the existing two functions in this file.
2. `app/tools/staff.py` — add `list_bookable_staff_names(session) -> list[str]`, wrapping (1) and returning
   just the names, matching the `get_service_catalog` shape. This is the piece a future Booking Agent turn
   loop will call to build the `known_staff` list passed into `parse_booking_intent`, and is also the
   natural future call site for FR-7's "offered" slot-list filtering — this ticket does not build FR-7
   itself, only the shared query it will need.
3. `app/agent/booking_intent.py` — extend `parse_booking_intent` with a new `known_staff: list[str]`
   keyword argument (default `[]`, same optional-hook-point shape as `known_services`), extend the system
   prompt to name the known bookable staff to the LLM, and add `_resolve_known_staff`, a case-insensitive
   matcher mirroring `_resolve_known_service` but that returns `None` (never raises) on no match — since
   `staff_preference` is optional and an unmatched name (including "Ramesh") is a known, unmodeled
   limitation, not an error condition.

No model, migration, or API route is added or changed. No `B2B_FE/` file is read or written.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/repositories/staff_repository.py` | Modify | Add `list_bookable_staff(db)` — the single "bookable staff" query (`role != owner_admin`), reused by both the tool layer and (in future) any offering logic. |
| `B2B_BE/app/tools/staff.py` | Modify | Add `list_bookable_staff_names(session)` tool wrapper, mirroring the existing `get_service_catalog` pattern in `app/tools/services.py`. |
| `B2B_BE/app/agent/booking_intent.py` | Modify | Add `known_staff` parameter, prompt update, and `_resolve_known_staff` to `parse_booking_intent` so an extracted `staff_preference` is only accepted when it matches a bookable staff name; otherwise silently dropped to `None`. |

No file outside `B2B_BE/` is touched. No `B2B_FE/` file is read or written. No model, repository schema
change, migration, or API route is added.

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: Bookable-staff repository query

**Description:** Add `list_bookable_staff(db: AsyncSession) -> list[Staff]` to
`app/repositories/staff_repository.py`, querying `Staff` where `role == StaffRole.STAFF` (excludes
`OWNER_ADMIN`, i.e. excludes Ramesh), ordered by name for stable output. This is the single enforcement
point for "which staff can be booked," reused by Task 2 and by any future offering logic.

**Files to modify:**
- `B2B_BE/app/repositories/staff_repository.py`

**New files to create:** *(none)*

**Dependencies:** None.

**Complexity:** `Low`

**Testing requirements:**
- Integration test (real Postgres, per `base-rules.md`'s repository-layer testing note) asserting
  `list_bookable_staff` returns exactly Meena and Arjun against the seeded fixture data, and excludes
  Ramesh.

---

### Task 2: Bookable-staff-names tool

**Description:** Add `list_bookable_staff_names(session: AsyncSession) -> list[str]` to
`app/tools/staff.py`, calling Task 1's `list_bookable_staff` and returning just the `name` values —
mirroring `get_service_catalog`'s shape in `app/tools/services.py` (a thin, read-only, tool-layer wrapper
over a repository call, never touching the DB directly). This is the hook point a future Booking Agent
turn loop will call to build `known_staff` for Task 3, and the future call site for FR-7's staff-filtered
slot offering.

**Files to modify:**
- `B2B_BE/app/tools/staff.py`

**New files to create:** *(none)*

**Dependencies:** Task 1.

**Complexity:** `Low`

**Testing requirements:**
- Unit test (mocked/stubbed repository call, matching how `app/tools/services.py`-style tools would be
  tested) asserting the tool returns only bookable staff names in the shape callers expect (`list[str]`).

---

### Task 3: Limit accepted/offered staff preference in intent parsing

**Description:** Extend `parse_booking_intent` in `app/agent/booking_intent.py`:
- Add a `known_staff: list[str]` keyword argument (default `[]`), following the exact optional-hook-point
  shape `known_services` already uses (no live caller/conversation loop exists yet to supply it from Task
  2 — same documented gap as `known_services` itself and as APPOINTMEN-22's `confirm_exact_match`).
- Extend the system prompt to tell the LLM which staff names are bookable (when `known_staff` is
  non-empty) and instruct it to only set `staff_preference` to one of those names, or leave it `null`
  otherwise — mirroring the existing services instruction.
- Add `_resolve_known_staff(staff_preference, known_staff) -> str | None`, a case-insensitive matcher
  mirroring `_resolve_known_service`, but which returns `None` on no match instead of raising — because
  `staff_preference` is optional (per FR-5's own AC) and an unmatched or non-bookable name (including a
  literal "Ramesh") is this ticket's known, unmodeled limitation, not an error condition to surface.
- Apply `_resolve_known_staff` to `intent.staff_preference` before returning `intent`, whenever
  `known_staff` is non-empty. When `known_staff` is empty (no caller has wired it in yet), preserve today's
  behavior unchanged (no filtering) so this stays a strictly additive, backward-compatible change for any
  existing caller.

**Files to modify:**
- `B2B_BE/app/agent/booking_intent.py`

**New files to create:** *(none)*

**Dependencies:** Task 2 (conceptually — `known_staff` is expected to be sourced from
`list_bookable_staff_names` once a real caller exists; Task 3's code change itself has no import-level
dependency on Task 2 and could be implemented/tested independently with a literal list).

**Complexity:** `Medium`

**Testing requirements:**
- Unit test: `staff_preference="Meena"` with `known_staff=["Meena", "Arjun"]` resolves to `"Meena"`
  (accepted).
- Unit test: `staff_preference="Ramesh"` with `known_staff=["Meena", "Arjun"]` resolves to `None` (never
  accepted, never raises).
- Unit test: `staff_preference=None` (no preference stated) is unaffected by `known_staff` filtering.
- Unit test: case-insensitive match (e.g. `"meena"` resolves against known `"Meena"`).
- Unit test: `known_staff=[]` (default / not yet wired) leaves existing behavior unchanged — no filtering
  applied, to confirm backward compatibility with any existing caller.

---

## External Dependencies

- None. No new third-party packages. No database schema change (the existing `staff.role` column is
  sufficient — no migration required).

---

## Testing Strategy

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | `_resolve_known_staff` matching/non-matching/case-insensitivity/empty-list behavior in `parse_booking_intent` (Task 3); shape of `list_bookable_staff_names` (Task 2, repository call stubbed/mocked). | `pytest` |
| Integration | `list_bookable_staff` (Task 1) against a real Postgres instance seeded via the existing Alembic migrations, asserting it returns exactly Meena and Arjun and excludes Ramesh. | `pytest`, real Postgres per `base-rules.md`'s integration-test guidance (repository/DB-layer correctness is not meaningfully verified by a mocked DB). |

Minimum coverage expectation, per `base-rules.md`'s Testing Requirements (happy-flow-only demo; FR-13 is
not in the explicit priority-1/2 list of confirm-before-write/conflict-detection behaviors, so coverage
here is proportionate, not exhaustive): the accept/reject boundary itself (Meena/Arjun accepted, Ramesh
never accepted) must be covered, since that boundary is the entire content of this ticket's acceptance
criteria. **No test is written in this planning phase** — the above states what will be required when
Task 1–3 are implemented and validated.

---

## Security Considerations

None beyond existing baselines. This is read-only filtering logic (a `SELECT ... WHERE role = 'staff'`
query and a client-side-of-the-DB name match) with no new input trusted for a write, no new secret, and no
new authentication/authorization surface. `staff_preference` remains a plain string validated by
`BookingIntent`'s existing Pydantic model; no deep defensive handling is added, consistent with the
happy-flow-only scope.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| No live Booking Agent conversation loop exists yet to actually call `parse_booking_intent` with a real `known_staff` list sourced from Task 2 — so FR-13's "accepted" behavior can only be demonstrated at the function level, not end-to-end in a live conversation, until that loop is built. | High | Med | Explicitly scoped as a hook-point extension, matching the same documented gap `known_services` and APPOINTMEN-22 already carry; called out here and in Out of Scope rather than silently claimed as end-to-end wired. |
| FR-13's "offered" side (filtering a slot-list to bookable staff, FR-7/Story 2.6) is not built by this ticket — Task 2's tool exists but has no caller yet. | Med | Low | Task 2 delivers exactly the shared query FR-7's future implementation will need; not building FR-7 itself here is an explicit, stated scope boundary, not an oversight. |
| Relying on `role` rather than a hardcoded name list means any future change to who counts as `STAFF` vs `OWNER_ADMIN` silently changes bookability. | Low | Low | This is the intended, PRD-aligned behavior (base-rules.md's own domain-model note treats `role` as the authoritative signal) — flagged here as a deliberate design choice, not hidden coupling. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — Bookable-staff repository query | `Low` |
| Task 2 — Bookable-staff-names tool | `Low` |
| Task 3 — Limit accepted/offered staff preference in intent parsing | `Medium` |
| **Overall** | `Low-Medium` |

---

## Out of Scope

- **Writing unit/integration tests in this planning phase** — this plan states what will be required
  (see Testing Strategy); tests are written during implementation, not during planning, per this task's
  explicit instruction.
- **A rejection/error/notification flow for a stated preference of "Ramesh"** — the ticket explicitly
  states this is a known, unmodeled limitation for this happy-flow-only demo, not something to build. A
  non-bookable name silently resolves to `None` (treated as if no preference was stated); no bespoke
  "Ramesh isn't bookable" message, error, or retry prompt is added.
- **FR-7's staff-filtered slot-list rendering (Story 2.6, "offered" side end-to-end)** — not yet built in
  this repo (no slot-listing/offering code exists at all yet). This ticket delivers the shared bookable-
  staff query (Task 1/2) that a future FR-7 implementation will consume; it does not build FR-7 itself.
- **Wiring a live Booking Agent conversation loop** that actually calls `list_bookable_staff_names` to
  build `known_staff` and passes it into `parse_booking_intent` on every turn — no such loop exists yet
  anywhere in the repo (same gap already documented by APPOINTMEN-19 and APPOINTMEN-22); this ticket only
  adds the parameter and its resolution logic, following the same hook-point pattern already established.
- **Any `B2B_FE/` change** — this ticket is backend-only per its `backend` label and per the acceptance
  criteria, which concern service/parsing logic only, not UI.
- **Changing `get_staff_by_name` / `get_staff_by_phone_number`** — both remain role-agnostic by design,
  since they are used elsewhere (`confirm_and_create_booking`, staff identity resolution) to resolve a
  name/phone number *already known* to be valid at that point in the flow; FR-13's limiting happens
  upstream of those lookups, not by changing them.
- **A new DB column, table, or migration** — `staff.role` (already seeded) is sufficient; no schema change
  is needed.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-20` · Branch: `feature/APPOINTMEN-20-23-fr-13-staff-preference-limited-to`*
