---
title: Agentic Appointment Management Engine — Salon Edition
status: final
created: 2026-09-17
updated: 2026-09-17
---

# PRD: Agentic Appointment Management Engine — Salon Edition
*Working title — confirm.*

## 0. Document Purpose

This PRD translates `bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/brief.md` and its
companion `addendum.md` (both approved at Gate 1) into functional requirements the Architect and UX
Designer agents can build from. It is scoped to a 24-hour hackathon, happy-flow-only demo of a
single-business, two-agent conversational appointment-management engine. Requirements are grouped by
persona (Customer, Ramesh — Owner/Admin, Meena/Arjun — Staff), each FR is globally numbered and
traceable to its brief/addendum source, and every inline `[ASSUMPTION]` is indexed in §10. Three
product-level questions the brief itself left open for the human/stakeholder (Ramesh's role, whether the
demo tracks business KPIs, and which human-verification moment(s) to showcase) were resolved directly by
the user on 2026-09-17; §9 records each decision and every section it touches. This PRD carries no open
PM-owned questions as of this revision. Architecture, technical-implementation, and UX-design decisions
remain explicitly out of this PRD's scope; where the brief/addendum surfaced such an item (stack, MCP vs.
in-process tools, repo-layout nesting, conversation-state persistence, DB choice), it is carried forward
unchanged as noted technical context for the Architect in §9 — still open for Phase 3, not resolved or
re-asked here.

This is a chain-top PRD: it feeds the Architect (system design, epics/stories) and the UX Designer
(interaction design for both chat surfaces and the dashboard) directly. No UX or architecture artifact
exists yet for this pivot.

## 1. Vision

A single salon — Ramesh's 4-chair unisex salon, staffed by Ramesh, Meena, and Arjun — runs its entire
appointment lifecycle through natural-language conversation instead of a slot-picker UI or a phone/paper
register. A customer texts or chats "I need a haircut Thursday afternoon, prefer Rahul" — actually the
salon's own staff, Meena or Arjun — and the **Booking Agent** parses the request, checks live
availability, and either confirms, offers same-day alternatives, or names the nearest open slot. Staff
tell the **Manager Agent** about their own availability changes in the same conversational style; the
owner manages the service/pricing catalog the same way. A read-only dashboard gives the owner a live
window onto staff and bookings. All three surfaces — Booking Agent, Manager Agent, dashboard — read
and write one shared data store, so a change made on one surface is visible on the others immediately;
this shared-state behavior is the demo's core technical proof point (brief.md, Executive Summary).

This is framed as a B2B, plug-into-any-business engine — the salon is the seeded demo vertical, not the
ceiling of the idea (brief.md, Executive Summary) — but this PRD scopes only the hackathon MVP: the
happy-flow, single-salon demo. Multi-tenancy, defensive handling of ambiguous or non-happy-path input,
and the deferred capabilities in brief.md's Vision (Post-MVP) are explicitly not covered here (see §5, §6.2).

## 2. Target User

### 2.1 Jobs To Be Done

- **Customer** — "Let me get an appointment booked, changed, or cancelled by just saying what I want, on whatever channel I'm already using, without hunting through a slot grid." (brief.md, Who This Serves; Scope — Hackathon MVP)
- **Ramesh (Owner/Admin)** — "Let me update what services I offer and what they cost by just telling the system, and let me see at a glance who's working and what's booked, without touching a spreadsheet or calling my staff." (brief.md, Who This Serves; addendum.md §1)
- **Meena / Arjun (Staff)** — "Let me tell the system when I'm not available, in my own words, and trust that it won't double-book me and that customers see the change right away." (brief.md, Who This Serves; addendum.md §1)

### 2.2 Non-Users (v1)

- Other salons or businesses (multi-tenant use) — this is a single seeded business for the demo, not a multi-business platform yet (brief.md, Document Note — Full Pivot; Constraints).
- Customers wanting multi-person/family bookings or multi-service combination bookings in one visit — deferred (brief.md, [HACKATHON SCOPE]; Out of scope for this demo).
- Anyone needing password/OTP-grade authentication, payments, or account self-service beyond phone-number lookup — not built for this demo (brief.md, Scope — Hackathon MVP; Out of scope for this demo).
- Ramesh acting as a bookable service provider or managing his own availability — **confirmed as a non-user for v1.** Ramesh is admin-only: he does not take appointments himself and does not manage his own availability. Confirmed directly by the user on 2026-09-17 as a locked product decision, not an assumption (see §9, Decision 1); see §4.1 FR-13 and §4.2 FR-19/FR-21.

### 2.3 Key User Journeys

*Numbered globally UJ-1 through UJ-6. FRs reference these by ID.*

