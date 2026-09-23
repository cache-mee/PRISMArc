# Implementation Plan: 4.6 FR-22 — Owner/Admin cannot manage staff accounts

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-42` |
| Type | `Story` |
| Branch | `feature/APPOINTMEN-42-owner-admin-cannot-manage-staff-accounts` |
| Assigned to | `sparc.team25@experionglobal.com` |

---

## Overview

This is a **negative/restriction requirement**: FR-22's acceptance criteria is that no
conversational (chat/LLM tool-calling) or Dashboard action exists anywhere in the backend that
creates, deletes, or edits a `Staff` record — the staff list must stay view-only for this demo. A
full audit of `B2B_BE/` (models, repositories, tools, agent modules, API routers, migrations) found
**zero** existing Staff mutation paths. The codebase is already compliant. This plan is therefore a
short verification-only plan: it records the audit evidence and adds one small regression test that
locks the guarantee in going forward, so a future ticket cannot silently introduce a Staff
create/update/delete path without an explicit, visible test failure.

---

## Business Context

> "As Ramesh, I want no path to add, remove, or edit a staff account, so the staff list stays
> view-only as scoped for this demo. AC (FR-22): no conversational or Dashboard action exists that
> creates, deletes, or edits a Staff record."

Per `stack/rules/base-rules.md`, `staff` is a small, fixed, pre-seeded table (3 demo rows: Ramesh as
`owner_admin`, Meena and Arjun as `staff`) with no product requirement anywhere in the PRD/FR set to
manage staff accounts through the app. The user-facing outcome is a guarantee, not a feature: Ramesh
(or anyone) has no way — via the Web Chat / Manager Agent conversational surface or via any Dashboard
API — to add, remove, or edit a staff account.

---

## Technical Context

Audited under `B2B_BE/` (this ticket is backend-only, label `backend`; no `B2B_FE/` files were read
or touched):

**LLM/chat tool-calling surface** (`app/tools/`, registered per `stack/rules/base-rules.md`'s
"in-process tool registration" pattern):
- `app/tools/staff.py` exposes exactly one LLM-callable tool, `resolve_staff_identity` — a read-only
  phone-number → `StaffIdentity` lookup. No create/update/delete tool for `Staff` exists.
- `app/agent/manager_agent.py` (the Owner/Admin-mode conversational agent module named in
  `base-rules.md`'s architecture tree) currently only contains `resolve_speaker` /
  `describe_speaker` — identity-resolution helpers built on `resolve_staff_identity`. It has no tool
  registry wired yet, and defines no staff-mutation logic.
- `app/agent/booking_agent.py` (Customer-facing) never touches `Staff` at all beyond read paths used
  for booking (out of scope for this ticket).

**Dashboard/API surface** (`app/api/`):
- Only `app/api/chat.py` (`POST /chat`) and `app/api/services.py` (`GET /services`, not even wired
  into `app/main.py` yet) exist today. `app/main.py` registers only `chat_router`.
- `app/api/dashboard.py` — named in `base-rules.md`'s architecture tree as the future home of
  "read-only dashboard data endpoints" — does not exist yet in this repository. There is therefore no
  Dashboard endpoint of any kind yet, mutating or otherwise.
- No `app/api/staff.py` exists, and no route in the app (present or planned) accepts POST/PUT/PATCH/
  DELETE for a staff resource.

**Data-access layer:**
- `app/repositories/staff_repository.py` defines only `get_staff_by_phone_number` and
  `get_staff_by_name` — both read-only `SELECT` queries. No insert/update/delete function exists for
  `Staff`.
- `app/models/staff.py` is a plain SQLAlchemy model with no additional read/write helper methods.

**Migrations (deploy-time, not an app/user-facing path):**
- `alembic/versions/72040317c08b_create_staff_table.py` creates the table.
- `alembic/versions/8aac3e937d39_seed_staff_records.py` bulk-inserts the 3 demo rows (`upgrade`) and
  removes them by phone number (`downgrade`). This is a one-time, operator-run schema migration
  (`alembic upgrade`/`downgrade`), never reachable via chat or Dashboard, and is explicitly not the
  kind of path FR-22 is scoped to prevent. Noted here for completeness, not flagged as a violation —
  see Out of Scope.

**Conclusion:** every Staff-adjacent code path in `B2B_BE/` is read-only. FR-22 is satisfied by the
current codebase with no removal or blocking work required. The remaining work is to record this
finding as an enforceable regression test, since `base-rules.md`'s own architecture tree earmarks
future `app/api/dashboard.py` and a Manager Agent tool registry as planned work in later tickets —
this guard ensures FR-22 is not accidentally violated when that later work lands.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/tests/test_staff_no_mutation_path.py` | New | Regression test asserting no Staff create/update/delete path exists in the tool registry, the repository layer, or the FastAPI route table — locks in FR-22 for future changes. |

