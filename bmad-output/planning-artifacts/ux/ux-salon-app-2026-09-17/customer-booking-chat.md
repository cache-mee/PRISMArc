---
title: UX Specification — Web Chat, Customer (Booking Agent)
status: draft
created: 2026-09-17
updated: 2026-09-17
surface: Web Chat — Customer
realizes: UJ-1, UJ-2, UJ-3
covers_fr: FR-1 through FR-13
sources:
  - bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md
  - bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/brief.md
  - bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/addendum.md
  - stack/rules/base-rules.md
---

# Web Chat — Customer (Booking Agent)

This is a conversational surface, not a screen-picker. The spec below is organized as message-turn
structure (what the agent says, what the customer says, what UI affordance appears at each turn) rather
than a wireframe grid, per PRD §0/§2.3's framing of this product as conversational-first.

## 1. Entry Point

The Web Chat widget is a persistent chat launcher (bottom-right corner, standard low-friction convention
for embedded chat widgets) on the salon's public-facing web page, built in `B2B_FE/src/chat/` per
`stack/rules/base-rules.md`. Clicking the launcher opens the chat panel; the Booking Agent sends the
first message (see §3.1). No login screen, no landing page — the chat *is* the product surface for the
Customer.

**Decision — embedded launcher vs. dedicated page.** What: customer chat opens as an overlay panel
triggered by a floating launcher, not a dedicated full-page route. Why: this is the public,
lowest-commitment surface (any site visitor, not-yet-identified) — an overlay matches how a first-time
visitor actually arrives (browsing the site, then deciding to chat), and keeps the rest of the salon's
page visible/available. Alternative considered: a dedicated full-page chat route, same as the internal
Manager Agent surface (see `staff-owner-manager-chat.md`) — rejected here because the Manager Agent's
audience (staff/owner) deliberately navigates to a work tool, while the Customer's entry is casual and
should not require leaving the page they're on.

## 2. Screen/Component Inventory

| Component | Purpose | States |
|---|---|---|
| Chat launcher | Opens/closes the chat panel | collapsed, open, (badge/none — no unread-count feature is in scope) |
| Chat panel header | Salon identity, close control | default |
| Message list | Scrollable turn history | populated, empty (first open, before any agent message renders) |
| Message bubble | One agent or customer turn | sending (customer's own outgoing message, brief), sent |
| Typing indicator | Signals the agent is composing a reply | hidden, visible |
| Composer (text input + send) | Free-text input for any turn | enabled, disabled (while the agent is composing a reply, to keep turns ordered) |
| Catalog list card | Structured rendering of FR-4's service/price list | populated |
| Slot-choice chips | Selectable list of proposed times (FR-7, FR-8) | default, hover/focus, selected, disabled-after-selection |
| Confirm/Cancel action pair | The FR-9 explicit-confirmation affordance | default, hover/focus, disabled-after-tap (prevents duplicate submission) |
| Booking-history list | Upcoming/Past sections (FR-10) | populated, empty ("no upcoming appointments yet") |

## 3. Interaction Rules & Turn-by-Turn Structure

General rule across every flow below: the agent's message and any affordance (chips, confirm buttons)
render in the same turn; the customer may respond either by using the affordance (tap/click) **or** by
typing the equivalent free-text reply — both satisfy the same underlying intent. This dual-input rule is
stated once here and applies to every turn below unless noted otherwise.

**Decision — dual-input (button-or-text) rather than button-only.** What: every structured affordance
(slot chips, confirm/cancel) accepts an equivalent typed reply. Why: this product's whole premise (brief.md,
Executive Summary) is replacing rigid slot-picker UI with natural language; a button-only chat would
reintroduce exactly the rigidity being designed against. A dedicated button is still offered because it
gives FR-9's "explicit confirmation" a low-ambiguity default and a clean state to build/test against.
Alternative considered: typed-only (no buttons) — rejected, loses the low-friction one-tap path a web
chat surface can offer over WhatsApp's plain text (see `whatsapp-deltas.md`).

### 3.1 Identity Resolution (FR-1, FR-2)

1. **Agent** (on open): "Hi! I'm [Salon]'s booking assistant. Could I get your phone number to pull up
   your account?"
2. **Customer**: types phone number.
3. **Branch A — number matches an existing record (FR-1):**
   - **Agent**: "Welcome back, {name}! What can I help with — booking, browsing services, or checking
     your appointments?" No further identity question is asked this conversation.
4. **Branch B — no match (FR-2):**
   - **Agent**: "I don't have that number on file yet — what's your name?"
   - **Customer**: types name.
   - **Agent** (record created silently, no confirmation screen needed — creation is not a
     customer-facing decision point): "Thanks, {name}! What can I help with today?"

### 3.2 Browse Catalog (FR-4)