- **UJ-1. A new customer books a haircut via web chat, exact time available.**
  - **Persona + context:** A first-time customer, chatting on the salon's website widget, wants a Thursday-afternoon haircut.
  - **Entry state:** Not authenticated; no phone number on file yet; web chat surface.
  - **Path:** Opens chat → agent asks for phone number → number not found → agent also asks for name → agent creates the customer record → customer states "haircut, Thursday 3pm, no preference" → agent checks availability → the exact slot is open → agent confirms the slot and asks the customer to confirm → customer confirms.
  - **Climax:** The agent confirms the booking is created, naming the service, date/time, and assigned staff member.
  - **Resolution:** Customer knows they have a confirmed appointment; can ask to see it again via booking history at any later point.
  - **Edge case:** Not modeled — non-happy-path handling (e.g., ambiguous service name) is explicitly out of scope for this demo (brief.md, [HACKATHON SCOPE]).

- **UJ-2. A returning customer books via WhatsApp with a staff preference; exact time unavailable.**
  - **Persona + context:** A returning customer, already known by phone number, messages the salon's WhatsApp number asking for a color appointment with Meena at 11am Saturday.
  - **Entry state:** Phone number already known from the WhatsApp channel; customer record exists.
  - **Path:** Customer messages intent → agent looks up the number, finds a match, greets by name (no name question asked) → agent checks Meena's 11am Saturday slot → unavailable → agent proposes the nearest alternative(s) with brief reasoning (e.g., "Meena's 11am is booked; she's free at 1pm or 2:30pm Saturday") → customer picks 1pm → agent confirms.
  - **Climax:** Booking created at the alternative time, with the customer's staff preference honored.
  - **Resolution:** Customer has a confirmed appointment; can cancel or reschedule it later via the same channel.

- **UJ-3. A customer reschedules an existing booking.**
  - **Persona + context:** A customer with an upcoming booking wants to move it to a different day.
  - **Entry state:** Authenticated by phone-number match; at least one upcoming booking exists.
  - **Path:** Customer states the reschedule intent → agent identifies the existing booking (from booking history) → agent cancels the old slot → agent re-runs the normal booking flow (as in UJ-1/UJ-2) for the new time → customer confirms the new slot.
  - **Climax:** Old slot is freed, new slot is confirmed, in the same conversation.
  - **Resolution:** Customer sees one active booking at the new time; the old slot is immediately available for someone else to book.

- **UJ-4. Meena blocks out an availability window; the change is immediately visible to the next customer.**
  - **Persona + context:** Meena is out Friday morning and needs to signal that before customers can book her.
  - **Entry state:** Meena, authenticated via pre-seeded phone-number lookup, messaging the Manager Agent (either channel).
  - **Path:** Meena states "block out Friday morning, I'm out" → agent checks the change against Meena's existing bookings for that window → no conflict → agent confirms the block and applies it.
  - **Climax:** The block is applied to the shared data store.
  - **Resolution:** A customer who asks the Booking Agent for a Friday-morning slot with Meena immediately sees her as unavailable for that window — no separate sync step, no delay (brief.md, Executive Summary; Demo Success Criteria item 2).

- **UJ-5. Ramesh adds a new service and price via natural language.**
  - **Persona + context:** Ramesh wants to start offering a new service (e.g., "beard trim, ₹150") without editing a spreadsheet.
  - **Entry state:** Ramesh, authenticated via pre-seeded phone-number lookup, messaging the Manager Agent.
  - **Path:** Ramesh states the new service and price → agent confirms the details back to him → Ramesh confirms → agent applies it to the live catalog.
  - **Climax:** The service is now part of the catalog the Booking Agent can offer.
  - **Resolution:** A customer asking the Booking Agent to "browse services" immediately sees the new service and price.

- **UJ-6. Ramesh checks today's bookings on the dashboard and watches it update live.**
  - **Persona + context:** Ramesh wants a quick visual check of who's working and what's booked today.
  - **Entry state:** Ramesh, viewing the read-only dashboard (no conversational interaction here).
  - **Path:** Ramesh opens the dashboard → sees the staff list and today's bookings per staff member → a customer books a new slot via the Booking Agent in parallel → the dashboard reflects the new booking without Ramesh refreshing or re-navigating.
  - **Climax:** The booking Ramesh sees appear was never entered by Ramesh himself — proof the three surfaces share one live data store.
  - **Resolution:** Ramesh has an accurate, current picture of the day; no action is taken from the dashboard itself (brief.md, Scope — Hackathon MVP: "Dashboard ... No editing from the dashboard.").

## 3. Glossary

