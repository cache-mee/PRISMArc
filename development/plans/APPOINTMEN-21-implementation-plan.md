# Implementation Plan: 2.4 SM-4a — Booking-Intent Human-Verification Checkpoint

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-21` |
| Type | `Story` |
| Branch | `feature/APPOINTMEN-21-booking-intent-verification-checkpoint` |
| Assigned to | unassigned |

**Description (from Jira):** As a judge evaluating the build, I want a human-verification
checkpoint on the Booking Agent's parsed intent before it's acted on, so the
Human-Verification-40 weighting has an observable moment tied to intent parsing.

**AC (PRD §8 SM-4a):** a human reviews/corrects the parsed intent (service/date-time/staff)
before Stories 2.5/2.6/2.7 proceed; not customer-visible, zero UI change on the customer
conversation. Open question in the ticket text itself: whether this needs an operator-facing
UI hook or a log/terminal demonstration suffices is left as a Developer decision — resolved
below in Technical Context.

---

## Overview

Add a backend-only "SM-4a" checkpoint that sits between the Booking Agent's intent parsing
(`parse_booking_intent`, FR-5, `app/agent/booking_intent.py`) and any future availability-
resolution code (FR-6/7/8 — Stories 2.5/2.6/2.7, i.e. APPOINTMEN-22/23/24). The checkpoint
logs the parsed intent as an observable moment, and mechanically blocks any downstream code
from acting on it until a human has explicitly verified (optionally correcting) it — mirroring
the existing `confirmed: bool = False` + `*NotConfirmedError` gate idiom already used for FR-9
(`BookingNotConfirmedError`) and FR-27 (`AvailabilityChangeNotConfirmedError`).

---

## Business Context

The PRD's Human-Verification-40 scoring weighting requires an observable point where a human
is in the loop before the system acts autonomously on the Booking Agent's LLM-parsed intent.
Per the ticket, this must NOT be visible to the customer and must NOT change the customer
conversation UI at all — it is an internal, operator-facing checkpoint only. FR-6/7/8's
availability-resolution stories (APPOINTMEN-22/23/24) are the "acted on" step this checkpoint
must precede.

---

## Technical Context

Investigated the current codebase (`B2B_BE/app/agent/booking_agent.py`,
`app/agent/booking_intent.py`, `app/domain/appointments.py`, `app/domain/availability.py`,
`app/tools/`) before planning:

- `BookingIntent` (FR-5, `app/agent/booking_intent.py:11-33`) is a plain Pydantic model
  (`service_name`, `requested_time`, `staff_preference`) produced by `parse_booking_intent`
  (`app/agent/booking_intent.py:63-108`), which calls the Anthropic API directly. This module
  has no DB/agent-orchestration dependencies — a safe, side-effect-free leaf module.
- `confirm_exact_match` (FR-6, `app/agent/booking_agent.py:110-122`) is already documented as
  "the hook point a future conversational Booking Agent loop will call once intent parsing,
  staff-preference limiting, **the SM-4a checkpoint**, and an actual availability check have all
  resolved" — i.e. this ticket's checkpoint is the explicitly-named missing piece between
  `parse_booking_intent` and `confirm_exact_match`/future FR-7/8 code.
  `handle_message` (`app/agent/booking_agent.py:60-99`) does not yet call any of intent
  parsing, this checkpoint, or `confirm_exact_match` — there is no live end-to-end turn loop
  yet (only FR-1 identity resolution is wired). Per the module's own docstring
  (`booking_agent.py:33-35`), wiring the resolved-turn loop into intent parsing/confirmation is
  explicitly out-of-scope future work (Epic 2/3), not something this ticket introduces either.
- The established "confirm-before-write" idiom (FR-9 `app/domain/appointments.py:15-20,52-77`;
  FR-27 `app/domain/availability.py:12-32,51-54`) is: a Pydantic model carrying the
  proposed/parsed thing plus a `confirmed: bool = False` field, and a single domain-layer gate
  function that raises a dedicated `*NotConfirmedError` before any dependent action runs if the
  flag isn't `True`. FR-27's version is fully self-contained in one domain file (model + error +
  gate together) — that is the cleaner of the two precedents and the one this plan follows,
  naming the flag `verified` (not `confirmed`) to match the ticket's own "human-verification"
  language and avoid confusion with the customer-facing `confirmed` flags on FR-6/9/27.
- **Resolving the ticket's open question:** given the explicit ticket allowance ("log/terminal
  demonstration suffices"), the base-rules constraint against building anything beyond a 24-hour
  hackathon's needs, and that no operator-facing UI surface (dashboard or otherwise) currently
  reads from the backend for this purpose, this plan implements the checkpoint as (a) a
  structured log line emitted at the checkpoint — the observable moment — plus (b) the same
  mechanical `verified: bool` gate idiom used elsewhere, with a small tool function a future
  Manager Agent (operator-facing only, never the customer-facing Booking Agent) can call to
  supply the human's review/correction. No `B2B_FE` change, no new DB table, no session-state
  change — none of those are needed to satisfy the AC as written.
- Layers touched: `app/domain/` (new gate module) and `app/agent/` (new hook function on the
  existing `booking_agent.py`), plus `app/tools/` (new tool module) — no `app/models/`,
  `app/repositories/`, or `B2B_FE/` changes.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/app/domain/booking_intent_verification.py` | New | SM-4a gate: `VerifiedBookingIntent`, `BookingIntentNotVerifiedError`, `require_verified_intent` |
