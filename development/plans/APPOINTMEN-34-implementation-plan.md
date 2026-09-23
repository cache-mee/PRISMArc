# Implementation Plan: 3.5 FR-28 — Staff cannot manage the catalog

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-34` |
| Summary | 3.5 FR-28: Staff cannot manage the catalog |
| Type | `Story` |
| Labels | `backend` |
| Priority | Medium |
| Branch | `feature/APPOINTMEN-34-35-fr-28-staff-cannot-manage-the-catalog` |
| Assigned to | `sparc.team_18@experionglobal.com` |

---

## Overview

Add the FR-28 role-boundary behaviour to the Manager Agent: when a Staff-identified speaker
(Meena or Arjun) asks to add, edit, or delete a Service or its price — an Owner/Admin-only
action — the agent must answer with a fixed, plain one-line redirect instead of attempting the
action or returning an error. This is implemented as two small, testable hook-point functions
(a catalog-change intent classifier and a role-boundary redirect function) added alongside the
existing Manager Agent hook points from APPOINTMEN-16/17/25, following the same incremental
pattern — there is no wired Manager Agent conversation loop or API endpoint yet for either
Staff or Owner, so this ticket adds the pieces a future turn loop will call, exactly as
`build_proposed_availability_change` (FR-25) and `confirm_exact_match` (Booking Agent FR-6) were
added ahead of their own wiring.

---

## Business Context

From the ticket description:

> As Meena or Arjun, when I ask about adding/editing/deleting a service or price, I want to be
> told that's not something I manage, so the boundary between my role and the Owner/Admin's is
> clear.

Acceptance criteria (PRD FR-28 Consequences, `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md`):

> A catalog-change request from a Staff-identified session is not a permitted action (per
> `staff-owner-manager-chat.md` §5, surfaced as a plain one-line redirect, not an error state).

The UX spec (`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/staff-owner-manager-chat.md`
§5) fixes the exact copy and framing:

> **A Staff member asks about the catalog, the dashboard, or the other staff member's schedule
> (FR-28, FR-29, FR-30):** **Agent**: "That's something Ramesh manages — I can help you with your
> own availability." Same short-redirect pattern.
>
> **Decision — role-boundary responses are plain, one-line redirects, not error states.** ... a
> disallowed request is not a malformed input, it's simply outside what this identified role can
> do ... the redirect copy is informational, matching that framing.

This ticket implements the FR-28 slice of that shared decision only (the catalog/price
sub-case); FR-29 (dashboard/staff-list) and FR-30 (other staff's schedule) are separate stories
(3.6/3.7) sharing the same copy pattern but a different trigger condition, not built here.

---

## Technical Context

Per `stack/rules/base-rules.md` §"Required patterns", the long-term enforcement mechanism for
FR-28 is a **role-scoped tool registry**: a Staff session simply never has a catalog-write tool
registered, so the LLM cannot call it. That registry, and the Manager Agent's actual
conversational tool-calling loop, do not exist yet in this codebase — `app/agent/manager_agent.py`
currently contains only hook-point functions (`resolve_speaker`, `describe_speaker`,
`build_proposed_availability_change`) that a future wired turn loop will call, mirroring how
`app/agent/booking_agent.py` built up its identity gate and confirmation hooks incrementally
across several tickets before being fully wired. There is also no Owner-side catalog
add/edit/delete tool built yet (`app/tools/services.py` only has the read-only
`get_service_catalog`, FR-4) — FR-28's redirect is independent of whether that Owner-side
mechanism exists, since the UX spec frames it as a conversational boundary, not a tool-call
failure.

Given that, this ticket adds the same kind of hook point already established for FR-25:

- A **catalog-change intent classifier**, `is_catalog_change_request(text) -> bool`, in a new
  `app/agent/catalog_intent.py` module — same shape and precedent as `app/agent/availability_intent.py`
  (`parse_availability_change`) and `app/agent/booking_intent.py`: a synchronous Anthropic
  tool-calling call classifying a free-text message, sharing `app.config.settings` for the API
  key/model, consistent with the "no forking of intent-parsing logic" and "same agent, every
  channel" rules (`base-rules.md`) — this classifier has no channel-specific branch and will be
  reusable unchanged by the WhatsApp delta (Story 7.4).
- A **role-boundary redirect hook**, `handle_staff_catalog_boundary(speaker, message) -> str | None`,
  added to the existing `app/agent/manager_agent.py`, mirroring `build_proposed_availability_change`'s
  doc-commented "hook point a future conversational Manager Agent loop calls" pattern. It returns
  the fixed UX-spec redirect string for a `StaffRole.STAFF` speaker whose message is a
  catalog-change request, and `None` otherwise (Owner/Admin speaker, or a Staff message that is not
  a catalog-change request) — `None` signals the caller to continue with other intent handling
  (e.g. FR-25's availability parsing), not that nothing should happen.

No database, model, repository, or API layer changes are needed — FR-28 is a pure
conversational-response rule over already-resolved identity (`StaffRole`, APPOINTMEN-16/17) and a
newly classified message intent.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/agent/catalog_intent.py` | New | LLM-based classifier: is a free-text message a catalog add/edit/delete (service or price) request — FR-28's trigger condition |
| `B2B_BE/app/agent/manager_agent.py` | Modify | Add the fixed FR-28 redirect string and the `handle_staff_catalog_boundary` hook function that returns it for a Staff-identified catalog-change request |

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: Catalog-change intent classifier