- **Salon** — The single seeded business this demo models: Ramesh's 4-chair unisex salon. One salon only for this demo; multi-salon is out of scope (brief.md, Constraints).
- **Customer** — A person who books, views, reschedules, or cancels an appointment via the Booking Agent. Identified by phone number.
- **Owner/Admin** — Ramesh. Manages the service/pricing catalog and views the staff list and bookings via the dashboard. Distinct from Staff (see Role).
- **Staff** — Meena and Arjun. Provide services and manage their own Availability via the Manager Agent. Distinct from Owner/Admin.
- **Role** — One of `Customer`, `Owner/Admin`, or `Staff`. Determines which actions a person may take through the Manager Agent, per the permission matrix in addendum.md §1.
- **Booking Agent** — The customer-facing conversational agent, reachable via Web Chat or WhatsApp, that parses booking intent and manages Bookings.
- **Manager Agent** — The staff/owner-facing conversational agent, reachable via Web Chat or WhatsApp, that parses Availability changes (Staff) and catalog changes (Owner/Admin).
- **Dashboard** — The read-only, non-conversational web view for the Owner/Admin showing the Staff list and current Bookings.
- **Channel** — The surface a person uses to reach an agent: Web Chat or WhatsApp. Both front the same agent core (brief.md, What Makes This Different).
- **Service** — A named, priced offering in the catalog (e.g., "haircut," "color"), managed by the Owner/Admin.
- **Booking** — A confirmed appointment: one Customer, one Service, one Staff member, one date/time.
- **Availability** — A Staff member's open or blocked time. A **block** marks time as unavailable to Customers; an **unblock** reopens it.
- **Slot** — A specific date/time window a Customer could book, bounded by a Staff member's Availability and existing Bookings.
- **Conflict** — A proposed Availability change or Booking that collides with an existing Booking or block for the same Staff member and time.
- **Shared Data Store** — The single store of Services, Staff/Owner records, Bookings, and Availability that the Booking Agent, Manager Agent, and Dashboard all read from and (agents) write to. A change on one surface is immediately visible on the others.
- **Happy Flow** — The scoped path this demo supports: clear, unambiguous customer/staff/owner intent with at least one satisfiable outcome. Ambiguous intent, zero availability, and other non-happy-path cases are known limitations, not handled (brief.md, [HACKATHON SCOPE]).

## 4. Features

### 4.1 Customer — Booking Agent (Web Chat + WhatsApp)

**Description:** The Customer-facing feature set. A Customer identifies themselves by phone number,
then can browse the catalog, book, view booking history, cancel, or reschedule — all in natural
language, on either Channel, against the same agent core. Realizes UJ-1, UJ-2, UJ-3. Source: brief.md
"Scope — Hackathon MVP," "Who This Serves"; addendum.md §1 (Customer), §2.2 (agent-to-tool pattern).

**Functional Requirements:**

#### FR-1: Phone-number identity resolution (Web Chat)
On Web Chat, the Booking Agent can ask a Customer for their phone number and look it up against
existing Customer records before proceeding with any booking action. Realizes UJ-1.

**Consequences (testable):**
- The agent asks for a phone number before any booking, browse-history, cancel, or reschedule action is completed on Web Chat.
- A number that matches an existing record results in the agent greeting the Customer by name and proceeding directly to the stated intent (no name question asked).
- A number with no match results in FR-2 firing before any booking action proceeds.

#### FR-2: New-customer record creation
When a phone number has no match, the Booking Agent can ask for the Customer's name and create a new
Customer record before proceeding. Realizes UJ-1.

**Consequences (testable):**
- A new Customer record (phone number + name) exists after this exchange, retrievable on a subsequent conversation with the same phone number.
- The Customer is not asked for their phone number again in the same conversation once resolved.

#### FR-3: WhatsApp identity resolution (channel-aware)
On WhatsApp, the Booking Agent can resolve Customer identity from the channel-supplied phone number
without asking the Customer for it; if no record matches, the agent still asks only for the name (not
the number). Realizes UJ-2.

**Consequences (testable):**
- No phone-number question is ever asked on the WhatsApp channel.
- A WhatsApp message from a known number results in a name-based greeting with no further identity questions.
- A WhatsApp message from an unknown number results in exactly one question (name) before proceeding.

#### FR-4: Browse services & pricing
A Customer can ask to see the current services and prices at any point in the conversation, whether or
not they are mid-booking.

**Consequences (testable):**
- The agent returns the current catalog (service names + prices) reflecting the latest state of the Shared Data Store, including any change the Owner/Admin applied via FR-14/FR-15/FR-16 before this request.

#### FR-5: State a booking intent in natural language
A Customer can state a booking intent consisting of a Service and, optionally, a date/time and/or a
named Staff preference, in free text (e.g., "I need a haircut Thursday afternoon, prefer Meena").
Realizes UJ-1, UJ-2.

**Consequences (testable):**
- A Service is required for the agent to proceed; date/time and staff preference are each optional and independently omittable.
- The agent correctly extracts Service, and where stated, date/time and staff preference, for at least the demo's rehearsed happy-path phrasings.

#### FR-6: Exact-time resolution — direct confirmation
When the Customer's stated intent names an exact, available date and time (and Staff member, if named),
the Booking Agent confirms that slot directly. Realizes UJ-1.

**Consequences (testable):**
- The agent's response names the Service, date/time, and assigned Staff member, and asks for explicit confirmation before creating the Booking.

#### FR-7: Day-only resolution — list that day's available slots
When the Customer names a day but no specific time, the Booking Agent lists that day's available slots,
either salon-wide or filtered to a named Staff member if one was stated. Realizes UJ-1.

**Consequences (testable):**
- The listed slots reflect only currently open Availability for the relevant Staff member(s) at the time of the request (excludes blocked time and already-booked Slots).
- If a Staff preference was stated, only that Staff member's open slots are listed.