| `B2B_BE/app/agent/booking_agent.py` | Modify | Add `present_intent_for_verification` hook (logs + returns unverified `VerifiedBookingIntent`); update module docstring |
| `B2B_BE/app/tools/intent_verification.py` | New | Operator-facing tool letting a human review/correct/verify a pending `BookingIntent` |

---

## Tasks

### Task 1: SM-4a domain gate

**Description:** Add the domain-layer enforcement point: `VerifiedBookingIntent` (wraps a
`BookingIntent` plus `verified: bool = False`), `BookingIntentNotVerifiedError`, and
`require_verified_intent(verified_intent) -> BookingIntent`, which raises unless
`verified_intent.verified is True`. This is the single place SM-4a's guarantee is mechanically
enforced, mirroring `confirm_and_apply_availability_change`'s self-contained structure in
`app/domain/availability.py`.

**Files to modify:** none

**New files to create:**
- `B2B_BE/app/domain/booking_intent_verification.py` — model, error, gate function; imports
  `BookingIntent` directly from `app.agent.booking_intent` (a plain runtime import, not
  `TYPE_CHECKING`-only, since `VerifiedBookingIntent.intent` is a real Pydantic field requiring
  the actual class at runtime — unlike `appointments.py`'s `TYPE_CHECKING` import of
  `DirectConfirmationPrompt`, which is only ever used as a function-parameter type hint)

**Dependencies:** None

**Complexity:** `Low`

**Testing requirements:**
- (Deferred to `sdlc-unit-test-workflow` per standing scope for this ticket batch — not written
  in this phase.) When written: `require_verified_intent` raises `BookingIntentNotVerifiedError`
  for `verified=False` and returns the wrapped intent unchanged for `verified=True`.

---

### Task 2: Booking Agent checkpoint hook

**Description:** Add `present_intent_for_verification(intent: BookingIntent) ->
VerifiedBookingIntent` to `app/agent/booking_agent.py`, alongside the existing
`confirm_exact_match` hook. Logs the parsed intent's `service_name`/`requested_time`/
`staff_preference` at `INFO` level as the "observable moment tied to intent parsing" the ticket
asks for, then returns an unverified `VerifiedBookingIntent` — a human operator must
subsequently call the Task 3 tool (or, once a live loop exists, whatever wires it in) to
progress it to `verified=True` before `require_verified_intent` will release it. Update the
module's top-of-file docstring to describe this third piece alongside `handle_message` and
`confirm_exact_match`, and to name it (not `confirm_exact_match`) as the actual SM-4a checkpoint
referenced in `confirm_exact_match`'s own docstring.

**Files to modify:**
- `B2B_BE/app/agent/booking_agent.py` — add `import logging`, a module-level
  `logging.getLogger(__name__)`, the new `present_intent_for_verification` function, its import
  of `BookingIntent`/`VerifiedBookingIntent`, and the docstring update.

**New files to create:** none

**Dependencies:** Task 1 (imports `VerifiedBookingIntent`)

**Complexity:** `Low`

**Testing requirements:**
- (Deferred, per above.) When written: calling the hook logs the intent fields and returns
  `VerifiedBookingIntent(intent=intent, verified=False)`.