Available at any point in the conversation, mid-booking or not.

1. **Customer**: "what do you offer" / "show me your prices" (any phrasing at any turn).
2. **Agent**: renders the **catalog list card** — a structured component (service name + price rows),
   not a text paragraph, reflecting the live Shared Data Store at request time:
   > Here's what we offer right now:
   > - Haircut — ₹300
   > - Color — ₹1200
   > - Beard Trim — ₹150
   >
   > Want to book one?

### 3.3 Booking-Resolution Branches (FR-6, FR-7, FR-8)

Entered after the customer states a booking intent (FR-5), e.g. "I need a haircut Thursday 3pm, no
preference" or "color with Meena at 11am Saturday."

**FR-6 — exact time available (direct confirmation):**
1. **Customer**: states service + exact date/time (+ optional staff preference).
2. **Agent**: "Haircut, Thursday Sep 24 at 3:00 PM with Meena — shall I book it?" **[Confirm] [Cancel]**
   → proceeds to §3.4.

**FR-7 — day only, no time (slot list):**
1. **Customer**: states service + day (+ optional staff preference), no time.
2. **Agent**: renders **slot-choice chips** for that day's open slots, filtered to the named staff member
   if one was stated, salon-wide otherwise: "Meena's open Thursday slots: 11:00 AM, 1:30 PM, 4:00 PM —
   which works?"
3. **Customer**: selects a chip (or types the time).
4. → proceeds to §3.4 with the selected slot restated for confirmation.

**FR-8 — exact time unavailable (nearest alternative):**
1. **Customer**: states service + exact time that turns out to be unavailable.
2. **Agent**: names the reason, then offers alternative(s) as **slot-choice chips**: "Meena's 11am
   Saturday is already booked. She's free at 1:00 PM or 2:30 PM Saturday — want one of these?"
3. **Customer**: selects an alternative (or types it).
4. → proceeds to §3.4.

### 3.4 Booking Confirmation & Creation (FR-9)

1. **Agent** restates the full proposal — service, date/time, staff — with **[Confirm] [Cancel]**
   (buttons disable immediately after either is tapped, to prevent a double-tap creating two bookings).