#### FR-8: Exact-time-unavailable resolution — nearest alternative(s)
When the Customer's exact requested time is unavailable, the Booking Agent suggests the nearest
alternative(s) with brief reasoning for why the original time doesn't work. Realizes UJ-2.

**Consequences (testable):**
- The agent names at least one alternative slot when one exists within the same Staff-preference constraint (or salon-wide if none was stated).
- The agent's response states the reason the original time is unavailable (e.g., already booked, blocked).

#### FR-9: Booking confirmation and creation
A Booking is created only after the Customer explicitly confirms a proposed slot in the same
conversation. Realizes UJ-1, UJ-2.

**Consequences (testable):**
- No Booking record exists in the Shared Data Store until an explicit customer confirmation message follows a proposed slot.
- Once confirmed, the Booking is immediately queryable (FR-10) and immediately visible on the Dashboard (FR-19) and to any subsequent availability check by any Customer or Staff member.

#### FR-10: View booking history
A Customer can ask to see their upcoming and/or past bookings on request.

**Consequences (testable):**
- The response distinguishes upcoming Bookings from past ones.
- Only the requesting Customer's own Bookings are returned (never another Customer's).

#### FR-11: Cancel a booking
A Customer can cancel an existing upcoming Booking on request.

**Consequences (testable):**
- The cancelled Booking no longer appears as an active upcoming Booking in FR-10 results.
- The freed slot is immediately available to be offered to another Customer (FR-7/FR-8) with no further action needed.

#### FR-12: Reschedule as cancel + rebook
A Customer can reschedule an existing Booking; the system treats this as cancelling the existing slot
and re-running the normal booking flow (FR-5 through FR-9) for the new time. Realizes UJ-3.

