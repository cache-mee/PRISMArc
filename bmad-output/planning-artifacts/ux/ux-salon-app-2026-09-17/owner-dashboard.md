---
title: UX Specification — Owner Dashboard (Read-Only)
status: draft
created: 2026-09-17
updated: 2026-09-17
surface: Owner Dashboard
realizes: UJ-6
covers_fr: FR-19, FR-20, FR-32
sources:
  - bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md
  - stack/rules/base-rules.md
---

# Owner Dashboard (Read-Only)

The one surface in this product that is a traditional screen, not a conversation. Non-conversational,
read-only, single owner (Ramesh) audience. Built in `B2B_FE/src/dashboard/` per
`stack/rules/base-rules.md`'s enforced layout.

## 1. Entry Point

Ramesh navigates to the dashboard route (e.g., `/dashboard`) in the same React app that hosts the chat
surfaces. No booking/catalog action is available from here at all (FR-19, FR-20's consequence: "no
add/remove/edit control," "no booking, cancellation, or edit action").

**Open question — Architect/Developer:** the PRD's identity/auth minimalism NFR (§7) covers only the
conversational agents' phone-number lookup (FR-1–3, FR-14, FR-24); it is silent on how — or whether — the
Dashboard route itself is gated to Ramesh specifically. This spec does not invent an authentication screen
(that would be an architecture/security decision outside UX scope), but flags the gap explicitly: is the
Dashboard reachable by anyone with the URL for this demo (consistent with the stated no-password/no-OTP
minimalism), or does the Architect want a minimal owner-only gate even though no FR calls for one?

## 2. Screen Layout

A single screen, three regions:

### 2.1 Top bar
- Salon name / "Dashboard" label.
- **Today / This Week** toggle (segmented control) — FR-20 names both views explicitly ("today's or the
  week's").
- A small **"Live"** indicator (pulsing dot + label) — see decision below.

### 2.2 Staff list panel
One card per Staff member — **Meena and Arjun only**, never Ramesh (FR-19's confirmed consequence, tracing
to PRD Decision 1: Ramesh is admin-only, not a bookable Staff member). Each card shows:
- Name.
- A status pill derived from current Availability: **"Available now"** or **"Blocked now."**
- A same-day booking count (e.g., "3 bookings today").

No edit, add, or remove control exists anywhere on this panel (FR-19, FR-22's consequence: the Staff list
is view-only).

### 2.3 Bookings panel
- **Today view:** two columns, one per Staff member (Meena | Arjun), each a chronological list of that
  day's Bookings: time, customer name, service.
- **Week view:** a table — rows are days (Mon–Sun), columns are Staff members; each cell lists that
  day/staff's bookings as compact entries (e.g., "10:00 Haircut — Priya").
- **Empty state** (a normal state, not error handling): a day/staff cell with nothing scheduled shows
  muted "No bookings" text.

No booking, cancellation, or edit action is exposed from any row or cell (FR-20's consequence).

## 3. Live-Update Behavior (FR-32)

- A Booking created via the Booking Agent, or an Availability change confirmed via the Manager Agent,
  appears on this screen without Ramesh refreshing, re-navigating, or taking any action.
- New booking rows insert at their correctly sorted time position with a brief highlight/fade transition
  (a few seconds) so Ramesh notices the change without needing to spot it unaided.
- A staff status-pill update (Available ↔ Blocked) reflects immediately when a block/unblock is confirmed
  via the Manager Agent.
- No manual refresh control exists anywhere on this screen — its absence is deliberate, not an omission,
  since FR-32 explicitly requires no manual trigger.

**Decision — a visible "Live" indicator badge.** What: a small pulsing-dot + "Live" label in the top bar.
Why: FR-32's real-time property is otherwise *invisible* until something changes — UJ-6's climax beat is
specifically that Ramesh sees a booking appear that he never entered himself, proving the shared-store
behavior; a visible "Live" cue primes him (and a watching judge, per SM-3) to notice and trust that what's
on screen is current, rather than wondering if it's stale. This is a UX addition beyond what any FR
literally requires, not a new feature — flagged here as a non-obvious choice per this spec's evidence
expectations. Alternative considered: no indicator, relying solely on the live-update behavior itself to
be self-evident — rejected because a judge watching for SM-3/SM-2's live-reflection proof point benefits
from an explicit visual cue rather than having to infer freshness from timing alone.

## 4. Privacy & Accessibility Notes

**Privacy — information boundary enforced on this surface:** booking entries show the customer's name,
service, and time only — the minimum needed for Ramesh's stated operational need (UJ-6: "an accurate,
current picture of the day"). The customer's phone number and any other customer record (e.g., their
booking history beyond the shown entry) are **not** displayed here. This is a UX-level least-privilege
choice bounding Ramesh's dashboard visibility to what FR-20 actually requires (current bookings), not an
itemized requirement in the addendum.md §1 role matrix — documented explicitly per this agent's
privacy-documentation duty.

**Accessibility:**
- The Week view uses real `<table>` semantics (or an ARIA grid) with row/column headers (day, staff
  name) — not a purely visual grid of `<div>`s.
- New-booking arrivals are announced via a debounced `aria-live="polite"` summary (e.g., "1 new booking
  added") rather than announcing every field change, to avoid overwhelming screen-reader users during a
  busy live demo.
- Status pills ("Available now" / "Blocked now") use icon + text, never color alone, to convey state.
- The Today/Week toggle is keyboard-operable (arrow keys or tab+enter, standard segmented-control
  pattern) and exposes its current selection via `aria-pressed`/`aria-selected`.
- Sufficient color contrast on status pills and highlight-fade transitions; the highlight transition
  respects `prefers-reduced-motion` (falling back to a static border/label change rather than an animated
  fade).

## 5. Decision Record Summary

| Decision | Rationale | Alternative(s) considered |
|---|---|---|
| Visible "Live" indicator badge | Makes FR-32's real-time property observable, supporting UJ-6/SM-2/SM-3's proof-point moment | No indicator, rely on implicit timing |
| Two-column (staff) layout for Today view | Matches the salon's actual bookable-staff count (Meena, Arjun) and gives an at-a-glance per-person schedule | Single flat chronological list across both staff |
| Dashboard shows customer name/service/time only, not phone number | Least-privilege bound on an admin view where the FR doesn't itemize what's shown | Showing the full booking record including phone number |

## 6. Open Questions Forwarded

1. **To Architect:** is any access gate needed on the `/dashboard` route, given the PRD's auth-minimalism
   NFR covers only the conversational agents and is silent on Dashboard access? Not designed here.
