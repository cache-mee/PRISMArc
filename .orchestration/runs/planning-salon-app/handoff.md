# Handoff

## Work ID
planning-salon-app

## Objective
Hand off the finalized UX specification for the Booking Agent (Web Chat + WhatsApp), Manager Agent (Web
Chat + WhatsApp), and Owner Dashboard to the Architect and Developer agents, so Phase 5 (epics/stories,
implementation) can begin without re-deriving interaction design from the PRD alone.

## Acceptance Criteria
1. The Architect/Developer can begin epic/story breakdown and implementation directly from the four UX
   artefacts below plus the PRD and `stack/rules/base-rules.md`, without needing to ask the UX Designer
   or the human anything this handoff already answers.
2. Every UX-driven open question is named explicitly, with its owner, so nothing is silently treated as
   resolved that isn't.
3. No designed flow implies a role can reach a tool/action its role-scoped registry would not expose
   (verified against PRD §4.2/§4.3 and addendum.md §1's role matrix at design time — see Decisions below).

## Current State
Phase 4 (UX Design) is **done** for this pass. Four UX specification files are written and internally
consistent with the approved PRD (`status: final`) and the locked stack
(`stack/rules/base-rules.md`, `status: approved`). No Design Approval gate has been recorded yet in
`run-record.md`/`workflow-status.md` — per this workflow's established pattern (Gate 1/2/3 each required
explicit human sign-off before the next phase started), a human gate for these UX artefacts should be
expected before Phase 5 begins in earnest, consistent with `workflow-status.md`'s "Design Approval —
pending" row. This UX pass does not self-validate its own output as gate-cleared (per this agent's scope
boundary: "Accepting its own UX as validated without a separate review pass" is explicitly not owned by
the UX Designer).

## Completed
- **`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/customer-booking-chat.md`** — Web Chat,
  Customer / Booking Agent. Entry point, component/state inventory, turn-by-turn structure for identity
  resolution (FR-1/FR-2), catalog browse (FR-4), all three booking-resolution branches (FR-6/FR-7/FR-8),
  confirmation (FR-9), history (FR-10), cancel (FR-11), reschedule (FR-12); privacy/accessibility notes;
  4 recorded design decisions with rationale and alternatives; 2 forwarded open questions.
- **`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/staff-owner-manager-chat.md`** — Web Chat,
  Staff/Owner / Manager Agent. Entry point (separate internal route from the Customer widget), identity
  resolution (FR-14/FR-24), Staff availability block/unblock with conflict-named response (FR-25–FR-27),
  Owner catalog add/edit/delete (FR-15–FR-18), a role-boundary interaction rule covering FR-21–FR-23 and
  FR-28–FR-30; privacy/accessibility notes; 4 recorded design decisions; 2 forwarded open questions.
- **`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/owner-dashboard.md`** — the one
  traditional screen. Full layout: top bar (Today/Week toggle, Live indicator), Staff list panel
  (Meena/Arjun only, per confirmed PRD Decision 1 that Ramesh is not staff), Bookings panel (Today = two
  staff columns, Week = day×staff table), live-update behavior (FR-32) with no manual refresh control;
  privacy/accessibility notes; 3 recorded design decisions; 1 forwarded open question (Dashboard access
  gating — unspecified in the PRD).
- **`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/whatsapp-deltas.md`** — channel-delta
  notes for both agents: identity-question skip (FR-3, FR-24), plain-text-only rendering in place of Web
  Chat's structured chips/cards/buttons, and an explicit statement of what does NOT change (intent
  parsing, resolution logic, conflict detection, role boundaries — per the channel-parity NFR, PRD §7,
  and the "no per-channel forking" rule in `stack/rules/base-rules.md`); 1 recorded design decision
  (plain-text-only given Twilio Sandbox, not a production WhatsApp Business Account); 1 forwarded open
  question.
- Every design decision with non-obvious rationale is recorded inline (what/why/alternatives) and rolled
  up into a per-file "Decision Record Summary" table, per this agent's evidence expectations.
- Privacy-sensitive elements are explicitly documented with the information boundary enforced: FR-10's
  own-bookings-only filter (customer chat), FR-29's no-cross-staff-visibility boundary (manager chat), and
  the Dashboard's deliberate omission of customer phone numbers (dashboard).

## Failed / Unresolved
Nothing failed. The following are UX-driven open questions/scope implications, explicitly not resolved
here per this agent's scope boundary against making architecture/product-scope decisions:

1. **SM-4a/SM-4b/SM-4c UI hook (Architect/Developer decision).** PRD §8's three human-verification
   checkpoints are, per this spec, deliberately designed with **zero Customer/Staff/Owner-visible UI
   change** — the conversation reads as uninterrupted regardless of whether a human reviewed the
   intermediate step. Whether the demo needs any operator-facing hook at all (e.g., a presenter-only panel
   showing raw parsed intent / conflict outcome with an approve-or-edit control) or whether a
   terminal/log-based demonstration is sufficient for judging is **not decided in this spec** — it is a
   build-time demo-mechanism decision belonging to the Architect/Developer. See
   `customer-booking-chat.md` §3.4/§7, `staff-owner-manager-chat.md` §3.3/§8.
2. **Dashboard access gating (Architect decision).** The PRD's auth-minimalism NFR (§7) covers the
   conversational agents' phone-lookup identity only; it is silent on how (or whether) the `/dashboard`
   route itself is restricted to Ramesh. This spec does not invent an authentication screen. See
   `owner-dashboard.md` §1, §6.
