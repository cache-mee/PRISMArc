---
title: UX Specification — Web Chat, Staff/Owner (Manager Agent)
status: draft
created: 2026-09-17
updated: 2026-09-17
surface: Web Chat — Staff/Owner
realizes: UJ-4, UJ-5
covers_fr: FR-14 through FR-30
sources:
  - bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md
  - bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/addendum.md (§1 role matrix)
  - stack/rules/base-rules.md
---

# Web Chat — Staff/Owner (Manager Agent)

Same underlying chat component library as the Customer surface (`B2B_FE/src/chat/`, which
`stack/rules/base-rules.md` names explicitly as hosting "Booking Agent + Manager Agent conversation UI"),
but a distinct entry point and distinct conversational content/identity flow, per this audience being
internal (staff/owner), not public.

## 1. Entry Point

**Decision — separate internal route, not a mode toggle inside the public Customer widget.** What: the
Manager Agent is reached via its own route in the same React app (e.g., `/team`), landing on a dedicated
chat page rather than an overlay. Why: the Customer and Manager Agents have different audiences,
different identity models (FR-1/2 vs. FR-14/24), and different permission surfaces (role-scoped tool
registries per `stack/rules/base-rules.md`) — mixing them behind a single public launcher risks a customer
landing in a staff flow (or the reverse) and blurs an audience boundary the PRD treats as structural
(§4.2 vs. §4.3). This is consistent with, not a departure from, the locked stack's "one codebase serving
two surfaces" framing (`stack/rules/base-rules.md` — Frontend row) — a third internal route within the
same codebase, not a new codebase. Alternative considered: a role-selector shown inside the public widget
before any identity question — rejected because no FR describes a manual role-selection step; identity is
phone-lookup only (FR-1/FR-3/FR-14/FR-24), and adding a selector would invent an unspecified interaction.

No login screen is designed beyond the phone-number exchange in §2 — consistent with the PRD's
identity/auth minimalism NFR (§7).

## 2. Identity Resolution (FR-14, FR-24)

1. **Agent** (on open, Web Chat): "Hi — I'm the salon's team assistant. What's your phone number?"
2. **Staff/Owner**: types phone number.
3. **Match against the pre-seeded Staff/Owner records** determines which role-scoped conversation
   follows:
   - **Staff match (Meena or Arjun):** "Hi Meena! Want to update your availability?"
   - **Owner/Admin match (Ramesh):** "Hi Ramesh! Want to update the service catalog?"
4. **No match:** out of scope for this demo per FR-14's own stated consequence ("a non-matching number is
   out of scope for this demo — no fallback flow defined"). This spec designs no UI for that case; it is a
   named PRD limitation, not a gap here.

**Decision — role determines conversational content, never a visible role label or menu.** What: the
agent's own opening line differs by role (staff vs. owner), but no separate "menu screen" of available
actions is shown. Why: each role's permitted action set is small (staff: block/unblock only; owner:
catalog CRUD only) and the FRs describe these as stated-in-natural-language requests, not menu selections
— a menu would reintroduce the slot-picker-style rigidity this product is designed against (brief.md,
What Makes This Different). Alternative considered: a persistent quick-action chip row per role (e.g.,
"Block time" / "Unblock time" for staff) — allowed as an optional low-friction affordance layered on top
of free text, not a replacement for it; not required by any FR, so left as a Developer-phase nice-to-have
rather than a specified requirement.

## 3. Staff — Availability Block/Unblock (FR-25, FR-26, FR-27)

### 3.1 Block, no conflict
1. **Meena**: "block out Friday morning, I'm out."
2. **Agent** parses the window (Friday, morning) and checks it against Meena's existing Bookings
   (FR-26) — invisibly to Meena (see §3.3 on SM-4c).
3. No conflict found → **Agent**: "Got it — I'll mark you unavailable Friday 9 AM–1 PM. Confirm?"
   **[Confirm] [Cancel]**
4. **Meena**: confirms.
5. **Agent**: "Done — Friday morning is now blocked on your schedule." Immediately reflected in the
   Booking Agent's next availability check for Meena (FR-27's consequence) and on the Dashboard (FR-32).

### 3.2 Block, with conflict (FR-26's "named, not silent" requirement)
1. **Meena**: "block out all of Friday, I'm out."
2. **Agent** checks the window against her Bookings, finds one that overlaps.
3. **Agent**: "Friday at 10 AM is already booked — you have a haircut appointment with a customer then,
   so I can't block that whole window. Want to choose a different time to block?" No block is applied.
4. **Meena** restates a narrower window (e.g., "just the morning before 10") → flow re-enters §3.1.

**Decision — on conflict, the agent names it and asks for a different window; it does not propose a
partial-block alternative automatically.** What: unlike the Booking Agent's FR-8 (which actively suggests
alternative *times*), the Manager Agent here only reports the conflict and invites the staff member to
restate their own request. Why: FR-26's stated consequence is that the conflict is *named*, not silently
rejected — it does not ask for an alternative-suggestion behavior the way FR-8 explicitly does for
Customers; inventing an auto-suggested partial-block would be adding an unscoped feature. Alternative
considered: mirror FR-8's alternative-suggestion pattern here too — rejected as not asked for by any
Staff-facing FR (FR-25–FR-27), and flagged below as an open question rather than silently added.

### 3.3 Unblock
1. **Meena**: "unblock Saturday."
2. **Agent** (no conflict check applies to unblock — FR-26 is scoped to blocks only, since opening time
   cannot collide with an existing Booking): "You said unblock Saturday — I'll reopen your whole Saturday
   schedule. Confirm?" **[Confirm] [Cancel]**
