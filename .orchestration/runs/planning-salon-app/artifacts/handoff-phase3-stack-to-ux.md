# Handoff

## Work ID
planning-salon-app

## Objective
Hand off the finalized PRD for the Agentic Appointment Management Engine (Salon Edition, hackathon
scope) to the Architect and UX Designer agents so Phase 3 (system design, epics/stories, interaction
design) can begin without reconstructing Phase 1/2 discovery or re-litigating decisions already resolved.

## Acceptance Criteria
1. The Architect can begin system design and epic/story breakdown directly from
   `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md` plus the brief/addendum, without
   needing to ask the PM or the human anything this handoff already answers.
2. The UX Designer can begin interaction design for both chat surfaces and the dashboard directly from
   the same PRD, using §1–§4 (personas, journeys, features/FRs) and §3 (glossary) as the primary input.
3. Every item still open for either agent is named explicitly, with its owner and where it's recorded —
   nothing is silently treated as resolved that isn't.

## Current State
Phase 2 (PRD) is **done**. `prd.md` frontmatter `status: final`.

**Phase 3 (Stack) is now done and locked.** `stack/stack-proposal.md` frontmatter is `status: approved`
(Gate 3, 2026-09-17). The user approved the proposal unchanged; their one clarifying question (whether
the Twilio WhatsApp integration path was fully covered) was answered by confirming §6.2's Sandbox
recommendation already covers it end-to-end — no revision was requested or made. The Architect has
written the locked `stack/rules/base-rules.md` and seeded `stack/rules/client-rules.md` per the Gate 3
approval sequence in `sdlc-planning-workflow`. **The UX Designer and Developer agents build against
`stack/rules/base-rules.md` from this point forward, not against `stack/stack-proposal.md` directly** —
the proposal remains the rationale record; the rules file is the enforced contract.

All three product-level questions the brief left open for the human (Ramesh's role; demo KPI tracking;
which human-verification moment(s) to showcase) were answered directly by the user on 2026-09-17 and are
locked decisions in PRD §9.1 — not assumptions, not open items. No PM-owned open question remains in the
PRD. Gate 2 (PRD approval, if the orchestrating workflow requires a distinct human sign-off before Phase
3 starts) has not yet been separately recorded in `run-record.md` / `workflow-status.md` as of this
handoff's PM-authored portion; that is unaffected by, and unresolved by, the Phase 3 work recorded above.

## Completed
- PRD produced and finalized at
  `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md` (32 FRs across 4 feature areas,
  6 user journeys, grouped by persona: Customer §4.1, Ramesh/Owner-Admin §4.2, Meena-Arjun/Staff §4.3,
  cross-cutting shared-state §4.4).
