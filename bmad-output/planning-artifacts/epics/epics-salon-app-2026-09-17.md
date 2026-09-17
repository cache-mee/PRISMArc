---
title: Epics & User Stories — Agentic Appointment Management Engine (Salon Edition)
status: draft
created: 2026-09-17
owner: Business Analyst
sources:
  - bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md (status: final)
  - bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/customer-booking-chat.md
  - bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/staff-owner-manager-chat.md
  - bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/owner-dashboard.md
  - bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/whatsapp-deltas.md
  - stack/rules/base-rules.md (status: approved)
  - stack/stack-proposal.md (status: approved, Gate 3)
  - bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/addendum.md
---

# Epics & User Stories: Agentic Appointment Management Engine — Salon Edition

## 0. Scope & Method

Epics are derived from the PRD's own functional-requirement groupings (§4.1–§4.4) and their technical
dependencies, not from a fixed template. Every acceptance criterion quotes the PRD's own "Consequences
(testable)" language directly where an FR exists for it; where a story exists without a 1:1 FR (the shared
data model, project scaffolding, the WhatsApp integration risk spike), this is called out explicitly as a
non-FR enabler story, not invented product scope.

**MVP boundary respected exactly as PRD §6.1/§6.2 states it.** No story exists here for: payments, POS,
ratings/reviews, offers/discounts, multi-salon, multi-person/family booking, multi-service combination
booking, Owner/Admin managing his own availability or taking appointments, Owner/Admin staff-account
management, staff overriding another staff member's schedule, or defensive/non-happy-path input handling.
Where a PRD FR states a case is a "known limitation, not a defect" (e.g., FR-13, FR-17's retroactive
handling), no story is written to handle it — this is deliberate, not an omission.

**Complexity bar.** S/M/L estimates reflect a working, judge-demoable happy path for a 24-hour build, not
production hardening — consistent with `stack/rules/base-rules.md`'s Testing Requirements framing.

## Epic List

0. Project Scaffolding & Environment Setup
1. Shared Foundation — Domain Model & Identity Resolution (Web Chat)
2. Customer Booking Lifecycle (Web Chat)
3. Staff Availability Management (Web Chat)
4. Owner/Admin Catalog Management (Web Chat)
5. Owner Dashboard (Read-Only)
6. Shared State & Live Reflection (Cross-Cutting)
7. WhatsApp Channel Integration

**Build sequencing:** Epic 0 gates every other epic — no backend, frontend, or database-dependent story in
Epics 1–7 is buildable until the `B2B_BE/` and `B2B_FE/` projects actually exist, run, and can reach a
Postgres instance (Stories 0.1–0.4); it is more foundational than Epic 1, which assumes a running service
to build against. Epic 1 in turn gates Epics 2, 3, 4 (identity + data model precede every persona action).
Epics 2 and 3 gate Epic 5 (dashboard has nothing to show until bookings/availability exist) and Epic 6
(live-reflection has nothing to reflect until writes exist). Epic 7 (WhatsApp) reuses the core logic built
in Epics 1–3 and only adds channel-adapter behavior, so it is sequenced last but its Twilio Sandbox risk
spike (Story 7.5) should start in parallel with Epic 0/1, not after Epics 1–6, per the addendum's flagged
integration-lead-time risk.

---

## Epic 0: Project Scaffolding & Environment Setup

**Goal:** Stand up the `B2B_BE/` and `B2B_FE/` projects per the approved, locked repository layout, wire
local orchestration via Docker Compose, and establish Postgres connectivity — so that a running backend,
running frontend, and reachable database exist before any feature-level story in Epics 1–7 is buildable.
Not derived from any PRD FR — this is foundational build-environment work, the same enabler-story pattern
already used for Story 1.1 and Story 7.5 elsewhere in this document. Traces to `stack/rules/base-rules.md`
(Stack table; Architecture Constraints — Enforced repository layout; Dependency Policy; Security
Baselines; Testing Requirements) and `stack/stack-proposal.md` §5 (Infrastructure) and §9 (Repository
Layout).

### Story 0.1 — Backend project scaffolding

*Enabler story — not tied to a PRD FR; derived from `stack/rules/base-rules.md`'s Architecture Constraints
(Enforced repository layout) and `stack-proposal.md` §9's full `B2B_BE/` tree, same enabler pattern as
Story 1.1.*

As a developer, I want the `B2B_BE/` project initialized per the approved layout with a trivial
health-check endpoint, so that there is a running FastAPI service to build every backend story in this
document against.

**Acceptance Criteria:**
- `B2B_BE/pyproject.toml` exists, targeting Python 3.12+ (`base-rules.md` Stack table) and declaring the
  core dependency set named in `base-rules.md`'s Dependency Policy at minimum (`fastapi`, `uvicorn`,
  `sqlalchemy`, `alembic`, `pydantic` v2, `pytest`); `twilio` and an LLM provider SDK may be added when the
  stories that need them (Epic 7, Epics 2–4) are built, not required here.
- `B2B_BE/Dockerfile` exists and builds the service (`base-rules.md` Stack table — Infra row;
  `stack-proposal.md` §5).
- `B2B_BE/app/main.py` exists as the FastAPI entrypoint; `B2B_BE/app/config.py` exists, reading all
  secrets/connection settings from environment variables per `base-rules.md`'s Security Baselines (no
  hard-coded secrets), with a `.env.example` documenting the required variables and the real `.env`
  git-ignored.
- The package skeleton exists exactly per `stack-proposal.md` §9's enforced tree: `app/api/` (`chat.py`,
  `appointments.py`, `availability.py`, `dashboard.py`, `webhooks/whatsapp.py`), `app/agent/`
  (`booking_agent.py`, `manager_agent.py`, `prompts/`, `state/`), `app/tools/` (`services.py`, `staff.py`,
  `availability.py`, `appointments.py`), `app/domain/` (`appointments.py`, `availability.py`,
  `conflicts.py`), `app/models/`, `app/repositories/` — as stub/empty modules; implementing their contents
  is the scope of later stories (Epics 1–7), not this one.