3. **Meena**: confirms → **Agent**: "Done — Saturday is open again."

**Human-verification checkpoint (SM-4c) — not Staff-visible.** SM-4c (a human reviewing the Manager
Agent's conflict-detection outcome) sits between §3.1/§3.2's conflict check and the block/unblock being
finalized (FR-27) or, per PRD §8, before a resulting Booking (FR-9) is finalized. As with SM-4a/SM-4b on
the Customer surface, this spec designs **zero UI change** for it — the Staff-facing conversation reads
as an uninterrupted exchange. Same open question as raised in `customer-booking-chat.md` §3.4 applies
here: whether any operator-facing hook is needed for demo purposes is an Architect/Developer decision, not
resolved in this spec.

## 4. Owner (Ramesh) — Catalog Management (FR-15, FR-16, FR-17, FR-18)

### 4.1 Add
1. **Ramesh**: "add beard trim for 150 rupees."
2. **Agent**: "New service: Beard Trim — ₹150. Add it to the catalog?" **[Confirm] [Cancel]**
3. **Ramesh**: confirms → **Agent**: "Added! Beard Trim (₹150) is now live." Immediately returned by
   FR-4's Customer-side catalog browse.

### 4.2 Edit
1. **Ramesh**: "change haircut to 350."
2. **Agent**: "Update Haircut price from ₹300 to ₹350 — confirm?" **[Confirm] [Cancel]**
3. **Ramesh**: confirms → **Agent**: "Updated." Prior price no longer returned by FR-4 (FR-16's
   consequence).

### 4.3 Delete
1. **Ramesh**: "remove beard trim."
2. **Agent**: "Remove Beard Trim (₹150) from the catalog — confirm?" **[Confirm] [Cancel]**
3. **Ramesh**: confirms → **Agent**: "Removed." No longer offered via FR-4 (FR-17's consequence).

All three share the same confirm/cancel affordance pattern as §3 and `customer-booking-chat.md` §3.4 —
one consistent component (`Confirm/Cancel action pair`) used across every write-confirming moment in the
product (FR-9, FR-18, FR-27), so a Customer, Staff member, or Owner all learn the same interaction once.

## 5. Role-Boundary Interaction Rule (FR-21–FR-23, FR-28–FR-30)

Per the role matrix (addendum.md §1) and the stack's role-scoped tool registries
(`stack/rules/base-rules.md`), a role's disallowed actions are simply not registered as tools for that
session — the primary enforcement is architectural, not conversational. This spec's only UX obligation is
what the conversation *shows* when a disallowed action is asked for directly:

- **Ramesh asks to block/unblock his own time, or to change Meena's/Arjun's schedule (FR-21, FR-23):**
  **Agent**: "That's managed by Meena and Arjun themselves for their own schedules — I can help you with
  the service catalog instead." Short, single-turn redirect; no retry loop, no error styling.
- **A Staff member asks about the catalog, the dashboard, or the other staff member's schedule (FR-28,
  FR-29, FR-30):** **Agent**: "That's something Ramesh manages — I can help you with your own
  availability." Same short-redirect pattern.

**Decision — role-boundary responses are plain, one-line redirects, not error states.** What: no
"permission denied" styling, no distinct visual treatment from a normal agent turn. Why: PRD §7 explicitly
scopes out defensive/non-happy-path UI; a disallowed request is not a malformed input, it's simply outside
what this identified role can do, and the FRs themselves describe the outcome as "not offered as an
available action" (FR-21, FR-23, FR-28–FR-30) rather than a rejected attempt — the redirect copy is
informational, matching that framing. No proactive quick-action chip ever surfaces a disallowed action in
the first place (§2's decision on role-scoped opening content).

## 6. Privacy & Accessibility Notes

**Privacy:** the Manager Agent never surfaces another Staff member's schedule, the full Staff list, or
Dashboard-equivalent data to a Staff-identified session (FR-29's boundary) — enforced structurally via
role-scoped tool registries, and reflected here in the fact that no Staff-facing turn ever names another
staff member's bookings.

**Accessibility:** same component-level rules as `customer-booking-chat.md` §5 (live-region message list,
real `<button>` affordances, no color-only signaling, focus management, reduced-motion typing indicator) —
inherited from the shared chat component library, not restated per surface.

## 7. Decision Record Summary

| Decision | Rationale | Alternative(s) considered |
|---|---|---|
| Separate internal route for Manager Agent, not a toggle in the public widget | Audience/identity/permission separation; matches PRD's structural staff/owner vs. customer split | Role-selector inside the public Customer widget |
| Role determines opening content, no menu screen | Small per-role action sets; menu reintroduces slot-picker rigidity | Persistent quick-action chip row (allowed as optional layer, not required) |
| Conflict is named, not auto-resolved with a suggested alternative | FR-26 only requires naming the conflict; FR-8's alternative-suggestion is Customer-facing only | Mirroring FR-8's alternative-slot suggestion for staff conflicts too |
| Role-boundary responses are plain one-line redirects | PRD §7 scopes out defensive/error UI; FRs frame this as "not offered," not "rejected" | Distinct error-state styling |

## 8. Open Questions Forwarded

1. **To Architect/Developer:** same SM-4c UI-hook question as SM-4a/SM-4b (see
   `customer-booking-chat.md` §3.4 and §7) — not resolved here.
2. **To PM/Architect:** should staff conflict handling (§3.2) eventually mirror the Booking Agent's
   alternative-suggestion pattern (FR-8)? Not required by any current FR; flagged as a possible post-MVP
   consistency improvement, not built into this spec.