- The three business decisions the brief flagged as needing human/stakeholder sign-off (addendum.md §4
  rows 1, 2, 11) were resolved directly by the user on 2026-09-17 and are recorded in PRD §9.1:
  - **Decision 1 (Ramesh's role):** admin-only, confirmed — he does not take appointments and does not
    manage his own availability. No FR text changed in substance; only marker language changed. Touches
    PRD §2.2, §4.1 FR-13, §4.2 FR-19/FR-21, §6.2.
  - **Decision 2 (demo KPIs):** confirmed — no business-style metrics (bookings-created counter,
    cancellation rate, retention, conversion, wait-time reduction, etc.) are tracked for this demo.
    Touches PRD §8 ("Note on business KPIs").
  - **Decision 3 (human-verification moment):** confirmed — **all three** candidate checkpoints are
    showcased, not one: (a) a human reviews/corrects the Booking Agent's parsed booking intent
    (service/date/time/staff) before it's acted on; (b) a human reviews the Booking Agent's reasoning
    when it suggests an alternative time slot, before it's offered to the customer; (c) a human reviews
    the Manager Agent's conflict-detection outcome before an availability change or booking is finalized.
    Recorded as PRD §8 SM-4a/SM-4b/SM-4c.
- Every `[PENDING USER DECISION]` marker in the PRD tied to these three items was removed and replaced
  with "confirmed decision" language at every location it appeared (§2.2, §4.1 FR-13, §4.2 FR-19, §4.2
  FR-21, §6.2, §8, §9, §10 — see PRD §9.1 for the full list per decision).
- `.memlog.md` at `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/.memlog.md` updated with
  the resolution event.
- **Stack proposal produced, presented, and approved (Architect, Gate 3, 2026-09-17):**
  `stack/stack-proposal.md` — React+TypeScript(Vite) frontend, FastAPI/Python 3.12+ backend, PostgreSQL
  16+, no native mobile, Docker Compose infra, in-process tool registration (no MCP), Twilio WhatsApp
  Sandbox. Every PRD §9.2 carried-forward technical item (interface, agent coordination pattern, intent
  parsing, conflict detection, data model) and every `addendum.md` §4 open assumption relevant to the
  Architect (Postgres confirmation, session-state mechanism, web-chat frontend technology, MCP vs.
  in-process tools, repo-layout nesting) was resolved in this document — see stack-proposal.md §8 for the
  explicit resolution map. Approved unchanged at Gate 3.
- **`stack/rules/base-rules.md` written and locked** (Architect, on approval): stack table; language &
  style for both `B2B_BE/` (Python 3.12+, type hints, Pydantic v2, `black`/`ruff`) and `B2B_FE/`
  (TypeScript strict mode, function components, `prettier`/`eslint`); the enforced `B2B_BE/app/...` /
  `B2B_FE/src/...` layout; required patterns (in-process tool registration, role-scoped tool registries,
  single-process two-agent shape, channel-adapter-only divergence, backend-persisted conversation state,
  two-layered conflict detection); forbidden patterns (no MCP tool-exposure layer, no per-channel
  agent-logic forking, no client-resent history, no heavyweight agent-orchestration framework, no full
  cloud infra); naming conventions (files/folders, API routes, `snake_case` DB tables — `salons`,
  `staff`, `services`, `bookings`, `availability`, `messages`); testing requirements (pytest for
  `B2B_BE/`, Vitest+RTL if FE tests are written, happy-flow-only scope stated explicitly, FR-9/FR-18/
  FR-27 confirm-before-write and FR-26 conflict detection named as the testing priority); security
  baselines (phone-lookup-only auth stated plainly as not a real security boundary, role-scoped tool
  registries as the primary access-control mechanism, standard Pydantic input validation on tool
  arguments, env-var secrets handling); dependency policy (mature/boring libraries, no MCP SDK, no
  heavyweight agent framework).
- **`stack/rules/client-rules.md` seeded** with the standard starter template (Client Requirements /
  Organisation Conventions / Preferences / Overrides to Base Rules) — no client-specific requirement is
  on record yet for this pivot, so every section is left as placeholder guidance, not fabricated content.
  Owned by the user going forward; agents read it but never overwrite it.

## Failed / Unresolved
- Nothing failed in this pass. Architect-owned items are now resolved (see Completed above and
  stack-proposal.md §8/§11). The items below remain open for the **UX Designer** specifically — not
  something this PM pass, nor the Architect's stack-approval pass, was authorized to resolve:
  - Interaction design for the Booking Agent, Manager Agent, and Owner Dashboard, consistent with PRD §4
    and the locked stack (React+TypeScript, per `stack/rules/base-rules.md`).
  - Any UX implication of the now-resolved "web chat" frontend-technology decision (React, not
    Flutter-web, and the same technology as the Dashboard) — this was previously flagged to the UX
    Designer as pending on the Architect; it is no longer pending. The UX Designer can now design a single
    consistent web component/interaction language across the Web Chat widget and the Dashboard, since
    both are the same underlying technology.
  - Design implications of the confirmed SM-4a/SM-4b/SM-4c human-verification checkpoints (PRD §8): each
    is a UI moment requiring an explicit confirm/correct/override affordance before a write proceeds
    (mirrors FR-9/FR-18/FR-27 at the interaction level) — the UX Designer should treat these as first-class
    designed moments, not an afterthought bolted onto a generic chat bubble.
- No PM-owned or Architect-owned open question remains as of this handoff.

## Constraints
- `CLAUDE.md`'s `B2B_BE/` (backend) / `B2B_FE/` (frontend) top-level split is authoritative for all
  application code the Architect and Developer produce — this is fixed, not re-derived per ticket. See
  `CLAUDE.md` §"Repository layout" for the classify-before-writing rules both agents must follow once
  Phase 3/4/5 work touches actual code. `stack/rules/base-rules.md`'s enforced layout nests entirely
  within this split.
- This PRD is scoped to the 24-hour hackathon, happy-flow-only demo. Non-happy-path handling (ambiguous
  intent, zero availability, malformed input) is explicitly out of scope (PRD §5, §6.2) — the UX Designer
  should not design defensive/edge-case flows beyond what each FR's stated consequences require.
  `stack/rules/base-rules.md`'s Testing Requirements section states the same scope limit for whoever
  builds against the resulting designs.
- **`stack/rules/base-rules.md` is now locked.** It MUST NOT be edited without Architect sign-off recorded
  in its own frontmatter. `stack/rules/client-rules.md` is user-owned; agents read it but never overwrite
  it, and any conflict between it and `base-rules.md` is resolved in the client file's favor with the
  override documented there.
- Role-based permission enforcement (Owner/Admin vs. Staff vs. Customer) per PRD §4.2/§4.3 and the
  addendum.md §1 role matrix is a hard product constraint, not a UX suggestion — Ramesh cannot manage his
  own availability or act as a bookable provider (confirmed, PRD §9.1 Decision 1); Staff cannot access the
  catalog or dashboard; no one overrides another staff member's schedule. At the architecture level this
  is enforced via role-scoped tool registries (`stack/rules/base-rules.md`, Architecture Constraints) —
  the UX Designer should ensure no designed flow implies a role can reach a tool/action its registry would
  not expose.

## Decisions
- The three business decisions above (Ramesh's role, demo KPIs, human-verification moment(s)) were made
  by the user directly, not inferred or unilaterally resolved by the PM — see PRD §9.1 for the full
  record and every FR/section each one touches.
- The full stack decision (frontend, backend, database, mobile, infra, key libraries, agent-to-tool
  boundary, conflict-detection mechanism, session-state mechanism, repo-layout nesting) was made by the
  Architect in `stack/stack-proposal.md` and approved by the user at Gate 3 on 2026-09-17, unchanged. See
  stack-proposal.md for every decision's rationale and rejected alternatives.

## Evidence
- `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md` — the finalized PRD (`status:
  final`); primary input for both the Architect and the UX Designer.
- `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/.memlog.md` — chronological record of PRD
  drafting and the resolution of the three pending decisions.
- `bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/brief.md` and `addendum.md` —
  background source material for the PRD; the addendum's §1 (persona depth, role-permission matrix),
  §2 (technical considerations), §3 (risks), and §4 (assumptions/open-questions resolution log) remain
  the fullest record of context behind PRD §9.2's carried-forward architecture items.
- `stack/stack-proposal.md` (`status: approved`, Gate 3, 2026-09-17) — the full stack decision record,
  rationale, and rejected alternatives.
- `stack/rules/base-rules.md` (`status: approved`, 2026-09-17) — the locked coding rules the UX Designer
  and Developer agents build against.
- `stack/rules/client-rules.md` — seeded starter template; user-owned, currently empty of real content.
- `.orchestration/runs/planning-salon-app/artifacts/handoff-phase1-brief-to-pm.md` — the superseded
  Phase 1 → Phase 2 handoff, retained for trail continuity.
- `.orchestration/runs/planning-salon-app/run-record.md` — phase/gate history for this work.

## Next Action
- **UX Designer:** Start from PRD §2 (personas, journeys UJ-1–UJ-6) and §3 (glossary) to scope interaction
  design for the Booking Agent, Manager Agent, and read-only Dashboard — **design against the now-approved
  frontend stack in `stack/rules/base-rules.md`: React + TypeScript (Vite), one shared component/API-client
  layer across the Web Chat widget and the Dashboard.** Note the confirmed Decision 1 (Ramesh admin-only,
  not bookable) when designing the Manager Agent's conversation flows and the Dashboard's staff list
  (Ramesh is not listed as staff — PRD FR-19). The previously-open "web chat" frontend-technology question
  is resolved (React, same technology as the Dashboard, per stack-proposal.md §1) — no coordination with
  the Architect is needed on that point before finalizing web-chat interaction patterns. Treat the three
  confirmed human-verification checkpoints (PRD §8 SM-4a/b/c) as designed UI moments requiring an explicit
  confirm/correct/override affordance.
- **Architect's Phase 3 work is complete for this handoff's purposes** (stack proposed, approved, and
  locked into `stack/rules/base-rules.md`). Any further Architect involvement in this run is either a
  future ADR (if a locked decision needs reversing) or Developer-phase support if `base-rules.md` needs
  interpretation.

## Completion Condition
This handoff is satisfied once the UX Designer has produced (or confirmed no gap in) interaction designs
for the Booking Agent, Manager Agent, and Dashboard consistent with PRD §4's FRs, the three confirmed
decisions in §9.1, and the approved stack in `stack/rules/base-rules.md`.

## Escalation
No PM-owned or human-owned open question remains as of this handoff. The Architect-owned items previously
flagged as open have all been resolved and locked via Gate 3 approval (see Completed, Decisions above) —
none required escalation. Any future need to reverse a locked stack decision after downstream work has
started against it is an Architect escalation per that agent's contract (new ADR required, not a silent
edit to `base-rules.md`), not something this handoff anticipates being necessary right now.