No existing file requires modification — no Staff mutation path exists to remove or block.

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: Record the audit finding (no code change)

**Description:** This implementation plan itself is the audit record: every Staff-related file
under `B2B_BE/` (`app/models/staff.py`, `app/repositories/staff_repository.py`, `app/tools/staff.py`,
`app/agent/manager_agent.py`, `app/api/`, `alembic/versions/*staff*`) was read and confirmed
read-only with respect to `Staff` records. No file requires edit or deletion to satisfy FR-22. This
task's "testable outcome" is the audit trail above (Technical Context) plus Task 2's automated
assertion of the same conclusion.

**Files to modify:** None.

**New files to create:** None.

**Dependencies:** None.

**Complexity:** `Low`

**Testing requirements:**
- N/A — no code changed. Verified by manual `grep`/read audit (commands recorded in Testing
  Strategy below) and by Task 2's automated test.

**Documentation updates:** None (this plan is the record).

---

### Task 2: Add a regression test locking in "no Staff mutation path"

**Description:** Add one small backend test module that mechanically asserts the guarantee FR-22
requires, so any future change that introduces a Staff create/update/delete path (a new tool, a new
`app/api/staff.py` or `app/api/dashboard.py` route, or a new repository write function) fails this
test and requires deliberate review rather than landing silently. The test covers three angles:
1. `app.main.app.routes` contains no route whose path mentions `staff` with a method other than
   `GET`/`HEAD`/`OPTIONS`.
2. `app.tools.staff` exposes no public callable other than `resolve_staff_identity` (and its
   supporting Pydantic models) — i.e. no function name matching a create/update/delete verb.
3. `app.repositories.staff_repository` exposes no public callable other than the two known read
   functions (`get_staff_by_phone_number`, `get_staff_by_name`).

**Files to modify:** None.

**New files to create:**
- `B2B_BE/tests/test_staff_no_mutation_path.py` — the regression test described above.

**Dependencies:** Task 1 (audit findings the test encodes).

**Complexity:** `Low`

**Testing requirements:**
- Test passes against the current codebase (proves the audit finding, not just asserts it).
- Test is written to fail loudly (clear assertion message naming the offending route/function) if a
  future change adds a Staff mutation path, per `stack/rules/base-rules.md`'s Pydantic-schema and
  type-hint conventions for any new backend test code.

**Documentation updates:** None.

---

## External Dependencies

None. No third-party API, feature flag, environment variable, or other team's in-flight work is
required for this ticket.

---

## Testing Strategy

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | `app.tools.staff` and `app.repositories.staff_repository` module surface — asserts only read-only callables are exported | `pytest` (per `stack/rules/base-rules.md` §Testing Requirements) |
| Integration | `app.main.app` FastAPI route table — asserts no non-GET route mentions `staff` | `pytest` + `fastapi.testclient.TestClient` (existing pattern in `B2B_BE/tests/conftest.py`, `test_health.py`) |
| End-to-End | Not applicable — no user-facing flow to add; this is an absence-of-capability guarantee, not a new happy path. | N/A |