---

### Task 3: Operator-facing verification tool

**Description:** Add `verify_booking_intent(pending, args) -> VerifiedBookingIntent` to a new
`app/tools/intent_verification.py`, following the existing in-process tool pattern
(`app/tools/customers.py`, `app/tools/staff.py`): an `VerifyBookingIntentArgs` Pydantic model
for LLM/tool-call arguments (optional `service_name`/`requested_time`/`staff_preference`
overrides — `None` keeps the parsed value — plus a required `verified: bool`), and a function
applying any corrections via `BookingIntent.model_copy(update=...)` and returning the resulting
`VerifiedBookingIntent`. Unlike `customers.py`/`staff.py`, this tool needs no DB access (pure
data transformation), so it does not open a `SessionLocal` session. Not registered into any
tool registry yet — no registry-assembly code exists in this codebase for any agent/tool yet
(see Out of Scope).

**Files to modify:** none

**New files to create:**
- `B2B_BE/app/tools/intent_verification.py`

**Dependencies:** Task 1 (imports `VerifiedBookingIntent`)

**Complexity:** `Low`

**Testing requirements:**
- (Deferred, per above.) When written: a correction field left `None` keeps the parsed value;
  a supplied correction overrides it; `verified` passes through as given.

---

## External Dependencies

None. No new third-party packages, environment variables, or other teams' work required.

---

## Testing Strategy

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | `require_verified_intent` gate behavior; `verify_booking_intent` correction/pass-through logic | `pytest` (per `stack/rules/base-rules.md`) |
| Integration | Not applicable — no DB or cross-service interaction in this checkpoint | — |
| End-to-End | Not applicable — no live conversational loop calls this yet (see Out of Scope) | — |

**Note:** per standing user direction for this ticket batch, `sdlc-unit-test-workflow` and
`sdlc-qa-workflow` are not run as part of this ticket — the table above records what a future
test pass should cover, not work performed in Phase 4.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Checkpoint has no live caller yet (no end-to-end conversational loop exists), so it cannot be demonstrated inside an actual customer conversation | High | Low | Matches the existing FR-6 (`confirm_exact_match`) precedent, which has the same gap for the same reason (Epic 2/3 loop wiring is separate, larger, out-of-scope work). The log statement plus a short manual/script call chain (`parse_booking_intent` → `present_intent_for_verification` → `verify_booking_intent` → `require_verified_intent`) is sufficient to demonstrate the observable checkpoint per the ticket's own "log/terminal demonstration suffices" allowance. |
| Naming the flag `verified` instead of reusing `confirmed` could read as inconsistent with FR-6/9/27 | Low | Low | Deliberate: keeps this checkpoint's language distinct from the customer-facing confirmation flags it is *not* the same concept as (SM-4a is human/operator verification of parsed intent, not a customer confirming a booking or availability change). Documented in Technical Context above. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — SM-4a domain gate | `Low` |
| Task 2 — Booking Agent checkpoint hook | `Low` |
| Task 3 — Operator-facing verification tool | `Low` |
| **Overall** | `Low` |

---

## Out of Scope

- Wiring this checkpoint into a live, end-to-end conversational Booking Agent turn loop
  (`handle_message`) — that loop does not exist yet for any story beyond FR-1 identity
  resolution; wiring it is future Epic 2/3 work, consistent with the existing `confirm_exact_match`
  hook having the same gap.
- Any operator-facing UI/dashboard surface for reviewing or correcting intent — the ticket
  explicitly allows a log/terminal demonstration instead; no `B2B_FE` change in this ticket.
- Registering the new tool into a role-scoped tool registry — no registry-assembly code exists
  yet anywhere in this codebase for any agent/tool.
- Persisting the pending/verified intent across conversation turns (in `SessionState` or a
  `messages` table) — neither exists yet for any story; not needed to satisfy this ticket's AC.
- Availability resolution / nearest-alternative logic itself (FR-7/FR-8 — APPOINTMEN-23/24) —
  separate tickets, currently unimplemented placeholder branches.
- Unit/integration tests — deferred to `sdlc-unit-test-workflow`, currently skipped for this
  ticket batch per explicit standing user override.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-21` · Branch: `feature/APPOINTMEN-21-booking-intent-verification-checkpoint`*