**Description:** Add `app/agent/catalog_intent.py` with `is_catalog_change_request(text: str) -> bool`,
using an Anthropic tool-calling call (mirroring `availability_intent.parse_availability_change`'s
structure: a Pydantic input model, a `_build_tool_schema()` helper, `tool_choice` forcing the
one tool) to classify whether `text` is a request to add, edit, or delete a Service or its price.
The tool's single boolean field's description should explicitly name "add", "edit"/"change", and
"delete"/"remove" a service or price as the positive cases, and note that questions about existing
prices/services (browsing, not changing) and availability/schedule requests are negative cases —
so it does not fire on FR-25 (availability block/unblock) messages routed to the same speaker.

**Files to modify:** *(none — new file only)*

**New files to create:**
- `B2B_BE/app/agent/catalog_intent.py` — the classifier described above.

**Dependencies:** None.

**Complexity:** `Low`

**Testing requirements:**
- Unit test (mocking the Anthropic client response, same approach as would be used for
  `availability_intent.parse_availability_change`): returns `True` for the ticket's own example
  phrasings ("add beard trim for 150 rupees", "change haircut to 350", "remove beard trim") and
  `False` for an unrelated message (e.g. an availability block request, "block out Friday
  morning").
- Per `base-rules.md`'s happy-flow-only testing scope, only the stated positive/negative examples
  need covering — no exhaustive ambiguous-phrasing edge cases are required for this build.

**Documentation updates:** *(none — module docstring is the only documentation surface, per existing precedent in `availability_intent.py`)*

---

### Task 2: FR-28 role-boundary redirect hook on the Manager Agent

**Description:** In `app/agent/manager_agent.py`, add the fixed redirect string from the UX spec
and a `handle_staff_catalog_boundary(speaker: SpeakerContext, message: str) -> str | None`
function: returns the fixed string when `speaker.role is StaffRole.STAFF` and
`is_catalog_change_request(message)` is `True`; returns `None` for an Owner/Admin speaker
(FR-28 only restricts Staff — Ramesh is allowed to manage the catalog, Epic 4, not built here)
or when the message is not a catalog-change request. The returned string is always the fixed
UX-spec copy — never templated from `message` or from `speaker.name` — matching the "plain
one-line redirect, not an error state" decision and keeping the copy identical regardless of how
the disallowed request was phrased (same reasoning already documented on
`build_proposed_availability_change` for why identity/content is never taken from free text).

**Files to modify:**
- `B2B_BE/app/agent/manager_agent.py` — add the redirect constant, the
  `handle_staff_catalog_boundary` function, and the new import of
  `is_catalog_change_request` from `app.agent.catalog_intent`.

**New files to create:** *(none)*

**Dependencies:** Task 1.

**Complexity:** `Low`

**Testing requirements:**
- Unit test: a `SpeakerContext` with `role=StaffRole.STAFF` and a catalog-change message returns
  exactly `"That's something Ramesh manages — I can help you with your own availability."`
- Unit test: a `SpeakerContext` with `role=StaffRole.OWNER_ADMIN` returns `None` regardless of
  message content (Owner/Admin is never redirected by this rule).
- Unit test: a `SpeakerContext` with `role=StaffRole.STAFF` and a non-catalog message (e.g. an
  availability request) returns `None`.

**Documentation updates:** *(none — function docstring only, per existing module convention)*

---

## External Dependencies

- Anthropic API key/model (`app.config.settings.anthropic_api_key`, `anthropic_model`) — already
  configured and already used by `booking_intent.py` and `availability_intent.py`; no new
  environment variable, dependency, or third-party service is introduced.
- No dependency on Epic 4 (Owner-side catalog add/edit/delete) or on the Manager Agent's
  conversational turn loop / API endpoint — both are unbuilt, and FR-28 is independently
  demonstrable at the unit level (classifier + hook function) ahead of either landing, exactly as
  FR-25/26/27's hook points were.

---

## Testing Strategy

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | `is_catalog_change_request` classifier phrasing cases (Task 1); `handle_staff_catalog_boundary` role/message-branch cases (Task 2) | `pytest`, mocking the `anthropic` client response object (no live API call in tests) |
| Integration | Not applicable — no DB write, no API endpoint exists yet for the Manager Agent (no `/manager-chat` route) to exercise end-to-end | — |
| End-to-End | Not applicable — same reason as above; deferred to whichever ticket wires the Manager Agent's conversational loop/endpoint | — |

Minimum coverage expectation: per `stack/rules/base-rules.md` Testing Requirements, this build is
explicitly happy-flow-only and FR-28 is not one of the two explicitly prioritized behaviours
(confirm-before-write, conflict detection) — so only the stated positive/negative example
coverage above ("Everything else, time permitting" tier) is expected, not exhaustive edge-case
coverage. Actual test-writing is a later workflow step; this plan states the requirement and
approach only.

---

## Security Considerations

Per `base-rules.md` Security Baselines, role-scoped enforcement in this system is "a code-level
convention, not a hard security boundary." `handle_staff_catalog_boundary` is a conversational
courtesy check only: since no catalog-write tool or endpoint is registered/exposed yet, there is
currently nothing for a Staff session to bypass by calling the API directly, but this remains true
even once Epic 4 lands — this ticket does not add or claim any enforcement beyond "keeps the
LLM-driven conversation flow honest," per the existing documented limitation.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The classifier misreads an ambiguous message (e.g. "how much is a haircut?" vs. "change the haircut price") | Low | Low | Not in scope to handle exhaustively per `base-rules.md`'s happy-flow-only testing scope; the tool-schema description explicitly distinguishes "browsing/asking price" from "changing price" to cover the ticket's own stated examples correctly |
| FR-28 has no live end-to-end demo path until a Manager Agent turn loop/endpoint is wired (none exists yet, for either Staff or Owner) | Medium | Medium — acceptance criteria are verifiable at the unit level now, but not demonstrable in a running chat | Flag for whoever picks up the (not-yet-scoped) Manager Agent turn-loop/endpoint ticket that `handle_staff_catalog_boundary` and its FR-25 sibling (`build_proposed_availability_change`) are both waiting to be called from it |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — Catalog-change intent classifier | `Low` |
| Task 2 — FR-28 role-boundary redirect hook | `Low` |
| **Overall** | `Low` (matches the epics.md Story 3.5 "Complexity: S" rating) |

---

## Out of Scope

- Any `B2B_FE/` change (Manager Agent chat UI, `/team` route, redirect-message rendering/styling)
  — this ticket is backend-only per its `backend` label; the repository layout constraint
  (`CLAUDE.md`) confines all changes to `B2B_BE/`.
- FR-29 (Staff cannot view the staff list or dashboard, Story 3.6) and FR-30 (Staff cannot
  override another staff member's schedule, Story 3.7) — separate stories sharing the same
  redirect *pattern* but a different trigger condition; not implemented here even though the
  feature branch name (`...APPOINTMEN-34-35-fr-28...`) groups this ticket with a neighbouring one.
- FR-15–FR-18 (Owner/Admin catalog add/edit/delete, Epic 4, Stories 4.1–4.3) — not implemented;
  this ticket's redirect fires purely on Staff role + classified intent, independent of whether the
  underlying Owner-side catalog-write mechanism exists.
- The role-scoped tool registry mechanism itself (`base-rules.md`'s stated long-term enforcement
  point) and the Manager Agent's wired conversational turn loop / API endpoint — both are larger,
  not-yet-built architecture pieces that this ticket's hook points are written to be called from
  later, not built here.
- Modifying `app/domain/identity.py`, `app/tools/staff.py`, `app/repositories/staff_repository.py`,
  or the existing `resolve_speaker`/`describe_speaker` functions in `manager_agent.py` — Staff/Owner
  identity resolution is already complete (APPOINTMEN-16/17) and is reused unchanged.
- The WhatsApp channel delta for this redirect (Story 7.4, `whatsapp-deltas.md` §2) — explicitly a
  separate story ("identical copy and behavior... no channel-specific variation" once the shared
  hook point is wired into that channel too).

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-34` · Branch: `feature/APPOINTMEN-34-35-fr-28-staff-cannot-manage-the-catalog`*