**Consequences (testable):**
- The original Slot is freed (per FR-11's consequences) before or atomically with the new Booking being proposed.
- The Customer ends the conversation with exactly one active Booking reflecting the new time (not two).

#### FR-13: Staff selectable as a booking preference — Customer-side
A Customer's optional staff preference (FR-5) can name any Staff member who is bookable by Customers.
**Confirmed decision (2026-09-17): only Meena and Arjun are selectable; Ramesh is not offered or
accepted as a staff preference**, because he is admin-only and does not take appointments
(brief.md, Who This Serves; addendum.md §1, §4 row 1; confirmed directly by the user — see §9,
Decision 1).

**Consequences (testable):**
- A stated preference for "Ramesh" as a service provider is not fulfillable through this flow; this
  outcome is not modeled in this happy-flow-only demo (a known limitation, not a defect).

**Out of Scope:**
- Multi-service, multi-person/family booking, and cross-provider optimization (brief.md, [HACKATHON SCOPE]).

### 4.2 Ramesh — Owner/Admin (Manager Agent + Dashboard)

**Description:** The Owner/Admin-facing feature set. Ramesh identifies himself by pre-seeded
phone-number lookup, then manages the service/pricing catalog conversationally via the Manager Agent,
and separately views the Staff list and Bookings via the read-only Dashboard. Realizes UJ-5, UJ-6.
Source: brief.md "Scope — Hackathon MVP"; addendum.md §1 (Ramesh), role matrix (addendum.md §1).

**Functional Requirements:**

#### FR-14: Pre-seeded identity resolution (Owner/Admin)
On Web Chat, the Manager Agent can ask Ramesh for his phone number and match it against the pre-seeded
Owner/Admin record; on WhatsApp, the number is already known and no question is asked. A match
determines the Manager Agent treats the requester as Owner/Admin for permission purposes (FR-21, FR-22).

**Consequences (testable):**
- A Web Chat session with a matching pre-seeded number results in the Manager Agent granting Owner/Admin-permitted actions (FR-15–FR-17, FR-19) without a signup step.
- A non-matching number is out of scope for this demo (no fallback flow defined).

#### FR-15: Add a service via natural language
Ramesh can state a new Service name and price in natural language; the Manager Agent confirms the
details and, on confirmation, applies it to the live catalog. Realizes UJ-5.

**Consequences (testable):**
- The new Service does not exist in the Shared Data Store until Ramesh has explicitly confirmed the agent's restated details.
- Once confirmed, the new Service is immediately returned by FR-4 (Customer catalog browse) with no separate publish step.

#### FR-16: Edit a service or price via natural language
Ramesh can state a change to an existing Service's name and/or price in natural language; the Manager
Agent confirms and applies the change to the live catalog.

**Consequences (testable):**
- The prior price/name is no longer returned by FR-4 once the change is confirmed and applied.
- The updated Service is immediately reflected in any Customer-side quote or catalog browse afterward.

#### FR-17: Delete a service via natural language
Ramesh can state that a Service should be removed; the Manager Agent confirms and applies the removal.

**Consequences (testable):**
- The removed Service is no longer offered or returned by FR-4 after confirmation.
- Existing Bookings already made against that Service before removal are not modeled as needing retroactive handling in this happy-flow-only demo (not addressed — known limitation).

#### FR-18: Confirmation required before catalog changes apply
No catalog change (FR-15, FR-16, FR-17) is applied to the Shared Data Store until Ramesh has explicitly
confirmed the Manager Agent's restated version of the change in the same conversation.

**Consequences (testable):**
- The catalog is unchanged if the conversation ends before an explicit confirmation message.

#### FR-19: View staff list via dashboard (read-only)
Ramesh can view the current Staff list (Meena, Arjun) on the Dashboard. **Confirmed decision
(2026-09-17):** Ramesh himself is not listed as a Staff member — he is admin-only (see §9, Decision 1).
Realizes UJ-6.

**Consequences (testable):**
- The Staff list shown is not editable from the Dashboard — no add/remove/edit control exists on this surface (brief.md, "Out of scope for this demo": "Owner/Admin adding/removing/editing staff accounts (view-only)").
- The Staff list shown contains exactly Meena and Arjun — not Ramesh.

#### FR-20: View bookings via dashboard (read-only)
Ramesh can view current Bookings (today's or the week's) per Staff member on the Dashboard. Realizes UJ-6.

**Consequences (testable):**
- A Booking created via the Booking Agent (FR-9) after the Dashboard was last loaded is visible on the Dashboard without Ramesh performing any catalog or availability action himself (proof of Shared Data Store — see FR-30).
- No booking, cancellation, or edit action is available from the Dashboard itself.

#### FR-21: Owner/Admin cannot manage own availability
**Confirmed decision (2026-09-17):** Ramesh cannot block/unblock his own Availability through the
Manager Agent, because he is admin-only and is not a bookable Staff member (addendum.md §1 role matrix:
"Block/unblock own availability — Owner/Admin: No"; confirmed directly by the user — see §9, Decision 1).

**Consequences (testable):**
- A request from Ramesh's identified session to block or unblock availability is not a permitted action under the role matrix.

#### FR-22: Owner/Admin cannot manage staff accounts
Ramesh cannot add, remove, or edit Staff accounts through any surface in this demo — the Staff list is
view-only (addendum.md §1 role matrix; brief.md "Out of scope for this demo").

**Consequences (testable):**
- No conversational or Dashboard action exists that creates, deletes, or edits a Staff record.

#### FR-23: Owner/Admin cannot override staff schedules
Ramesh cannot alter Meena's or Arjun's Availability directly (addendum.md §1 role matrix: "Override
another staff member's schedule — Owner/Admin: No").

**Consequences (testable):**
- A request from Ramesh's identified session to change Meena's or Arjun's Availability is rejected or not offered as an available action.

### 4.3 Meena & Arjun — Staff (Manager Agent)

**Description:** The Staff-facing feature set. Meena and Arjun each identify themselves via pre-seeded
phone-number lookup and manage only their own Availability (block/unblock) via the Manager Agent, in
natural language, with the change checked against existing Bookings before being applied. Realizes
UJ-4. Source: brief.md "Scope — Hackathon MVP"; addendum.md §1 (Meena, Arjun), role matrix.

**Functional Requirements:**

#### FR-24: Pre-seeded identity resolution (Staff)
On Web Chat, the Manager Agent can ask a Staff member for their phone number and match it against the
pre-seeded Staff records; on WhatsApp, the number is already known. A match determines the Manager
Agent treats the requester as that specific Staff member (Meena or Arjun) for permission purposes.

**Consequences (testable):**
- The Manager Agent's response to an availability-change request always reflects which specific Staff member is understood to be speaking (never ambiguous between Meena and Arjun).

#### FR-25: State an availability change in natural language
A Staff member can state a block or unblock of their own Availability in natural language (e.g., "block
out Friday morning, I'm out" / "unblock Saturday"). Realizes UJ-4.

**Consequences (testable):**
- The agent correctly extracts which Staff member, which window (date/time range), and whether it is a block or an unblock, for at least the demo's rehearsed happy-path phrasings.

#### FR-26: Conflict check before applying an availability change
Before applying a block, the Manager Agent checks the proposed window against that Staff member's
existing Bookings. Realizes UJ-4. (addendum.md §2.4 item 6, carried forward here as a product-level
behavior, not a mechanism: the Architect/Developer own *how* this check is implemented.)

**Consequences (testable):**
- If the proposed block window contains an existing Booking, the agent's response names which
  Booking(s) cause the conflict (e.g., "Friday 10am is already booked with a customer for a haircut") —
  it is not a silent rejection.
- If no conflict exists, the block is confirmed and applied (FR-27).

#### FR-27: Confirmation required before an availability change applies
No block or unblock is applied to the Shared Data Store until the Staff member has explicitly confirmed
the Manager Agent's restated version of the change in the same conversation.

**Consequences (testable):**
- The Availability record is unchanged if the conversation ends before an explicit confirmation.
- Once confirmed and applied, the change is immediately reflected in the Booking Agent's next
  availability check for that Staff member (FR-7, FR-8) and in FR-20's Dashboard view — no separate
  sync step, no delay (brief.md, Demo Success Criteria item 2).

#### FR-28: Staff cannot manage the catalog
Neither Meena nor Arjun can add, edit, or delete Services or prices through the Manager Agent
(addendum.md §1 role matrix: "Add/edit/delete services & pricing — Staff: No").

**Consequences (testable):**
- A catalog-change request from a Staff-identified session is not a permitted action.

#### FR-29: Staff cannot view the staff list or dashboard
Neither Meena nor Arjun has access to the Staff list or the Dashboard (addendum.md §1 role matrix:
"View staff list / View bookings (dashboard) — Staff: No").

**Consequences (testable):**
- No conversational response to a Staff-identified session returns another Staff member's schedule, the full Staff list, or Dashboard-equivalent data.

#### FR-30: Staff cannot override another staff member's schedule
Neither Meena nor Arjun can block, unblock, or otherwise alter the other's Availability
(addendum.md §1 role matrix: "Override another staff member's schedule — Staff: No").

**Consequences (testable):**
- A request from Meena's identified session naming Arjun's schedule (or vice versa) is not a permitted action.

### 4.4 Cross-Cutting: Shared State & Live Reflection

**Description:** The property that makes the demo's core proof point work: the Booking Agent, Manager
Agent, and Dashboard all read from and write to one Shared Data Store, so a change from any one surface
is visible on the others without a manual refresh, restart, or separate sync action. This spans FR-9,
FR-11, FR-15–FR-17, FR-19, FR-20, FR-27. Source: brief.md, Executive Summary; Demo Success Criteria
items 2 and 4.

**Functional Requirements:**

#### FR-31: Availability and catalog changes are immediately visible to the Booking Agent
Any Staff availability change (FR-27) or Owner/Admin catalog change (FR-18) that has been confirmed and
applied is available to the Booking Agent's very next relevant query — not after a delay, cache
refresh, or restart.

**Consequences (testable):**
- A Customer conversation started immediately after a Staff member confirms a block never offers that
  blocked window as available.
- A Customer conversation started immediately after Ramesh confirms a price change or new Service
  reflects the new price/Service on the very next catalog browse or booking attempt.

#### FR-32: Dashboard reflects the shared store live
The Dashboard's Staff list and Bookings view (FR-19, FR-20) reflect Bookings and Availability changes
made through either agent, without Ramesh taking any action to trigger the update.

**Consequences (testable):**
- A Booking created via the Booking Agent, or an Availability change confirmed via the Manager Agent,
  appears on the Dashboard within the same demo session without a manual data re-entry step by Ramesh.

## 5. Non-Goals

- This is not a multi-salon or multi-business discovery/comparison platform for this demo — one seeded
  salon only (brief.md, Constraints; Out of scope for this demo).
- This is not a payments or point-of-sale system — no payment handling exists in this demo (brief.md,
  Out of scope for this demo).
- This is not a ratings-and-reviews or offers/discounts product for this demo (brief.md, Out of scope
  for this demo).
- This is not a general-purpose staff-account-management system — Owner/Admin cannot add, remove, or
  edit Staff accounts; the Staff list is view-only (brief.md, Out of scope for this demo).
- This is not a system that defends against ambiguous, malformed, or adversarial natural-language input
  — non-happy-path handling is explicitly deferred; it is a known limitation, not a build target for this
  demo (brief.md, [HACKATHON SCOPE]).
- This is not (yet) a domain-agnostic, config-driven engine for arbitrary appointment-based businesses —
  that is Vision (Post-MVP), not this PRD's scope (brief.md, Vision — Post-MVP).

## 6. MVP Scope

### 6.1 In Scope

- Customer identity via phone-number lookup only, on both Web Chat and WhatsApp (§4.1).
- Full Customer booking lifecycle in natural language: browse, book, view history, cancel, reschedule (§4.1).
- Three booking-resolution paths: exact-time-available, day-only (list slots), exact-time-unavailable (nearest alternative) (§4.1, FR-6–FR-8).
- Staff availability management (block/unblock) via natural language, with conflict checking against existing Bookings (§4.3).
- Owner/Admin catalog management (add/edit/delete services & pricing) via natural language (§4.2).
- Read-only Dashboard: Staff list, current Bookings (today's/week's) per Staff member (§4.2, FR-19–FR-20).
- Shared, live state across all three surfaces (§4.4).
- Role-based permission enforcement per the addendum.md §1 matrix (§4.2, §4.3).

### 6.2 Out of Scope for MVP

*(Carried forward verbatim in substance from brief.md, "Out of scope for this demo" — a fixed boundary for the Architect and UX Designer, not re-derived here.)*

- Multi-salon discovery/comparison.
- Multi-person/family booking optimization — deferred to post-MVP vision, not dropped.
- Multi-service combination booking in one visit.
- Ratings & reviews.
- Offers & discounts.
- Payments/POS.
- Owner/Admin managing their own availability or acting as a bookable provider — **confirmed out of
  scope.** Resolved directly by the user on 2026-09-17 as a locked decision, not an assumption (see §9,
  Decision 1); see also §4.1 FR-13, §4.2 FR-19/FR-21.
- Owner/Admin adding/removing/editing staff accounts (view-only).
- Staff overriding another staff member's schedule.
- Defensive handling of non-happy-path input (ambiguous intent, zero availability, malformed requests).

## 7. Cross-Cutting NFRs

- **Build window:** 24-hour hackathon build; happy-flow-only bar applies to every FR in this document — no FR above should be read as requiring defensive/edge-case handling beyond what's stated (brief.md, Constraints).
- **Identity/auth minimalism:** No password, OTP, or session-token authentication anywhere in this
  demo — phone-number lookup is the entire identity mechanism for both Customers (FR-1–FR-3) and
  Staff/Owner (FR-14, FR-24) (brief.md, Scope — Hackathon MVP). Stronger authentication is explicitly
  Vision (Post-MVP), not this demo (brief.md, Vision — Post-MVP).
- **Persistence:** No production-grade persistence or scaling guarantee is required for this demo;
  minimal or in-memory storage is acceptable if it speeds the build, so long as it upholds the
  Shared-State requirements in §4.4 for the duration of a demo session (addendum.md §2.1). This is a
  starting point for the Architect, not a PM-level technical decision.
- **Channel parity:** Booking Agent and Manager Agent behavior must be identical in substance across
  Web Chat and WhatsApp — only the identity-question mechanics differ (FR-1 vs. FR-3; FR-14/FR-24 note
  the same for staff/owner) (addendum.md §2.3). The *how* (webhook parsing, TwiML vs. WebSocket) is
  Architect-owned and out of this PRD's scope.

## 8. Success Metrics

Framed against the hackathon's stated evaluation weighting: Agentic SDLC 40 / Human Verification 40 /
Output Credibility 20 (brief.md, Goals & Success Metrics).

**Primary**
- **SM-1:** A judge observes a live, unscripted-in-the-moment Customer conversation completing browse
  → book → view history → cancel → reschedule, on both Web Chat and WhatsApp, without a mockup or
  slide standing in for any step. Validates FR-1–FR-13.
- **SM-2:** A judge observes a Staff availability change (block or unblock) immediately change what the
  Booking Agent offers next, with no restart or manual sync step visible. Validates FR-25–FR-27, FR-31.
- **SM-3:** A judge observes Ramesh add, edit, or delete a service/price via natural language, and see
  the Dashboard reflect the current Staff list and Bookings. Validates FR-15–FR-20, FR-32.

**Secondary**
- **SM-4:** **Confirmed decision (2026-09-17):** the build showcases **three** distinct
  human-verification checkpoints, one per agent-decision type — not a single moment. The brief's own
  flagged open question (brief.md, Goals & Success Metrics; addendum.md §4 row 11) is resolved with all
  three of the candidate options, per the user's direct decision (see §9, Decision 3):
  - **SM-4a — Booking-intent checkpoint:** A human reviews, and corrects where needed, the Booking
    Agent's parsed booking intent (Service, date/time, Staff preference — FR-5) before it is acted on
    (i.e., before FR-6/FR-7/FR-8 proceed on it).
  - **SM-4b — Alternative-slot checkpoint:** A human reviews the Booking Agent's reasoning when it
    suggests an alternative time slot (FR-8), before that alternative is offered to the Customer.
  - **SM-4c — Conflict-detection checkpoint:** A human reviews the Manager Agent's conflict-detection
    outcome (FR-26) before an Availability change (FR-27) or Booking (FR-9) is finalized.

  Each checkpoint validates the Human-Verification-40 evaluation weighting against a specific FR. The
  *mechanism* by which each checkpoint is surfaced during the build (e.g., a review step in the agent's
  tool-use loop, a logged approval gate) is Architect/Developer-owned and not specified here.

**Counter-metrics (do not optimize)**
- **SM-C1:** Time spent hardening non-happy-path input handling — explicitly a non-goal for this demo
  (§5); optimizing here trades demo-day risk on the happy path for coverage that will not be evaluated
  in the stated weighting. Counterbalances SM-1–SM-3.

**Note on business KPIs — confirmed decision (2026-09-17):** No traditional business KPIs (retention,
conversion, wait-time reduction, a bookings-created counter, cancellation rate, or similar) are tracked
for this demo (brief.md, Goals & Success Metrics; addendum.md §4 row 2 — resolved directly by the user;
see §9, Decision 2). SM-1 through SM-3 above are final as written; no business-KPI companion metric is
defined or required.

## 9. Open Questions

### 9.1 Resolved Decisions (2026-09-17)

The following three items were the brief's own flagged open questions requiring a human/stakeholder
decision (addendum.md §4, rows 1, 2, 11). The user resolved all three directly on 2026-09-17. Each is now
a **locked product decision**, not an assumption — every section previously drafted against the brief's
default reading is confirmed unchanged in substance; only the status label changes from
"[PENDING USER DECISION]" to "confirmed."

- **Decision 1 — Ramesh's role:** Ramesh is admin-only. He does not take appointments himself and does
  not manage his own Availability. This confirms the brief's own default reading (brief.md, Who This
  Serves; addendum.md §1 "Ramesh," §4 row 1) as final — no FR text changes in substance as a result, only
  the removal of pending-decision markers. Affects: §2.2 (Non-Users), §4.1 FR-13, §4.2 FR-19 and FR-21, §6.2.
- **Decision 2 — Demo KPIs:** No business-style metrics (bookings-created counter, cancellation rate,
  retention, conversion, wait-time reduction, or similar) are tracked for this demo. This confirms the
  brief's own working assumption (brief.md, Goals & Success Metrics; addendum.md §4 row 2) as final.
  Affects: §8 ("Note on business KPIs").
- **Decision 3 — Human-verification moment(s):** The build showcases **all three** of the candidate
  checkpoints, not one: (a) a human reviewing/correcting the Booking Agent's parsed booking intent
  before it's acted on; (b) a human reviewing the Booking Agent's reasoning when it suggests an
  alternative time slot, before it's offered to the customer; (c) a human reviewing the Manager Agent's
  conflict-detection outcome before an Availability change or Booking is finalized. This resolves the
  brief's own flagged open question (brief.md, Goals & Success Metrics; addendum.md §4 row 11) with a
  broader answer than any single option — the user selected all three. Affects: §8 SM-4 (now SM-4a/b/c).

No PM-owned open questions remain in this PRD as of this revision.

### 9.2 Items carried forward for the Architect phase — not PM-decidable, not re-asked here

These are technical/architecture items already correctly routed to the Architect in addendum.md §4 (rows
3, 4, 6, 7, 8, 9, 10, 12); listed here only so the Architect's starting context is visible alongside the
PRD, per this PRD's Purpose (§0) and per this agent's scope boundary against making architecture
decisions. **Unchanged by this revision — none of these were touched by the three resolved decisions
above.**

- Whether the §8-equivalent technical considerations in addendum.md §2.1 (interface, agents, intent
  parsing, conflict detection, data model) are adopted as-is or refined (addendum.md §4 row 3).
- Stack direction — Flutter + FastAPI (Python) + Postgres is a stated leaning, not a locked decision;
  formal Architect-phase evaluation and Gate 3 user approval still owed (addendum.md §4 row 4).
- MCP tool-layer vs. direct in-process function registration for the agent-to-tool boundary (addendum.md §4 row 6).
- Nesting the sketched backend package layout under this repository's authoritative `B2B_BE/`
  (backend) / `B2B_FE/` (frontend) split per `CLAUDE.md` (addendum.md §4 row 7).
- Conversation-state persistence approach — client resends full history each turn vs. backend-persisted
  session state (addendum.md §4 row 8).
- Postgres as the Architect's starting point for the database — a stated starting point, not yet
  formally confirmed (addendum.md §4 row 9).
- The *mechanism* by which conflict detection (FR-26) is implemented as an explicit, explainable
  pre-write check rather than a bare DB constraint — the *behavior* is specified in FR-26; the
  *mechanism* is Architect/Developer-owned (addendum.md §4 row 10).
- "Web chat" frontend technology — whether it is a Flutter-web build of the same chat frontend, a
  separate web technology from the Dashboard, or the same technology as the Dashboard (addendum.md §4
  row 12).

## 10. Assumptions Index

- **§2.2, Non-Users (v1):** Ramesh treated as non-bookable/admin-only — RESOLVED as a confirmed decision, not an open assumption (see §9.1, Decision 1).
- **§4.1 FR-13:** Staff preference selection limited to Meena and Arjun, excluding Ramesh — RESOLVED as a confirmed decision (see §9.1, Decision 1).
- **§4.2 FR-19:** Ramesh is not listed as a Staff member on the Dashboard — RESOLVED as a confirmed decision (see §9.1, Decision 1).
- **§4.2 FR-21:** Ramesh cannot manage his own availability — RESOLVED as a confirmed decision (see §9.1, Decision 1).
- **§6.2:** "Owner/Admin managing their own availability or acting as a bookable provider" listed as out of scope — RESOLVED as a confirmed decision (see §9.1, Decision 1).
- **§8, "Note on business KPIs":** No business KPIs tracked for this demo — RESOLVED as a confirmed decision (see §9.1, Decision 2).
- **§8, SM-4a/b/c:** All three candidate human-verification checkpoints are showcased, not a single one — RESOLVED as a confirmed decision (see §9.1, Decision 3).
- **§7, Persistence:** Minimal/in-memory persistence acceptable for the demo session — carried forward from addendum.md §2.1 as an Architect-phase starting point, not a PM-level decision requiring human sign-off. Unchanged by this revision.
- **§9.2 (Architect-carried items):** Stack direction, MCP vs. in-process tools, repo-layout nesting, conversation-state persistence, Postgres confirmation, conflict-detection mechanism, and web-chat frontend technology are all inherited as open architecture items per addendum.md §4 rows 3, 4, 6, 7, 8, 9, 10, 12 — none resolved or guessed at in this PRD, unchanged by this revision.