- `B2B_BE/tests/` skeleton exists and is runnable via `pytest` (base-rules.md Testing Requirements), even
  with zero or a trivially passing test.
- A `GET /health` (or equivalent) endpoint returns a 200 response when the service is run — this is the
  acceptance bar because it proves the service actually starts and serves a request, not merely that the
  files above exist.

**Dependencies:** None (foundational — gates Story 1.1 and every other backend-touching story in this
document).
**Complexity:** M

### Story 0.2 — Frontend project scaffolding

*Enabler story — not tied to a PRD FR; derived from `stack/rules/base-rules.md`'s Architecture Constraints
(Enforced repository layout) and `stack-proposal.md` §9's full `B2B_FE/` tree, same enabler pattern as
Story 1.1.*

As a developer, I want the `B2B_FE/` project initialized per the approved layout with a trivial rendered
page, so that there is a running React app to build every frontend-facing story in this document against.

**Acceptance Criteria:**
- `B2B_FE/package.json` exists declaring React 18+, TypeScript 5+, and Vite 5+ per `base-rules.md`'s Stack
  table.
- `B2B_FE/Dockerfile` exists and builds the app (`base-rules.md` Stack table — Infra row;
  `stack-proposal.md` §5).
- `tsconfig.json` has `"strict": true` per `base-rules.md`'s Language & Style section for the frontend.
- The `src/` skeleton exists exactly per `stack-proposal.md` §9's enforced tree: `src/chat/`,
  `src/dashboard/`, `src/shared/`, `src/api/` — as stub/empty modules; implementing their contents is the
  scope of later stories (Epics 2–7), not this one.
- `eslint` (`@typescript-eslint/recommended` + `eslint-plugin-react-hooks`) and `prettier` are configured
  at default settings per `base-rules.md`'s Language & Style section.
- `B2B_FE/tests/` skeleton exists; no test is required to exist yet, only the tooling path (Vitest + React
  Testing Library, per `base-rules.md` Testing Requirements) wired if/when frontend tests are written.
- Running the dev server renders a trivial page (e.g., a placeholder landing route) in a browser — this is
  the acceptance bar because it proves the app actually runs, not merely that the files above exist.

**Dependencies:** None (foundational — gates every frontend-facing story in this document, including
Epic 5's Dashboard and the chat UI stories referenced across Epics 2–4, 7).
**Complexity:** S

### Story 0.3 — Local orchestration via Docker Compose

*Enabler story — not tied to a PRD FR; derived from `base-rules.md`'s Stack table (Infra row) and
`stack-proposal.md` §5 (Infrastructure) and §9, which specify a root `docker-compose.yml` orchestrating
backend, frontend, and Postgres for local dev/demo parity.*

As a developer, I want a root `docker-compose.yml` wiring the backend, frontend, and Postgres together, so
that the full stack runs locally with one command for both development and the eventual demo.

**Acceptance Criteria:**
- `docker-compose.yml` exists at the repository root, orchestrating three services — backend
  (`B2B_BE/Dockerfile`), frontend (`B2B_FE/Dockerfile`), and Postgres 16+ (`base-rules.md` Stack table;
  `stack-proposal.md` §5) — as orchestration configuration only, not application code
  (`stack-proposal.md` §5's explicit clarification that this file does not conflict with the `CLAUDE.md`
  `B2B_BE/`/`B2B_FE/` split).
- `docker-compose up` brings up all three services without further manual intervention.
- The frontend can reach the backend's health-check endpoint (Story 0.1) over the network the compose file
  establishes — this proves end-to-end wiring, not merely that each container starts independently.
- Postgres connection details (host, port, credentials) are supplied to the backend via environment
  variables consumed by `app/config.py` (Story 0.1), never hard-coded, per `base-rules.md`'s Security
  Baselines.

**Dependencies:** Story 0.1, Story 0.2.
**Complexity:** S

### Story 0.4 — Database connectivity and initial migration

*Enabler story — not tied to a PRD FR; this is the explicit dependency Story 1.1 (shared data store
entities) needs to be buildable at all, per `base-rules.md`'s Dependency Policy (`alembic` as the required
migrations tool) and `stack-proposal.md` §3/§9.*

As a developer, I want the backend able to connect to Postgres and run an Alembic migration, so that
Epic 1's shared data store entities have a database to be created against.

**Acceptance Criteria:**
- `B2B_BE/alembic/` is initialized and configured to read the DB connection string from `app/config.py`'s
  environment-derived settings (Story 0.1), not a hard-coded value.
- The backend successfully opens a connection to the Postgres service brought up by Story 0.3 (verifiable
  via a simple query or by extending the health-check endpoint to report DB connectivity).
- An initial Alembic migration — even one that creates no domain tables, or only a trivial marker table —
  runs successfully via `alembic upgrade head` against that Postgres instance, proving the migration path
  itself works before Story 1.1's actual entity tables are authored against it.

**Dependencies:** Story 0.1 (backend + `app/config.py`), Story 0.3 (Postgres service reachable).
**Complexity:** S

---

## Epic 1: Shared Foundation — Domain Model & Identity Resolution (Web Chat)

**Goal:** Establish the shared data store's core entities and the phone-number identity-resolution flow
for all three personas on Web Chat. Every persona-specific action in Epics 2–4 depends on identity being
resolved first, and every surface depends on these entities existing and being shared. This epic in turn
depends on Epic 0 having stood up a running backend, running frontend, and reachable Postgres instance —
none of this epic's stories are buildable before Epic 0's scaffolding exists. Traces to PRD §3
(Glossary — Shared Data Store), §4.4, §4.1 FR-1/FR-2, §4.2 FR-14, §4.3 FR-24, §7 (identity/auth
minimalism NFR).

