# Implementation Plan: Web Chat Staff Identity Resolution (FR-24)

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-17` |
| Type | `Story` (label: `backend`) |
| Branch | `feature/APPOINTMEN-17-staff-identity-resolution` |
| Assigned to | `sparc.team25@experionglobal.com` |

---

## Overview

Give the (not-yet-built) Manager Agent a working, testable capability to resolve *which* pre-seeded
Staff member (Meena or Arjun) is speaking on Web Chat, from a phone number, per PRD FR-24 / epics.md
Story 1.5. This requires standing up the minimum slice of persistence this capability depends on — a
`staff` table, SQLAlchemy engine/session wiring (neither exists yet in `B2B_BE/`), and three pre-seeded
Staff rows (Ramesh — Owner/Admin, never bookable/listed; Meena — Staff; Arjun — Staff) — narrowly scoped
to what phone-number-based staff lookup needs, not the full shared-data-store buildout that
APPOINTMEN-13 (Story 1.1) still owns. The deliverable is a lookup-by-phone-number capability
(repository + LLM-callable tool) plus a Manager Agent stub function that turns a resolved phone number
into an unambiguous "who is speaking" result — the hook point a future conversational Manager Agent loop
will call.

---

## Business Context

From the ticket (verbatim): *"As Meena or Arjun (Staff) using Web Chat, I want the Manager Agent to ask
for my phone number and match it against pre-seeded staff records, so the agent knows specifically which
of us is speaking."*

**AC (FR-24, Web Chat clause, epics.md Story 1.5):** *"The Manager Agent's response to an
availability-change request always reflects which specific Staff member is understood to be speaking
(never ambiguous between Meena and Arjun)."*

This is the identity-resolution precondition every other Staff-mode Manager Agent story (Epic 3:
availability block/unblock, conflict checks, confirmation, permission denials) depends on — without a
reliable, unambiguous phone-number → Staff match, no downstream Staff action can be attributed correctly.

---

## Technical Context

Stack: FastAPI + SQLAlchemy + Alembic + PostgreSQL, per `stack/rules/base-rules.md`. Enforced backend
layout requires `app/models/` (SQLAlchemy models), `app/repositories/` (DB access), `app/tools/`
(in-process, Pydantic-schema-backed tool registrations the LLM calls), and `app/agent/manager_agent.py`
(the Manager Agent module) — all currently present only as empty scaffolding placeholders in the repo
(verified: `app/models/__init__.py`, `app/repositories/__init__.py`, `app/tools/__init__.py` are empty
files; `app/agent/manager_agent.py` does not exist yet; no SQLAlchemy engine/session module exists
anywhere in `B2B_BE/`).

**Dependency-ordering decision (explicit, per user instruction):** APPOINTMEN-13 (Story 1.1 — Salon,
Staff, Service, Customer, Booking, Availability entities) is nominally this ticket's dependency and is
still "To Do." Per the user's explicit direction, this plan starts APPOINTMEN-17 first and builds only
the minimum real slice Story 1.1 would otherwise provide for FR-24 to work: a `staff` table (id, name,
phone_number, role, created_at) and its three seeded rows. It deliberately does **not** build Salon,
Service, Customer, Booking, or Availability tables, a `salon_id` foreign key on `staff`, or any
non-FR-24 Story 1.1 acceptance criterion. When APPOINTMEN-13 is implemented, it is expected to *extend*
the `staff` table (e.g. add `salon_id`) via an additive migration, not replace this work.

Layering follows the enforced architecture exactly: `app/tools/staff.py` (LLM-callable, Pydantic-schema
tool) → `app/repositories/staff_repository.py` (DB access) → `app/models/staff.py` (SQLAlchemy model) →
Postgres, with `app/agent/manager_agent.py` as the (stubbed) caller representing the Manager Agent's
identity-resolution step. No `app/domain/` module is introduced for this ticket — a single indexed
phone-number lookup has no business logic beyond the query itself, so an intermediate domain layer would
be pure indirection; this is called out explicitly rather than silently deviating from the "tool → domain
→ repository" phrasing in `base-rules.md` (which describes the layers available, not a mandate that every
tool use every layer).

Because no chat endpoint, LLM provider integration, or conversation-state persistence exists anywhere in
the repo yet (`app/api/chat.py`, `app/agent/state/`, and LLM wiring are all still empty scaffolding), the
"Manager Agent" deliverable here is a stubbed Python function — the hook point named in the ticket's own
scoping guidance — not a working conversational loop. Wiring it into an actual chat turn is out of scope
(see Out of Scope).

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/models/base.py` | New | Declarative `Base` for SQLAlchemy models — does not exist yet anywhere in the repo. |
| `B2B_BE/app/database.py` | New | Engine + session-factory + `get_db` dependency, built from `settings.database_url` (already present in `app/config.py`) — no DB engine/session module exists yet. |
| `B2B_BE/app/models/staff.py` | New | `Staff` ORM model + `StaffRole` enum (`owner_admin`, `staff`), scoped to FR-24's needs only. |
| `B2B_BE/app/models/__init__.py` | Modify | Currently empty; import `Base` and `Staff` so Alembic's autogenerate/metadata sees the model. |
| `B2B_BE/alembic/env.py` | Modify | `target_metadata` is currently hard-set to `None` with a comment deferring it to "Story 1.1"; point it at `Base.metadata` now that a real model exists. |
| `B2B_BE/alembic/versions/<new>_create_staff_table.py` | New | Schema migration: creates the `staff` table and `staff_role` Postgres enum type. |
| `B2B_BE/alembic/versions/<new>_seed_staff_records.py` | New | Data migration: inserts the three pre-seeded rows (Ramesh/Owner-Admin, Meena/Staff, Arjun/Staff). |
| `B2B_BE/app/repositories/staff_repository.py` | New | `get_staff_by_phone_number(db, phone_number)` — the DB access layer. |
| `B2B_BE/app/tools/staff.py` | New | Pydantic-schema-backed, LLM-callable tool wrapping the repository lookup (the file `app/tools/staff.py` is explicitly named in the enforced tree and did not exist yet). |
| `B2B_BE/app/agent/manager_agent.py` | New | Manager Agent stub: resolves a phone number to an unambiguous "who is speaking" result (satisfies the AC's wording directly); the hook point a future conversational loop calls. |

No file outside `B2B_BE/` is touched. No `B2B_FE/` file is read or written.

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: SQLAlchemy engine/session foundation

**Description:** Add the declarative `Base` and the engine/session wiring that every subsequent task
depends on. Neither exists anywhere in `B2B_BE/` today (only `app/config.py`'s `settings.database_url`
exists from APPOINTMEN-12). `app/database.py` creates the SQLAlchemy engine from
`settings.database_url`, a `SessionLocal` session factory, and a `get_db()` FastAPI dependency generator
for future request-scoped use.

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/app/models/base.py` — `Base = declarative_base()` (or SQLAlchemy 2.0 `DeclarativeBase` subclass).
- `B2B_BE/app/database.py` — engine, `SessionLocal`, `get_db()`.

**Dependencies:** None.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 2: `Staff` ORM model

**Description:** Add the `Staff` model scoped to exactly what FR-24 needs: `id`, `name`, `phone_number`
(unique, indexed — the lookup key), `role` (`StaffRole` enum: `owner_admin` | `staff`), `created_at`. No
`salon_id` (Salon table doesn't exist yet — deferred to APPOINTMEN-13, see Technical Context). Wire it
into `app/models/__init__.py` so it registers on `Base.metadata`.

**Files to modify:**
- `B2B_BE/app/models/__init__.py`

**New files to create:**
- `B2B_BE/app/models/staff.py` — `StaffRole` enum + `Staff` model.

**Dependencies:** Task 1.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 3: Alembic wiring + `staff` table schema migration

**Description:** `alembic/env.py` currently hard-sets `target_metadata = None` with a comment deferring
this to "Story 1.1" — point it at `app.models.base.Base.metadata` now that a real model exists. Generate
a new migration (chained after `d141a62b1e58`, the existing initial empty migration) that creates the
Postgres `staff_role` enum type and the `staff` table with a unique index on `phone_number`.

**Files to modify:**
- `B2B_BE/alembic/env.py`

**New files to create:**
- `B2B_BE/alembic/versions/<generated-revision-id>_create_staff_table.py` — the exact filename/revision
  hash is assigned by running `alembic revision -m "create staff table"` at implementation time; this
  plan fixes its intent and its `down_revision` (`d141a62b1e58`), not its generated hash.

**Dependencies:** Task 2.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 4: Seed the three pre-seeded Staff records

**Description:** A second, separate data-only migration (chained after Task 3's schema migration)
inserts exactly three rows: Ramesh (`role=owner_admin`), Meena (`role=staff`), Arjun (`role=staff`), each
with a fixed placeholder phone number (demo data, not real numbers — e.g. `+15550000001` /
`+15550000002` / `+15550000003`, one per person). Kept as its own migration (not folded into Task 3's
schema migration) so the schema-vs-data change is independently reviewable and independently
revertible. Ramesh's row exists so downstream Owner/Admin identity-resolution work (APPOINTMEN-16, not
this ticket) has data to match against, but this ticket does not build any Ramesh-specific behavior.

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/alembic/versions/<generated-revision-id>_seed_staff_records.py`

**Dependencies:** Task 3.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 5: Staff repository — lookup by phone number

**Description:** The DB access layer: `get_staff_by_phone_number(db: Session, phone_number: str) ->
Staff | None`, doing an exact-match query against the unique, indexed `phone_number` column. No phone
number normalization/formatting is added (PRD does not ask for multi-format matching — see Out of
Scope).

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/app/repositories/staff_repository.py`

**Dependencies:** Task 2 (model), Task 1 (session).

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 6: Staff identity tool (LLM-callable)

**Description:** `app/tools/staff.py` — the file explicitly named in the enforced backend tree
(`stack/rules/base-rules.md`) that did not exist yet. Defines a Pydantic input schema
(`ResolveStaffIdentityInput { phone_number: str }`) and a Pydantic result schema (`StaffIdentity { id,
name, role }`), and a function `resolve_staff_identity(phone_number: str) -> StaffIdentity | None` that
opens a session via `SessionLocal`, calls the Task 5 repository function, and maps the ORM row to the
Pydantic result (or `None` on no match — per `addendum.md`'s identity model, "no match → out of scope for
the demo," so no fallback/creation flow is built here). This is the tool a future Manager Agent
tool-registry would register for the LLM's function-calling loop, per the "in-process tool registration"
pattern in `base-rules.md`.

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/app/tools/staff.py`

**Dependencies:** Task 5.

**Complexity:** `Low`

**Testing requirements:**
- None — unit/integration test-writing is intentionally out of scope for this cycle (see Out of Scope).

---

### Task 7: Manager Agent identity-resolution stub

**Description:** `app/agent/manager_agent.py` does not exist yet (only `app/agent/__init__.py`,
`app/agent/prompts/__init__.py`, `app/agent/state/__init__.py` exist, all empty). Add the minimal module
named in the enforced tree, exposing a `resolve_speaker(phone_number: str) -> SpeakerContext | None`
function that calls the Task 6 tool and a `describe_speaker(context: SpeakerContext) -> str` helper that
renders an unambiguous statement of who is speaking (e.g. `"Recognized as Meena (Staff)."` /
`"Recognized as Arjun (Staff)."`) — directly satisfying the AC's wording that the Manager Agent's
response "always reflects which specific Staff member is understood to be speaking." This module is
explicitly a stub: it is not wired into any chat endpoint, LLM provider call, or conversation-state
persistence (none of which exist in the repo yet) — it is the callable hook point a future conversational
Manager Agent loop (a separate, not-yet-created story) will invoke once the phone number is collected
from the user.

**Files to modify:** *(none)*

**New files to create:**
- `B2B_BE/app/agent/manager_agent.py`

**Dependencies:** Task 6.

**Complexity:** `Low`

---

## External Dependencies

- **PostgreSQL**, reachable via `DATABASE_URL` — already provisioned by APPOINTMEN-12 (`docker-compose.yml`
  at repo root, `B2B_BE/.env.example`). Available now; no new infrastructure needed.
- **No new third-party packages.** `sqlalchemy`, `alembic`, `psycopg[binary]`, `pydantic` are already in
  `B2B_BE/pyproject.toml`. Nothing in this plan requires a dependency addition.
- **APPOINTMEN-13 (Story 1.1)** — nominal dependency, still "To Do." This plan does not wait for it; see
  the explicit dependency-ordering decision in Technical Context and the Out of Scope section below for
  exactly what is deferred to it.

---

## Testing Strategy

**Unit and integration test-writing is intentionally out of scope for this cycle, by explicit user
instruction** (batch/time-constrained delivery; bypass to be recorded in Jira separately from this
plan). No test tasks are planned above, and none should be added during implementation. This is a
deliberate scope decision, not an oversight — see Out of Scope.

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | Not planned this cycle | `pytest` (available, not invoked for new coverage here) |
| Integration | Not planned this cycle | `pytest` against real Postgres (available, not invoked for new coverage here) |

Minimum coverage expectation: none beyond what already exists (`tests/test_health.py`,
`tests/integration/test_health_container.py`), which this ticket does not touch or regress.

---

## Security Considerations

- Phone-number-based lookup is the entire identity mechanism here, per PRD §6.3/§7 and
  `stack/rules/base-rules.md` Security Baselines — no password, OTP, or session token is introduced, and
  none should be. This is not a hardened security boundary (a determined actor with direct API/DB access
  bypasses it entirely) — consistent with the stack's documented, accepted risk, not a gap introduced by
  this ticket.
- Seeded phone numbers are placeholder demo values, not real numbers; no real PII is introduced.
- `phone_number` argument validation on the tool's Pydantic input model is standard shape validation only
  (non-empty string) — no deep format enforcement, consistent with the "happy-flow-only" testing/PRD
  scope.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| APPOINTMEN-13 later adds `salon_id` (or other columns) to `staff`, colliding with this ticket's schema | Med | Low | This plan's migration is additive-only (no columns beyond what FR-24 needs); APPOINTMEN-13 is expected to extend via a further additive migration, not rewrite this one. Flagged explicitly here so the Architect/Reviewer of APPOINTMEN-13 sees it. |
| No chat endpoint or LLM loop exists yet, so the AC ("Manager Agent's response...") can only be demonstrated at the function level, not end-to-end in a live chat | High | Med | Explicitly scoped as a stub/hook point per the ticket's own instructions; flagged in Overview, Technical Context, and Out of Scope rather than silently claimed as end-to-end done. |
| Seed migration hard-codes placeholder phone numbers that may not match whatever numbers are used in a live demo/testing session | Med | Low | Values are easy to change in one migration file; documented here as placeholder, not asserted as final production data. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — SQLAlchemy engine/session foundation | `Low` |
| Task 2 — `Staff` ORM model | `Low` |
| Task 3 — Alembic wiring + schema migration | `Low` |
| Task 4 — Seed pre-seeded Staff records | `Low` |
| Task 5 — Staff repository (lookup by phone number) | `Low` |
| Task 6 — Staff identity tool (LLM-callable) | `Low` |
| Task 7 — Manager Agent identity-resolution stub | `Low` |
| **Overall** | `Low` |

---

## Out of Scope

- **Unit tests and integration tests** — explicitly not written this cycle, per direct user instruction
  (to be recorded as a bypass note in Jira, separately from this plan; this plan does not edit any
  workflow/orchestration file to reflect that bypass).
- **The full shared-data-store buildout (APPOINTMEN-13 / Story 1.1)** beyond the `staff` table needed for
  FR-24: no `salons`, `services`, `customers`, `bookings`, or `availability` tables; no `salon_id` foreign
  key on `staff`; no cross-entity relationships. This ticket seeds exactly the three Staff rows FR-24
  needs and nothing else from Story 1.1's acceptance criteria.
- **A working chat endpoint or WebSocket surface** (`app/api/chat.py`) — does not exist yet anywhere in
  the repo and is not created by this ticket. The Manager Agent stub (Task 7) is a callable function, not
  a reachable HTTP/WS endpoint.
- **LLM provider integration** (registering `app/tools/staff.py` with an actual LLM tool-calling loop,
  system prompts, role-scoped tool registries per `app/agent/prompts/`) — no LLM provider is wired into
  the repo anywhere yet; out of scope for this narrowly-scoped identity-resolution ticket.
- **Conversation-state persistence** (`messages` table / `app/agent/state/`) — not touched; no
  conversation history is stored by this ticket.
- **The "ask for a phone number" conversational turn itself** (i.e., the actual chat prompt flow that
  collects a phone number from Meena/Arjun) — this ticket delivers the *matching* capability once a phone
  number is supplied, not the conversational turn that solicits it (which depends on the chat
  endpoint/LLM loop called out as out of scope above).
- **WhatsApp-channel identity resolution** (Story 7.2 / FR-14/FR-24 WhatsApp clause) — Web Chat only, per
  this ticket's stated scope.
- **Owner/Admin (Ramesh) identity-resolution behavior** (APPOINTMEN-16 / Story 1.4) — Ramesh's row is
  seeded here only because Task 4 seeds all three Story-1.1-required rows in one pass (cheaper than a
  separate migration later); no Ramesh-specific resolution logic, permission handling, or dashboard
  exclusion behavior is built in this ticket.
- **Phone number normalization/formatting** (e.g. accepting multiple formats for the same number) — exact
  string match only, consistent with the PRD's happy-flow-only scope.
- **No-match / unrecognized-number handling beyond returning `None`** — per `addendum.md`'s identity
  model, "no match → out of scope for the demo"; no fallback flow, error message design, or retry prompt
  is built here.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-17` · Branch: `feature/APPOINTMEN-17-staff-identity-resolution`*