2. **Customer**: confirms (tap or "yes"/"confirm").
3. **Agent**: "Booked! Haircut with Meena, Thursday Sep 24 at 3:00 PM. Anything else?" — no Booking
   record exists in the Shared Data Store before this turn (FR-9's testable consequence).

**Human-verification checkpoints (SM-4a, SM-4b) — not Customer-visible.** SM-4a (a human reviewing the
Booking Agent's parsed intent) sits between §3.3's customer intent statement and the agent proceeding
into FR-6/7/8. SM-4b (a human reviewing the alternative-slot reasoning) sits between the agent computing
FR-8's alternative and offering it in step 2 above. Per PRD §8, both are build-time/demo
human-verification mechanisms for judging — no FR grants the Customer visibility into or control over
them, and this spec designs **zero UI change** for them: the Customer-facing conversation reads as an
uninterrupted exchange regardless of whether a human reviewed the intermediate step.

**Open question — Architect/Developer:** does SM-4a/SM-4b need any UI hook at all to be demonstrable to
judges (e.g., an operator-only panel showing raw parsed intent + an approve/edit control, visible only on
the presenter's own screen, never in the Customer-facing widget) — or is a terminal/log-based
demonstration sufficient with no dedicated UI? This is a demo-mechanism decision, not a Customer-facing
UX decision, and is not resolved in this spec.

### 3.5 Booking History (FR-10)

1. **Customer**: "show my bookings" / "what do I have coming up."
2. **Agent**: renders the **booking-history list**, split into two labeled sections:
   > **Upcoming:** Haircut with Meena — Thu Sep 24, 3:00 PM
   > **Past:** Color with Arjun — Sep 10, 2:00 PM
3. **Empty state** (no upcoming bookings — a normal state, not an error): "You don't have any upcoming
   appointments yet."

**Privacy boundary enforced here:** the list is filtered server-side to the requesting Customer's own
Bookings only — no query path in this flow returns another Customer's booking, matching FR-10's
consequence.

### 3.6 Cancel (FR-11)

1. **Customer**: "cancel my Thursday haircut" (identifies the booking by day/service; per PRD §7,
   disambiguation among multiple ambiguous matches is not designed — the demo's rehearsed phrasing
   names the booking unambiguously).
2. **Agent**: "Done — I've cancelled your Haircut with Meena on Thursday Sep 24 at 3:00 PM." The freed
   slot is immediately offerable to another customer (FR-11's consequence); no separate action needed.

**Decision — cancel has no pre-write confirm gate, unlike booking/catalog/availability changes.** What:
cancel executes on the stated request and is acknowledged after the fact, rather than restated with a
[Confirm]/[Cancel] pair first. Why: FR-11's stated testable consequences do not include an
explicit-confirmation requirement (unlike FR-9, FR-18, FR-27, which each state one explicitly) — designing
one in would be adding a gate the PRD does not ask for. The agent still names exactly what it cancelled in
its acknowledgment, giving the customer a clear record without an extra turn. Alternative considered:
symmetric confirm-before-cancel, matching the FR-9/18/27 pattern — rejected as scope not asked for by any
FR; noted here so the choice is visible and reversible if the PM/Architect prefers the safer symmetric
behavior.

### 3.7 Reschedule (FR-12)

1. **Customer**: "move my Thursday haircut to Saturday afternoon."
2. **Agent** internally treats this as cancel-old + re-run FR-5–FR-9 for the new time; conversationally:
   "Let's move your Haircut with Meena — Saturday afternoon works, she's free at 1:00 PM or 3:00 PM. Which
   do you prefer?" → **slot-choice chips**.
3. **Customer**: selects 1:00 PM.
4. **Agent**: "Confirm: move your Haircut to Saturday at 1:00 PM with Meena?" **[Confirm] [Cancel]**
5. **Customer**: confirms.
6. **Agent**: "Done! Your Haircut is now Saturday at 1:00 PM with Meena (previously Thursday 3:00 PM)."
   States explicitly that exactly one active booking now exists, satisfying FR-12's testable consequence.

## 4. Edge Cases (Happy-Flow Scope Only)

Per PRD §5/§6.2/§7, non-happy-path handling (ambiguous intent, zero availability, malformed input) is
explicitly out of scope and is **not designed here**. The only states designed beyond the pure happy path
are ordinary UI states every chat surface needs regardless of input quality:
- Empty booking history (§3.5) — a normal state (a new customer legitimately has none yet), not error
  handling.
- Disabled buttons after a single tap (§3.1 general rule, §3.4) — prevents a double-submit race, not a
  defensive-input feature.

No flow is designed for: an unmatched staff preference (e.g., asking for "Ramesh" as a provider — FR-13
notes this is a known, unmodeled limitation), zero availability at all, or ambiguous free text. These
remain PRD-declared known limitations, not gaps in this spec.

## 5. Privacy & Accessibility Notes

**Privacy:**
- FR-10's own-bookings-only boundary (§3.5) is the single privacy-sensitive element on this surface —
  documented above.
- No other Customer's personal data (name, phone number, booking) is ever rendered on this surface at
  any turn.

**Accessibility:**
- Message list is an ARIA live region (`aria-live="polite"`) so new agent turns are announced to
  screen-reader users without interrupting whatever they're doing.
- Slot-choice chips and Confirm/Cancel controls are real `<button>` elements (keyboard-focusable,
  operable via Enter/Space), never non-interactive `<div>`s with click handlers.
- Confirm vs. Cancel is distinguished by label text, not color alone.
- Composer retains focus after the customer sends a message; focus is not stolen when the agent's reply
  and any chips render.
- Typing indicator respects `prefers-reduced-motion` (a static "typing…" label rather than an animated
  dots loop, when the user has that OS/browser preference set).
- Touch targets (chips, buttons) meet a minimum comfortable size for mobile web use, even though no
  native mobile app exists (`stack/rules/base-rules.md` — Mobile: N/A; the web chat is still
  responsive-web, reachable from a phone browser).

## 6. Decision Record Summary

| Decision | Rationale | Alternative(s) considered |
|---|---|---|
| Overlay launcher, not a dedicated page | Matches casual, not-yet-identified entry; keeps host page visible | Dedicated full-page chat route (used instead for the internal Manager Agent) |
| Dual-input confirmation (button or typed text) | Preserves natural-language product premise while giving FR-9 a low-ambiguity default | Button-only; typed-only |
| Cancel has no pre-write confirm gate | FR-11 states no such consequence, unlike FR-9/18/27 | Symmetric confirm-before-cancel |
| Catalog rendered as a structured list card, not paragraph text | Readability; web chat can afford richer components than WhatsApp's plain text | Plain paragraph text (used on WhatsApp — see `whatsapp-deltas.md`) |

## 7. Open Questions Forwarded

1. **To Architect/Developer:** Does SM-4a/SM-4b require a dedicated operator-facing UI hook for demo
   purposes, or is a log/terminal-based demonstration sufficient? (See §3.4.) Not resolved here — this is
   a build-time demo-mechanism decision.
2. **To PM (informational, not blocking):** §3.6's choice not to add a pre-write confirm step for cancel
   is a UX-added interpretation of FR-11's silence on the point, not a literal FR requirement — flagging
   in case the PM wants explicit parity with FR-9/18/27's confirm-before-write pattern.