### Story 1.1 — Shared data store entities exist
*Enabler story — not a single FR; derived from PRD §3 Glossary and §4.4, and addendum.md §2.1's minimal
data model, without adopting any Architect-owned schema/table decision.*

As a system, the shared data store defines Salon, Staff (with a role distinguishing Owner/Admin from
Staff), Service, Customer, Booking, and Availability entities, so that the Booking Agent, Manager Agent,
and Dashboard all read and write one consistent state.

**Acceptance Criteria:**
- One Salon record exists (single-salon demo — PRD §3, Glossary: "Salon").
- Staff records exist for Ramesh (role: Owner/Admin), Meena (role: Staff), and Arjun (role: Staff) —
  seeded, not created via signup (PRD §4.2 FR-14, §4.3 FR-24; addendum.md §1 "Identity model").
- Ramesh's Staff record is never returned as a bookable service provider or listed on the Dashboard's
  Staff list (PRD §9.1 Decision 1; §4.1 FR-13; §4.2 FR-19).
- Service, Customer, Booking, and Availability entities exist with the relationships implied by PRD §3's
  Glossary definitions (a Booking references one Customer, one Service, one Staff member, one date/time;
  an Availability record marks a Staff member's window as blocked or open).
- A write made against any entity through one surface is readable by a query against the same entity from
  any other surface (this is the precondition Epic 6's stories validate observably; this story only
  establishes that the store itself is single and shared, not surface-siloed).

**Dependencies:** Story 0.4 (backend, Postgres connectivity, and a working migration path must exist
before any entity table can be created against it).
**Complexity:** M

### Story 1.2 — FR-1: Web Chat customer identity resolution

As a Customer using Web Chat, I want the Booking Agent to ask for my phone number and look it up before
doing anything else, so that the agent knows whether I'm a known customer before acting on my request.

**Acceptance Criteria (PRD FR-1 Consequences):**
- The agent asks for a phone number before any booking, browse-history, cancel, or reschedule action is
  completed on Web Chat.
- A number that matches an existing record results in the agent greeting the Customer by name and
  proceeding directly to the stated intent (no name question asked).
- A number with no match results in Story 1.3 (FR-2) firing before any booking action proceeds.

**Dependencies:** Story 1.1.
**Complexity:** S

### Story 1.3 — FR-2: New-customer record creation

As a new Customer whose phone number has no match, I want the Booking Agent to ask for my name and create
my customer record, so that I can proceed straight to booking without a separate signup step.

**Acceptance Criteria (PRD FR-2 Consequences):**
- A new Customer record (phone number + name) exists after this exchange, retrievable on a subsequent
  conversation with the same phone number.
- The Customer is not asked for their phone number again in the same conversation once resolved.

**Dependencies:** Story 1.2.
**Complexity:** S

### Story 1.4 — FR-14: Web Chat Owner/Admin identity resolution

As Ramesh (Owner/Admin) using Web Chat, I want the Manager Agent to ask for my phone number and match it
against my pre-seeded record, so that I'm recognized as Owner/Admin and granted the right permissions.

**Acceptance Criteria (PRD FR-14 Consequences, Web Chat clause):**
- A Web Chat session with a matching pre-seeded number results in the Manager Agent granting
  Owner/Admin-permitted actions (FR-15–FR-17, FR-19) without a signup step.
- A non-matching number is out of scope for this demo (no fallback flow defined — PRD explicit limitation,
  not a gap in this story).

**Dependencies:** Story 1.1.
**Complexity:** S

### Story 1.5 — FR-24: Web Chat Staff identity resolution

As Meena or Arjun (Staff) using Web Chat, I want the Manager Agent to ask for my phone number and match it
against the pre-seeded staff records, so that the agent knows specifically which of us is speaking.

**Acceptance Criteria (PRD FR-24 Consequences, Web Chat clause):**
- The Manager Agent's response to an availability-change request always reflects which specific Staff
  member is understood to be speaking (never ambiguous between Meena and Arjun).

**Dependencies:** Story 1.1.
**Complexity:** S

---

## Epic 2: Customer Booking Lifecycle (Web Chat)

**Goal:** Deliver the full natural-language booking lifecycle for a Web Chat customer — browse, state
intent, resolve via one of three paths, confirm/create, view history, cancel, reschedule. Realizes UJ-1,
UJ-2, UJ-3; validated by SM-1. Traces to PRD §4.1, FR-4–FR-13.

### Story 2.1 — FR-4: Browse services & pricing

As a Customer, I want to ask to see the current services and prices at any point in the conversation, so
that I can decide what to book without leaving the chat.

**Acceptance Criteria (PRD FR-4 Consequences):**
- The agent returns the current catalog (service names + prices) reflecting the latest state of the
  Shared Data Store, including any change the Owner/Admin applied via FR-14/FR-15/FR-16 before this
  request.

**Dependencies:** Story 1.2 (or 1.3), Story 1.1.
**Complexity:** S

### Story 2.2 — FR-5: State a booking intent in natural language

As a Customer, I want to state what I want (service, and optionally a date/time and/or a staff
preference) in free text, so that I don't have to navigate a slot-picker UI.

**Acceptance Criteria (PRD FR-5 Consequences):**
- A Service is required for the agent to proceed; date/time and staff preference are each optional and
  independently omittable.
- The agent correctly extracts Service, and where stated, date/time and staff preference, for at least
  the demo's rehearsed happy-path phrasings.

**Dependencies:** Story 1.2 (or 1.3).
**Complexity:** M

### Story 2.3 — FR-13: Staff preference limited to bookable staff

As a Customer, I want my staff preference to be limited to staff who actually take appointments, so that
I only get offered a provider who can be booked.

**Acceptance Criteria (PRD FR-13 Consequences):**
- Only Meena and Arjun are accepted/offered as a staff preference; Ramesh is never offered or accepted
  (PRD §9.1 Decision 1).
- A stated preference for "Ramesh" as a service provider is a known, unmodeled limitation in this
  happy-flow-only demo — no rejection flow or error path is built for it.

**Dependencies:** Story 2.2.
**Complexity:** S

### Story 2.4 — SM-4a: Booking-intent human-verification checkpoint

As a judge evaluating the build, I want a human-verification checkpoint on the Booking Agent's parsed
intent before it is acted on, so that the Human-Verification-40 evaluation weighting (PRD §8) has an
observable moment tied to intent parsing.

**Acceptance Criteria (PRD §8 SM-4a):**
- A human reviews, and corrects where needed, the Booking Agent's parsed booking intent (Service,
  date/time, Staff preference — FR-5) before it is acted on — i.e., before Stories 2.5/2.6/2.7 (FR-6/7/8)
  proceed on it.
