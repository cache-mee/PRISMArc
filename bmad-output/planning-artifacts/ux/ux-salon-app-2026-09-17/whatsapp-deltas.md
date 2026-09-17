---
title: UX Specification — WhatsApp Channel Deltas
status: draft
created: 2026-09-17
updated: 2026-09-17
surface: WhatsApp (Booking Agent + Manager Agent)
covers_fr: FR-3, FR-24; channel-parity NFR (PRD §7)
sources:
  - bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md
  - bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/addendum.md (§2.3)
  - stack/rules/base-rules.md
---

# WhatsApp Channel Deltas

WhatsApp is **not a fourth surface** — it is the same Booking Agent and the same Manager Agent, reached
through a different channel. WhatsApp's own native app renders the conversation UI (message bubbles,
typing indicator, timestamps); there is nothing to wireframe. This file specifies only the
**message-flow and conversational-copy differences** from the Web Chat specs in
`customer-booking-chat.md` and `staff-owner-manager-chat.md`, per the PRD's channel-parity NFR (§7): agent
*behavior* is identical in substance across channels — only identity-question mechanics and message
formatting differ (addendum.md §2.3: WhatsApp is a second front door to the same agent core, not a second
agent; channel differences must stay confined to thin adapters, per `stack/rules/base-rules.md`).

## 1. Booking Agent (Customer) — WhatsApp Delta

**Identity resolution (FR-3) — the phone-number question never happens.**
- The channel already supplies the phone number (Twilio inbound webhook, per `stack/rules/base-rules.md`
  — `app/api/webhooks/whatsapp.py`). Compare to Web Chat's §3.1 turn 1 ("Could I get your phone
  number...") — this turn is **skipped entirely** on WhatsApp.
- **Known number:** first agent message is directly the name-based greeting: "Welcome back, Priya! What
  can I help with — booking, browsing services, or checking your appointments?"
- **Unknown number:** exactly one question is asked (name), never the phone number: "Hi! I don't have
  this number on file yet — what's your name?" → then proceeds directly to intent, same as Web Chat §3.1
  Branch B minus the phone-number turn.

**No rich affordances — plain text only.**
- No slot-choice chips, no Confirm/Cancel buttons. Every choice point in `customer-booking-chat.md` §3.3
  (FR-7, FR-8) and §3.4 (FR-9) that renders as tappable UI on Web Chat renders as a **numbered plain-text
  list** on WhatsApp instead:
  > Meena's open Thursday slots:
  > 1) 11:00 AM
  > 2) 1:30 PM
  > 3) 4:00 PM
  > Reply with a number or a time.
- Confirmation (FR-9, and the confirm step embedded in reschedule, FR-12) is a plain yes/no text question:
  > Haircut, Thursday Sep 24 at 3:00 PM with Meena — reply YES to confirm or NO to change it.
- The catalog list (FR-4) renders as a plain text list rather than the Web Chat "catalog list card"
  component:
  > Here's what we offer right now:
  > - Haircut — ₹300
  > - Color — ₹1200
  > - Beard Trim — ₹150
  > Want to book one?
- Bold/emphasis, where used at all, uses WhatsApp's own plain-text markup (`*bold*`), not HTML/rich
  formatting.

**Decision — plain text for everything, no interactive buttons, even where Twilio's WhatsApp API
technically supports quick-reply buttons.** What: this spec treats every WhatsApp choice/confirm point as
plain numbered-list or yes/no text, not an interactive button message. Why: `stack/rules/base-rules.md`
specifies **Twilio WhatsApp Sandbox**, not a production WhatsApp Business Account — interactive
message/button features are most reliably available through approved templates on a production account,
and are not guaranteed to behave consistently in Sandbox mode within a 24-hour build window. Choosing
plain text uniformly removes that risk rather than debugging Sandbox-specific interactive-message behavior
live. Alternative considered: use Twilio's quick-reply buttons if Sandbox supports them for the demo
number — not ruled out permanently, but not assumed here; flagged as an open item below rather than
designed against an unconfirmed capability.

**Booking history, cancel, reschedule (FR-10, FR-11, FR-12) — same content, plain-text rendering.**
Structurally identical to `customer-booking-chat.md` §3.5–§3.7 (same agent logic, same copy), rendered as
plain WhatsApp text messages instead of structured list/card components. No behavioral difference.

**Human-verification checkpoints (SM-4a, SM-4b).** No channel difference — these are backend/build-time
mechanisms (see `customer-booking-chat.md` §3.4), entirely independent of which channel the conversation
is happening on.

**Typing indicator.** WhatsApp's native client shows its own "typing…" indicator automatically once the
Business API marks a conversation as composing; this is a platform-native behavior, not something this
product designs or controls, unlike the custom typing-indicator component on Web Chat.

## 2. Manager Agent (Staff/Owner) — WhatsApp Delta

**Identity resolution (FR-24) — same skip pattern as FR-3.**
- The phone number is already known from the channel; the identity turn in
  `staff-owner-manager-chat.md` §2 step 1 ("What's your phone number?") is skipped. The first message is
  directly the role-based greeting: "Hi Meena! Want to update your availability?" or "Hi Ramesh! Want to
  update the service catalog?"
- No-match case: same as Web Chat — out of scope for this demo, no fallback flow.

**No rich affordances — plain text only.**
- Availability block/unblock confirmation (`staff-owner-manager-chat.md` §3.1, §3.3) and catalog
  add/edit/delete confirmation (§4.1–§4.3) each render as a plain yes/no text question on WhatsApp instead
  of a Confirm/Cancel button pair:
  > I'll mark you unavailable Friday 9 AM–1 PM. Reply YES to confirm or NO to cancel.
- The conflict-named response (§3.2) is unchanged in content — it is already plain text on Web Chat too —
  and needs no delta beyond formatting.

**Human-verification checkpoint (SM-4c).** No channel difference — same backend/build-time mechanism
regardless of channel, per `staff-owner-manager-chat.md` §3.3.

**Role-boundary redirects (§5 of `staff-owner-manager-chat.md`).** Identical copy and behavior on
WhatsApp; no channel-specific variation, since these are plain text messages on both channels already.

## 3. What Does Not Change

Per the channel-parity NFR (PRD §7) and the "same agent, every channel" constraint
(`stack/rules/base-rules.md` — Forbidden: "No forking of core agent/intent-parsing logic per channel"):
intent parsing, the three booking-resolution branches (FR-6/7/8), conflict detection (FR-26), catalog
logic (FR-15–18), and every role-permission boundary are byte-for-byte the same reasoning on WhatsApp as
on Web Chat. Only the identity-question mechanics (§1, §2 above) and message formatting (plain text vs.
structured components) differ. No WhatsApp-specific wording of the *agent's reasoning* is designed or
permitted — only rendering format changes.

## 4. Open Questions Forwarded

1. **To Architect/Developer:** can Twilio WhatsApp Sandbox reliably render quick-reply/interactive button
   messages for this build, or should plain-text-only (as designed above) be treated as the confirmed
   approach for the full 24-hour build? This spec defaults to plain-text-only given Sandbox constraints
   but does not rule out richer affordances if confirmed feasible.