Minimum coverage expectation: per `stack/rules/base-rules.md`, this build is explicitly happy-flow-
only and does not mandate exhaustive edge-case coverage; FR-22 is a "confirm absence" requirement,
so the single regression test above is sufficient — it is not in the base-rules.md priority list
(confirm-before-write, conflict detection) and no further test investment is warranted.

Commands to run before/after (from `B2B_BE/`, since no test/build/lint command is yet recorded in
`CLAUDE.md`, discovered here from `pyproject.toml`):
- `pytest` (test config: `[tool.pytest.ini_options] testpaths = ["tests"]` in `B2B_BE/pyproject.toml`)
- No lint/format command is configured yet in this repo (no `ruff`/`black` config block found in
  `pyproject.toml` beyond dependency mention in `base-rules.md`) — report as *not validated* rather
  than inventing one, per `CLAUDE.md`.

---

## Security Considerations

FR-22 is itself a security/access-control guarantee: per `stack/rules/base-rules.md`'s "Role-scoped
tool registry per agent/role, as the access-control mechanism," a tool a role should not invoke must
simply not be registered — there is currently no Staff-mutating tool to register into any role's
registry in the first place, which is the strongest form of compliance (nothing to gate). The same
document notes role-scoped registries are a code-level convention, not a hard security boundary
(a direct out-of-band API call could bypass it) — moot here since no such API route exists to call.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A future ticket (e.g. building out `app/api/dashboard.py` or wiring the Manager Agent's tool registry) reintroduces a Staff mutation path without revisiting FR-22 | `Med` | `Med` | Task 2's regression test fails immediately and by name if that happens, forcing explicit review rather than silent drift. |
| Reviewer disagrees that "verification-only" is sufficient and expects visible code removal | `Low` | `Low` | This plan's Technical Context documents the full audit trail (files read, conclusion per file) so the reviewer can independently verify the "already compliant" claim rather than take it on faith. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 | `Low` |
| Task 2 | `Low` |
| **Overall** | `Low` |

---

## Out of Scope

- **Any `B2B_FE/` work.** The ticket is labeled `backend` and its acceptance criteria concern only
  the backend's conversational tool-calling surface and Dashboard API surface. Any Owner/Admin
  Dashboard **webUI** (e.g. a bookings-view or staff-list-view frontend, mentioned elsewhere by the
  user) is explicitly out of scope for APPOINTMEN-42 and belongs to a separate, frontend-classified
  ticket under `B2B_FE/`. No file under `B2B_FE/` was read or written for this plan or will be for
  its implementation.
- **Building `app/api/dashboard.py` or any other new Dashboard endpoint**, read-only or otherwise —
  not requested by this ticket and not required to satisfy "no mutation path exists" (an endpoint
  that does not exist cannot mutate anything). Creating it is a separate ticket's concern.
- **Wiring a Manager Agent tool registry** — `app/agent/manager_agent.py` having no tool registry yet
  is itself compliant with FR-22 (nothing is registered, mutating or not); assembling that registry
  for other FRs (e.g. staff-permitted read tools) is future, separate work, not this ticket's.
- **The Alembic seed/create migrations for `staff`** (`72040317c08b_create_staff_table.py`,
  `8aac3e937d39_seed_staff_records.py`) are left untouched. They are one-time, operator-run schema
  operations, not an app-reachable conversational or Dashboard path, and are outside FR-22's stated
  scope ("no conversational or Dashboard action").
- **Any change to `app/repositories/bookings.py` / `app/repositories/availability.py`** "bookable
  staff" read queries referenced in git history (APPOINTMEN-20/24) — these are read-only staff
  lookups in service of booking search, unrelated to staff-record mutation, and were not modified.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-42` · Branch: `feature/APPOINTMEN-42-owner-admin-cannot-manage-staff-accounts`*