- This checkpoint is not Customer-visible; the Customer-facing conversation reads as an uninterrupted
  exchange regardless of whether a human reviewed the intermediate step (`customer-booking-chat.md` §3.4).
- **Open, not resolved here:** whether this checkpoint needs a dedicated operator-facing UI hook or is
  demonstrated via logs/terminal is an explicit Architect/Developer decision
  (`customer-booking-chat.md` §3.4, §7.1) — this story only guarantees the checkpoint's existence and
  placement in the flow, not its presentation mechanism.

**Dependencies:** Story 2.2, Story 2.3.
**Complexity:** S

### Story 2.5 — FR-6: Exact-time resolution — direct confirmation

As a Customer who named an exact, available date/time (and staff, if named), I want the Booking Agent to
confirm that slot directly, so that I don't have to pick from a list when what I asked for is already
open.

**Acceptance Criteria (PRD FR-6 Consequences):**
- The agent's response names the Service, date/time, and assigned Staff member, and asks for explicit
  confirmation before creating the Booking.

**Dependencies:** Story 2.2, Story 2.3, Story 2.4.
**Complexity:** S

### Story 2.6 — FR-7: Day-only resolution — list that day's available slots

As a Customer who named a day but no specific time, I want the Booking Agent to list that day's available
slots, so that I can pick one.

**Acceptance Criteria (PRD FR-7 Consequences):**
- The listed slots reflect only currently open Availability for the relevant Staff member(s) at the time
  of the request (excludes blocked time and already-booked Slots).
- If a Staff preference was stated, only that Staff member's open slots are listed.

**Dependencies:** Story 2.2, Story 2.3, Story 2.4, Story 1.1 (Availability/Booking entities).
**Complexity:** M

### Story 2.7 — FR-8: Exact-time-unavailable resolution — nearest alternative(s)

As a Customer whose exact requested time is unavailable, I want the Booking Agent to suggest the nearest
alternative(s) with a reason, so that I can still get booked without re-stating my whole request.

**Acceptance Criteria (PRD FR-8 Consequences):**
- The agent names at least one alternative slot when one exists within the same Staff-preference
  constraint (or salon-wide if none was stated).
- The agent's response states the reason the original time is unavailable (e.g., already booked,
  blocked).

**Dependencies:** Story 2.2, Story 2.3, Story 2.4, Story 1.1.
**Complexity:** M

### Story 2.8 — SM-4b: Alternative-slot human-verification checkpoint

As a judge evaluating the build, I want a human-verification checkpoint on the Booking Agent's
alternative-slot reasoning before it is offered to the customer, so that the Human-Verification-40
weighting has an observable moment tied to the alternative-suggestion path specifically.

**Acceptance Criteria (PRD §8 SM-4b):**
- A human reviews the Booking Agent's reasoning when it suggests an alternative time slot (FR-8), before
  that alternative is offered to the Customer.
- Not Customer-visible — zero UI change on the Customer-facing conversation
  (`customer-booking-chat.md` §3.4).
- **Open, not resolved here:** same operator-UI-vs-log question as Story 2.4 — an Architect/Developer
  decision, not a BA or PM decision.

**Dependencies:** Story 2.7.
**Complexity:** S

### Story 2.9 — FR-9: Booking confirmation and creation

As a Customer, I want my Booking to be created only after I explicitly confirm a proposed slot, so that
nothing is booked on my behalf without my say-so.

**Acceptance Criteria (PRD FR-9 Consequences):**
- No Booking record exists in the Shared Data Store until an explicit customer confirmation message
  follows a proposed slot.
- Once confirmed, the Booking is immediately queryable (Story 2.10) and immediately visible on the
  Dashboard (Story 5.2) and to any subsequent availability check by any Customer or Staff member (Story
  6.1).

**Dependencies:** Story 2.5, Story 2.6, Story 2.7 (whichever resolution path led here), Story 2.8 (for the
FR-8 path specifically).
**Complexity:** M

### Story 2.10 — FR-10: View booking history

As a Customer, I want to see my upcoming and past bookings on request, so that I can check what I have
scheduled.

**Acceptance Criteria (PRD FR-10 Consequences):**
- The response distinguishes upcoming Bookings from past ones.
- Only the requesting Customer's own Bookings are returned (never another Customer's).

**Dependencies:** Story 2.9, Story 1.2/1.3.
**Complexity:** S

### Story 2.11 — FR-11: Cancel a booking

As a Customer, I want to cancel an existing upcoming booking on request, so that the slot is freed and my
booking list is accurate.

**Acceptance Criteria (PRD FR-11 Consequences):**
- The cancelled Booking no longer appears as an active upcoming Booking in Story 2.10 results.
- The freed slot is immediately available to be offered to another Customer (Story 2.6/2.7) with no
  further action needed.