3. **Twilio WhatsApp Sandbox capability check (Architect/Developer decision).** This spec defaults every
   WhatsApp choice/confirm point to plain text, on the grounds that Sandbox mode (not a production WhatsApp
   Business Account, per `stack/rules/base-rules.md`) may not reliably support interactive quick-reply
   buttons within the 24-hour window. If Sandbox is confirmed to support them reliably, the Architect/
   Developer may choose to use them without needing a new UX pass — the underlying choice/confirm content
   is unchanged either way. See `whatsapp-deltas.md` §1, §4.
4. **PM-informational, non-blocking:** `customer-booking-chat.md` §3.6 designs cancel (FR-11) without a
   pre-write confirm gate, unlike booking/catalog/availability writes (FR-9/18/27) — because FR-11's
   stated consequences do not include one. Flagged in case the PM wants explicit symmetry added as a
   scope decision; not built into this spec as a requirement it doesn't have.
5. **Non-blocking design-consistency note:** `staff-owner-manager-chat.md` §3.2/§8 flags that Staff
   conflict handling only *names* a conflict (per FR-26) rather than *suggesting an alternative* the way
   the Booking Agent does for Customers (FR-8) — not designed as a feature since no Staff-facing FR asks
   for it; noted as a possible future consistency improvement, not a gap in this pass.

## Constraints
- `CLAUDE.md`'s `B2B_BE/`/`B2B_FE/` split remains authoritative for all application code the Architect and
  Developer produce; the UX artefacts above describe behavior/component states only and make no
  implementation-technology choices (framework internals, state management) beyond what
  `stack/rules/base-rules.md` already locks.
- This UX spec is happy-flow-only, per PRD §5/§6.2/§7 — no defensive/ambiguous-input UI beyond the ordinary
  component states every chat/dashboard surface needs regardless of input quality (e.g., an empty booking
  history, a disabled button after one tap). This is called out explicitly per file (each file's §4/edge
  cases section) so it is checkable, not assumed.
- Role-based permission enforcement (Owner/Admin vs. Staff vs. Customer, addendum.md §1) is treated as a
  hard product constraint: `staff-owner-manager-chat.md` §5 designs the *conversational manifestation*
  (short, plain redirect copy) of a boundary whose actual enforcement is architectural (role-scoped tool
  registries, `stack/rules/base-rules.md`) — the UX spec does not claim to be the enforcement mechanism
  itself.
- `stack/rules/base-rules.md` remains locked; nothing in this UX pass proposes changing it. Where this
  spec assumes a specific route/component location (e.g., `B2B_FE/src/chat/`, `B2B_FE/src/dashboard/`),
  it is citing the already-enforced layout, not proposing a new one.

## Decisions
- Every design decision made in this UX pass (11 total across the four files) is recorded inline with
  rationale and alternatives considered, and rolled up per file in a "Decision Record Summary" table —
  see each file's final section before "Open Questions Forwarded."
- No product-scope or architecture decision was made by this agent. Where a UX requirement bordered on a
  scope or architecture question (the four items in Failed/Unresolved above), it was recorded as an open
  question rather than resolved unilaterally, per this agent's scope boundary.

## Evidence
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/customer-booking-chat.md`
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/staff-owner-manager-chat.md`
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/owner-dashboard.md`
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/whatsapp-deltas.md`
- `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md` — source FRs/UJs every flow above
  traces to.
- `stack/rules/base-rules.md` — the locked stack/layout this spec designs against.
- `.orchestration/runs/planning-salon-app/artifacts/handoff-phase3-stack-to-ux.md` — the superseded
  PM/Architect → UX handoff, retained for trail continuity.

## Next Action
- **Human (Design Approval gate, expected per `workflow-status.md`):** review the four UX artefacts above,
  in particular the 5 open questions in Failed/Unresolved, before Phase 5 (Epics & Stories) proceeds.
- **Architect:** confirm or decide items 1–3 in Failed/Unresolved (SM-4a/b/c UI hook mechanism, Dashboard
  access gating, WhatsApp Sandbox interactive-button feasibility) as part of epic/story breakdown; none of
  the three blocks the *content* of any designed conversation turn, only how/whether an operator-facing
  or auth mechanism wraps around it.
- **Developer (once epics/stories exist):** build the Web Chat widget, Manager Agent route, and Dashboard
  against the four UX files above and `stack/rules/base-rules.md`'s enforced `B2B_FE/src/{chat,dashboard,
  shared,api}/` layout; the shared `Confirm/Cancel action pair`, message bubble, and typing-indicator
  components are designed once and reused across the Customer and Manager Agent chat surfaces (see
  `staff-owner-manager-chat.md` §4's cross-reference).

## Completion Condition
This handoff is satisfied once the Architect/Developer have either (a) resolved items 1–3 in
Failed/Unresolved as part of Phase 5 planning, or (b) explicitly deferred them with a recorded decision,
and epics/stories exist that reference the four UX artefacts above by path for every Customer/Staff/Owner-
facing story.

## Escalation
No UX requirement was found to be technically contradictory, and no privacy constraint from the brief was
found unmeetable within stated scope — no escalation is raised by this pass. Items 1–3 in
Failed/Unresolved are routine Architect/Developer decisions, not escalations requiring a human beyond the
already-expected Design Approval gate.