- Per `customer-booking-chat.md` §3.6's documented UX decision, no pre-write confirm gate is built for
  cancel (FR-11's stated consequences do not include one, unlike FR-9/FR-18/FR-27) — this is a UX-added
  interpretation forwarded to the PM as informational, not a literal FR requirement; not re-decided here
  (see §6 Gap Register below).

**Dependencies:** Story 2.10.
**Complexity:** S

### Story 2.12 — FR-12: Reschedule as cancel + rebook

As a Customer, I want to reschedule an existing booking, so that I end up with one booking at the new time
without having to cancel and rebook as two separate asks.

**Acceptance Criteria (PRD FR-12 Consequences):**
- The original Slot is freed (per Story 2.11's consequences) before or atomically with the new Booking
  being proposed.
- The Customer ends the conversation with exactly one active Booking reflecting the new time (not two).

**Dependencies:** Story 2.11, Stories 2.5–2.9 (re-run of the normal booking flow for the new time).
**Complexity:** M

---

## Epic 3: Staff Availability Management (Web Chat)

**Goal:** Let Meena and Arjun manage their own Availability conversationally, with conflict checking
against existing Bookings before any change applies, and enforce the role boundaries that keep this
action Staff-only. Realizes UJ-4; validated by SM-2. Traces to PRD §4.3, FR-25–FR-30.

### Story 3.1 — FR-25: State an availability change in natural language

As Meena or Arjun, I want to state a block or unblock of my own availability in natural language, so that
I can signal my schedule without a form or grid.

**Acceptance Criteria (PRD FR-25 Consequences):**
- The agent correctly extracts which Staff member, which window (date/time range), and whether it is a
  block or an unblock, for at least the demo's rehearsed happy-path phrasings.

**Dependencies:** Story 1.5.
**Complexity:** M

### Story 3.2 — FR-26: Conflict check before applying an availability change

As Meena or Arjun, I want the Manager Agent to check my proposed block against my existing bookings before
applying it, so that I don't accidentally block time I'm already committed to a customer for.

**Acceptance Criteria (PRD FR-26 Consequences):**
- If the proposed block window contains an existing Booking, the agent's response names which Booking(s)
  cause the conflict (e.g., "Friday 10am is already booked with a customer for a haircut") — it is not a
  silent rejection.
- If no conflict exists, the block is confirmed and applied (Story 3.4).

**Dependencies:** Story 3.1, Story 1.1 (Booking entity). **Sequencing note:** demonstrating the
conflict-found path (per `staff-owner-manager-chat.md` §3.2) requires at least one existing Booking against
the staff member in question — i.e., Epic 2's booking-creation stories should be functionally
demoable/seeded before this path is rehearsed, even though the check logic itself does not require Epic 2
to be "done." Flagged in §6 Gap Register as a build-sequencing dependency, not a functional one.
**Complexity:** M

### Story 3.3 — SM-4c: Conflict-detection human-verification checkpoint

As a judge evaluating the build, I want a human-verification checkpoint on the Manager Agent's
conflict-detection outcome before an availability change or booking is finalized, so that the
Human-Verification-40 weighting has an observable moment tied to conflict detection specifically.

**Acceptance Criteria (PRD §8 SM-4c):**
- A human reviews the Manager Agent's conflict-detection outcome (FR-26) before an Availability change
  (FR-27) or Booking (FR-9) is finalized.
- Not Staff-visible — zero UI change on the Staff-facing conversation
  (`staff-owner-manager-chat.md` §3.3).
- **Open, not resolved here:** same operator-UI-vs-log question as Stories 2.4/2.8 — an
  Architect/Developer decision.

**Dependencies:** Story 3.2.
**Complexity:** S

### Story 3.4 — FR-27: Confirmation required before an availability change applies

As Meena or Arjun, I want no block/unblock to apply until I've explicitly confirmed the agent's restated
version of it, so that nothing changes on my schedule without my explicit say-so.

**Acceptance Criteria (PRD FR-27 Consequences):**
- The Availability record is unchanged if the conversation ends before an explicit confirmation.
- Once confirmed and applied, the change is immediately reflected in the Booking Agent's next
  availability check for that Staff member (Stories 2.6/2.7) and in the Dashboard view (Story 5.2) — no
  separate sync step, no delay (also validated at Epic 6, Story 6.1).

**Dependencies:** Story 3.2, Story 3.3.
**Complexity:** S

### Story 3.5 — FR-28: Staff cannot manage the catalog

As Meena or Arjun, when I ask about adding/editing/deleting a service or price, I want to be told that's
not something I manage, so that the boundary between my role and the Owner/Admin's is clear.

**Acceptance Criteria (PRD FR-28 Consequences):**
- A catalog-change request from a Staff-identified session is not a permitted action (per
  `staff-owner-manager-chat.md` §5, surfaced as a plain one-line redirect, not an error state).

**Dependencies:** Story 1.5.
**Complexity:** S

### Story 3.6 — FR-29: Staff cannot view the staff list or dashboard

As Meena or Arjun, I want any request for the staff list or dashboard-equivalent data to be declined, so
that I only ever see my own schedule information.

**Acceptance Criteria (PRD FR-29 Consequences):**
- No conversational response to a Staff-identified session returns another Staff member's schedule, the
  full Staff list, or Dashboard-equivalent data.

**Dependencies:** Story 1.5.
**Complexity:** S

### Story 3.7 — FR-30: Staff cannot override another staff member's schedule

As Meena or Arjun, when I ask to change the other's schedule, I want to be told that's not something I can
do, so that only the schedule owner controls their own availability.

**Acceptance Criteria (PRD FR-30 Consequences):**
- A request from Meena's identified session naming Arjun's schedule (or vice versa) is not a permitted
  action.

**Dependencies:** Story 1.5.
**Complexity:** S

---

## Epic 4: Owner/Admin Catalog Management (Web Chat)

**Goal:** Let Ramesh manage the service/pricing catalog conversationally, with explicit confirmation before
any change applies, and enforce the role boundaries that keep catalog management Owner/Admin-only while
keeping him out of staff-scheduling actions. Realizes UJ-5. Traces to PRD §4.2, FR-15–FR-18, FR-21–FR-23.

### Story 4.1 — FR-15: Add a service via natural language

As Ramesh, I want to state a new service name and price in natural language, so that I can expand the
catalog without editing a spreadsheet.

**Acceptance Criteria (PRD FR-15 Consequences):**
- The new Service does not exist in the Shared Data Store until Ramesh has explicitly confirmed the
  agent's restated details.
- Once confirmed, the new Service is immediately returned by Story 2.1 (Customer catalog browse) with no
  separate publish step.

**Dependencies:** Story 1.4.
**Complexity:** S

### Story 4.2 — FR-16: Edit a service or price via natural language

As Ramesh, I want to state a change to an existing service's name and/or price, so that I can update the
catalog without editing a spreadsheet.

**Acceptance Criteria (PRD FR-16 Consequences):**
- The prior price/name is no longer returned by Story 2.1 once the change is confirmed and applied.
- The updated Service is immediately reflected in any Customer-side quote or catalog browse afterward.

**Dependencies:** Story 4.1 (or seeded catalog data), Story 1.4.
**Complexity:** S

### Story 4.3 — FR-17: Delete a service via natural language

As Ramesh, I want to state that a service should be removed, so that it's no longer offered.

**Acceptance Criteria (PRD FR-17 Consequences):**
- The removed Service is no longer offered or returned by Story 2.1 after confirmation.
- Existing Bookings already made against that Service before removal are not modeled as needing
  retroactive handling in this happy-flow-only demo (PRD explicit known limitation — not built).

**Dependencies:** Story 4.1 (or seeded catalog data), Story 1.4.
**Complexity:** S

### Story 4.4 — FR-18: Confirmation required before catalog changes apply

As Ramesh, I want no catalog change to apply until I've explicitly confirmed the agent's restated version
of it, so that nothing changes in the catalog without my explicit say-so.

**Acceptance Criteria (PRD FR-18 Consequences):**
- The catalog is unchanged if the conversation ends before an explicit confirmation message, across all
  of add (4.1), edit (4.2), and delete (4.3).

**Dependencies:** Story 4.1, Story 4.2, Story 4.3.
**Complexity:** S

### Story 4.5 — FR-21: Owner/Admin cannot manage own availability

As Ramesh, when I ask to block or unblock my own time, I want the system to not treat that as a permitted
action, so that the product's admin-only framing of my role stays consistent.

**Acceptance Criteria (PRD FR-21 Consequences):**
- A request from Ramesh's identified session to block or unblock availability is not a permitted action
  under the role matrix (PRD §9.1 Decision 1).

**Dependencies:** Story 1.4.
**Complexity:** S

### Story 4.6 — FR-22: Owner/Admin cannot manage staff accounts

As Ramesh, I want no path to add, remove, or edit a staff account, so that the staff list stays view-only
as scoped for this demo.

**Acceptance Criteria (PRD FR-22 Consequences):**
- No conversational or Dashboard action exists that creates, deletes, or edits a Staff record.

**Dependencies:** Story 1.4.
**Complexity:** S

### Story 4.7 — FR-23: Owner/Admin cannot override staff schedules

As Ramesh, when I ask to change Meena's or Arjun's availability directly, I want that request declined, so
that staff retain control of their own schedules.

**Acceptance Criteria (PRD FR-23 Consequences):**
- A request from Ramesh's identified session to change Meena's or Arjun's Availability is rejected or not
  offered as an available action (per `staff-owner-manager-chat.md` §5's plain one-line redirect pattern).

**Dependencies:** Story 1.4.
**Complexity:** S

---

## Epic 5: Owner Dashboard (Read-Only)

**Goal:** Give Ramesh a read-only, non-conversational view of the Staff list and current Bookings.
Realizes UJ-6. Traces to PRD §4.2, FR-19–FR-20.

### Story 5.1 — FR-19: View staff list via dashboard (read-only)

As Ramesh, I want to see the current staff list on the dashboard, so that I know who's on the roster
without asking anyone.

**Acceptance Criteria (PRD FR-19 Consequences):**
- The Staff list shown is not editable from the Dashboard — no add/remove/edit control exists on this
  surface.
- The Staff list shown contains exactly Meena and Arjun — not Ramesh (PRD §9.1 Decision 1).

**Dependencies:** Story 1.1 (seeded Staff records).
**Complexity:** S

### Story 5.2 — FR-20: View bookings via dashboard (read-only)

As Ramesh, I want to see current bookings (today's or the week's) per staff member on the dashboard, so
that I have an accurate, current picture of the day without touching a spreadsheet.

**Acceptance Criteria (PRD FR-20 Consequences):**
- A Booking created via the Booking Agent (Story 2.9) after the Dashboard was last loaded is visible on
  the Dashboard without Ramesh performing any catalog or availability action himself (proof of Shared
  Data Store — validated further at Story 6.2).
- No booking, cancellation, or edit action is available from the Dashboard itself.

**Dependencies:** Story 5.1, Story 2.9 (at least one booking to display).
**Complexity:** M

---

## Epic 6: Shared State & Live Reflection (Cross-Cutting)

**Goal:** Prove the demo's core technical claim — the Booking Agent, Manager Agent, and Dashboard all read
from and write to one Shared Data Store, so a change on one surface is visible on the others without a
manual refresh, restart, or separate sync step. This is the PRD's own §4.4 cross-cutting grouping,
validated by SM-2 and SM-3, and is kept as its own epic rather than folded silently into Epics 2–5 so it
isn't lost as a demo priority. Traces to PRD §4.4, FR-31–FR-32.

### Story 6.1 — FR-31: Availability and catalog changes are immediately visible to the Booking Agent

As a Customer, I want any staff availability change or catalog change that's already been confirmed to be
reflected the very next time I ask, so that I never get offered a slot or price that's already stale.

**Acceptance Criteria (PRD FR-31 Consequences):**
- A Customer conversation started immediately after a Staff member confirms a block never offers that
  blocked window as available (validates against Story 3.4).
- A Customer conversation started immediately after Ramesh confirms a price change or new Service
  reflects the new price/Service on the very next catalog browse or booking attempt (validates against
  Story 4.4).

**Dependencies:** Story 3.4 (FR-27), Story 4.4 (FR-18), Story 2.6/2.7 (the Booking Agent's own query
paths).
**Complexity:** M

### Story 6.2 — FR-32: Dashboard reflects the shared store live

As Ramesh, I want the Dashboard's staff list and bookings view to reflect changes made through either
agent without me doing anything, so that what I'm looking at is always current.

**Acceptance Criteria (PRD FR-32 Consequences):**
- A Booking created via the Booking Agent, or an Availability change confirmed via the Manager Agent,
  appears on the Dashboard within the same demo session without a manual data re-entry step by Ramesh.

**Dependencies:** Story 5.2, Story 2.9 (FR-9), Story 3.4 (FR-27).
**Complexity:** M

---

## Epic 7: WhatsApp Channel Integration

**Goal:** Extend the same Booking Agent and Manager Agent core (built in Epics 1–4) to the WhatsApp
channel, with channel-appropriate identity-skip behavior and plain-text-only formatting, per the
channel-parity NFR (PRD §7) and `whatsapp-deltas.md`. Kept as its own epic, not folded silently into the
Web Chat stories, given its own flagged Twilio integration-lead-time risk (addendum.md §3). Traces to PRD
§4.1 FR-3, §4.2/§4.3 FR-14/FR-24 (WhatsApp clause), §7 channel-parity NFR.

### Story 7.1 — FR-3: WhatsApp customer identity resolution (channel-aware)

As a Customer messaging via WhatsApp, I want the Booking Agent to recognize me from the number I'm already
messaging from, so that I'm never asked for a phone number I've already implicitly provided.

**Acceptance Criteria (PRD FR-3 Consequences):**
- No phone-number question is ever asked on the WhatsApp channel.
- A WhatsApp message from a known number results in a name-based greeting with no further identity
  questions.
- A WhatsApp message from an unknown number results in exactly one question (name) before proceeding.

**Dependencies:** Story 1.1, Story 1.2/1.3 (same underlying identity-match logic, different adapter).
**Complexity:** S

### Story 7.2 — FR-14/FR-24 (WhatsApp clause): WhatsApp Staff/Owner identity resolution

As Ramesh, Meena, or Arjun messaging via WhatsApp, I want the Manager Agent to recognize me from the
channel-supplied number without asking, so that I go straight into my role-appropriate conversation.

**Acceptance Criteria (PRD FR-14 and FR-24 Consequences, WhatsApp clause):**
- The phone-number question in the Web Chat flow (Stories 1.4/1.5) is skipped entirely; the first message
  is directly the role-based greeting.
- A non-matching number is out of scope for this demo, same as Web Chat (no fallback flow defined).

**Dependencies:** Story 1.4, Story 1.5.
**Complexity:** S

### Story 7.3 — Plain-text-only Customer booking flow on WhatsApp

*Not a distinct FR — required by the channel-parity NFR (PRD §7) and specified in `whatsapp-deltas.md` §1.*

As a Customer using WhatsApp, I want catalog listings, slot choices, and confirmations presented as plain
numbered-text lists and yes/no questions instead of tappable buttons/chips, so that the same booking
behavior works reliably within Twilio WhatsApp Sandbox's plain-text constraints.

**Acceptance Criteria (`whatsapp-deltas.md` §1):**
- Slot choices (Stories 2.6, 2.7) render as a numbered plain-text list ("1) 11:00 AM ... Reply with a
  number or a time"), not chips.
- Booking confirmation (Story 2.9) and the confirm step inside reschedule (Story 2.12) render as a plain
  yes/no text question, not a Confirm/Cancel button pair.
- The catalog (Story 2.1) renders as a plain text list, not a structured card.
- Booking history, cancel, and reschedule (Stories 2.10, 2.11, 2.12) render the same content as Web Chat
  as plain WhatsApp text, with no behavioral difference from Web Chat.
- No WhatsApp-specific variation exists in the underlying intent-parsing or resolution logic — only
  rendering format differs, per the channel-parity NFR.

**Dependencies:** Story 7.1, Stories 2.1, 2.6, 2.7, 2.9, 2.10, 2.11, 2.12.
**Complexity:** M

### Story 7.4 — Plain-text-only Staff/Owner Manager Agent flow on WhatsApp

*Not a distinct FR — required by the channel-parity NFR (PRD §7) and specified in `whatsapp-deltas.md` §2.*

As Meena, Arjun, or Ramesh using WhatsApp, I want availability and catalog confirmations presented as
plain yes/no text questions, so that the same Manager Agent behavior works on WhatsApp as on Web Chat.

**Acceptance Criteria (`whatsapp-deltas.md` §2):**
- Availability block/unblock confirmation (Story 3.4) and catalog add/edit/delete confirmation (Stories
  4.1–4.3) each render as a plain yes/no text question, not a button pair.
- The conflict-named response (Story 3.2) needs no content delta — it is already plain text on Web Chat.
- Role-boundary redirects (Stories 3.5–3.7, 4.5–4.7) are identical copy and behavior on WhatsApp — no
  channel-specific variation.
- SM-4c (Story 3.3) has no channel delta — it is a backend/build-time mechanism independent of channel.

**Dependencies:** Story 7.2, Stories 3.2, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 4.5, 4.6, 4.7.
**Complexity:** S

### Story 7.5 — Twilio WhatsApp Sandbox go/no-go integration spike

*Risk-mitigation enabler, not a persona story tied to an FR — surfaces addendum.md §3's explicitly flagged
integration risk so it is not discovered late.*

As the delivery team, I want an early Twilio WhatsApp Sandbox check (webhook reachable, inbound/outbound
message round-trip verified end-to-end) before building the channel-specific flows in Stories 7.1–7.4 on
top of it, so that WhatsApp Business API/Twilio setup lead-time risk (addendum.md §3, "WhatsApp Business
API / Twilio setup lead time within a 24-hour window") is retired early rather than discovered near the
demo.

**Acceptance Criteria:**
- A test inbound WhatsApp message reaches the backend webhook and a reply is delivered back through
  Twilio, using only Sandbox (not a production WhatsApp Business Account), before any Story 7.1–7.4 work
  is considered started.
- Whether Twilio Sandbox can reliably render quick-reply/interactive button messages for this build is
  answered (go/no-go) — if no, Story 7.3/7.4's plain-text-only design (already the default per
  `whatsapp-deltas.md`) is confirmed as final rather than revisited; if yes, the team explicitly decides
  whether to adopt richer affordances instead (an Architect/Developer decision, not decided here).

**Dependencies:** None — should start in parallel with Epic 0/1, not gated behind either, given the
lead-time risk.
**Complexity:** S (small scope, but time-boxed early rather than skipped — see §6 Gap Register)

---

## Story Count Summary

| Epic | Stories |
|---|---|
| 0. Project Scaffolding & Environment Setup | 4 |
| 1. Shared Foundation — Domain Model & Identity Resolution | 5 |
| 2. Customer Booking Lifecycle | 12 |
| 3. Staff Availability Management | 7 |
| 4. Owner/Admin Catalog Management | 7 |
| 5. Owner Dashboard | 2 |
| 6. Shared State & Live Reflection | 2 |
| 7. WhatsApp Channel Integration | 5 |
| **Total** | **44** |

## 6. Gap Register & Resolution Record

Per this agent's evidence expectations, every item below cites its source and states whether it was
resolved in this artefact or is carried forward/escalated. No item below was resolved by inventing
business intent not present in the source material.

| # | Item | Source | Status |
|---|---|---|---|
| 1 | Whether SM-4a/SM-4b/SM-4c need a dedicated operator-facing UI hook or a log/terminal demonstration is sufficient | `customer-booking-chat.md` §3.4/§7, `staff-owner-manager-chat.md` §3.3/§8 | Carried forward, not resolved here — explicitly an Architect/Developer decision per the task brief; captured as an open note on Stories 2.4, 2.8, 3.3 so the checkpoints themselves aren't dropped from scope regardless of how this resolves. |
| 2 | Whether Cancel (FR-11/Story 2.11) should have a symmetric pre-write confirm gate like FR-9/FR-18/FR-27 | `customer-booking-chat.md` §3.6, §7 (UX-flagged, forwarded to PM as informational) | Not re-decided here — this artefact follows the PRD's literal FR-11 text (no confirm-gate consequence stated) per this agent's evidence-expectations rule against inferring business intent beyond the source; flagged for PM attention if parity is wanted. |
| 3 | Whether staff-side conflict handling (Story 3.2) should mirror the Booking Agent's alternative-suggestion pattern (FR-8) | `staff-owner-manager-chat.md` §3.2, §8 (UX-flagged to PM/Architect) | Not built into any story here — no current FR asks for it; carried forward as a possible post-MVP consistency improvement, consistent with the UX spec's own framing. |
| 4 | Whether the `/dashboard` route needs any access gate, given the auth-minimalism NFR (PRD §7) is silent on Dashboard access | `owner-dashboard.md` §1, §6 | Carried forward — Architect decision, not addressed by any story in Epic 5. |
| 5 | Whether Twilio WhatsApp Sandbox can reliably support interactive/quick-reply messages, or plain-text-only is the confirmed final approach | `whatsapp-deltas.md` §1 decision note, §4 | Addressed procedurally via Story 7.5 (go/no-go spike), not resolved definitively here — the default assumption (plain-text-only) is treated as the safe fallback per the UX spec, with Story 7.5 as the checkpoint to confirm or revise it. |
| 6 | Build-sequencing dependency: demonstrating FR-26's conflict-found path needs at least one existing Booking against the relevant staff member | This agent's own analysis of `staff-owner-manager-chat.md` §3.2 against Epic 2/3 ordering — not sourced from an explicit PRD/UX statement | Flagged as a sequencing risk on Story 3.2; not a functional gap (the conflict-check logic itself has no such dependency), only a rehearsal/demo-data dependency. |
| 7 | Stack/architecture items already routed to the Architect (MCP vs. in-process tools, conversation-state persistence mechanism, conflict-detection mechanism, web-chat frontend tech) | PRD §9.2; addendum.md §4 rows 3, 4, 6–10, 12 | Out of this artefact's scope entirely — not re-litigated, re-asked, or assumed against in any story above; stories are written at the FR/behavior level only, never prescribing implementation mechanism. |
| 8 | Exact Python patch version pin beyond "3.12+" and Node.js runtime version for `B2B_FE/` are not stated anywhere in `base-rules.md` or `stack-proposal.md` (only React 18+/TypeScript 5+/Vite 5+ are pinned on the frontend side) | `stack/rules/base-rules.md` Stack table; `stack-proposal.md` §1 | Carried forward, not invented here — Story 0.1/0.2 scaffold against the stated floor versions only; a specific patch/Node version is a Developer/Architect discretion call at implementation time, not fabricated in this artefact. |
| 9 | Which Python packaging tool manages `B2B_BE/pyproject.toml` (e.g., `poetry`, `uv`, `pdm`, `hatch`, plain `pip` + `pyproject.toml`) and which Node package manager (`npm`, `pnpm`, `yarn`) manages `B2B_FE/package.json` are not specified in `base-rules.md` or `stack-proposal.md` | `stack/rules/base-rules.md` Dependency Policy; `stack-proposal.md` §9 | Carried forward, not invented here — Story 0.1/0.2's acceptance criteria require the manifest files to exist and declare the stated dependencies/versions, without prescribing a specific package-management tool; left to Developer discretion within `base-rules.md`'s "mature, widely-used" guardrail. |

No item above required escalation beyond what the PRD/UX artefacts had already flagged — this pass found
no new contradictory business rule and no core entity/relationship that couldn't be determined from the
available inputs.
