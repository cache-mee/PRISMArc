# Handoff

## Work ID
pm-prd-2026-09-05

## Objective
Produce a complete, implementable PRD for the Salon Time-Optimization Platform that the Architect and UX Designer agents can act on without ambiguity.

## Acceptance Criteria
1. PRD file exists at `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-05/prd.md`.
2. Every functional requirement is written as "The system shall..." or "The user can..." and is independently testable.
3. No [ASSUMPTION] tags remain in the PRD — all five founder-resolved assumptions are recorded as decisions.
4. Queue visibility privacy is an explicit NFR (NFR-PRIV-01, NFR-PRIV-02, NFR-PRIV-03).
5. Slot suggestion engine MVP scope (free/busy, single service) is clearly separated from post-MVP optimization scope.
6. Every requirement cites its source brief section or resolved assumption.

## Current State
PRD is complete and written to disk. No application source code exists in the repository. Branch: `feature/bmad-setup`. No code changes were made — only planning artifacts were written.

## Completed
- Read all source documents: `bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-04/brief.md`, `addendum.md`, and `docs/adr/project-brief.md`.
- Produced PRD at `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-05/prd.md`.
- All five founder-resolved assumptions are recorded as decisions in Section 10 (Resolved — Not Open).
- All requirements are traceable to source in Appendix A.
- Queue visibility privacy is explicit in NFR-PRIV-01 through NFR-PRIV-03 and FR-C-DET-03.
- MVP slot suggestion engine scope is defined in Section 5.1 and FR-C-BOOK-01 through FR-C-BOOK-07; post-MVP optimization is in Section 5.3.

Evidence note: PRD production is a design/writing task. No deterministic validation (test run, compile, lint) is applicable. This record is labelled a **judgement**: the PRD was reviewed against the brief sources and resolved assumptions before writing; no automated check exists to validate requirement completeness. Human review remains the gate for PRD approval.

## Failed / Unresolved
None. PRD is complete per the inputs provided.

Requirements that remain open (all logged in PRD Section 10 — Open Questions and Deferred Decisions):

- Staff assignment to bookings at booking time vs. service time (Architect to resolve).
- Slot computation caching strategy (Architect to resolve).
- Concurrency control mechanism for booking (Architect to resolve).
- Authentication method selection: OTP-SMS, email/password, or both (Architect to resolve).
- Notification delivery channel: push, SMS, email (Architect to resolve).
- Minimum TLS version (Architect to resolve).
- Walk-in reconciliation policy (Founder to decide).
- Service duration bootstrapping policy (Founder to decide).
- Go-to-market and cold-start strategy (Founder to decide).
- KPI numeric targets (Founder to decide).
- Review moderation policy beyond attribution anonymization (Founder to decide).
- Data residency and regulatory compliance for launch jurisdiction (Founder to decide + legal review).

None of these block Architect or UX Designer from beginning MVP-core work.

## Constraints
- Scope: planning artifacts only. No application code was touched or created.
- INR is the fixed currency. No currency abstraction.
- Single city, single locale, single salon location per partner account.
- No in-app payments, no PCI scope.
- MVP booking: single service per booking, free/busy slot suggestion only.
- Monetization is deferred — no monetization requirement in PRD.
- PRD MUST NOT contain [ASSUMPTION] tags.

## Decisions
- All five founder-resolved assumptions (launch geography, salon types, optimization scope, monetization, payments) are treated as decisions and recorded in PRD Section 10 (Resolved — Not Open). They are not re-opened.
- Staff_id on Booking is nullable in the data model. The question of whether bookings are assigned to a specific staff member at booking time is explicitly passed to the Architect as an open question — it was not resolved in the PRD.
- Slot is defined as computed (not persisted) in the data model. The Architect defines the algorithm and caching.
- Rating attribution uses "Verified customer" rather than a customer's full name (FR-C-RAT-05), consistent with queue visibility privacy policy.
- Offers are informational in MVP (FR-P-OFFER-04). No automatic discount application.

## Evidence
- `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-05/prd.md` — the PRD artifact. Existence on disk is verifiable. Content correctness relative to sources is a judgement, not deterministic evidence.
- Source documents read and used: `bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-04/brief.md`, `bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-04/addendum.md`, `docs/adr/project-brief.md`.

## Next Action

### Architect agent
Read `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-05/prd.md` in full. Begin with:
1. Resolve the staff assignment question (PRD Section 10, "Staff assignment to bookings") — this directly affects whether slot computation is per-salon or per-staff, which is the first architectural fork.
2. Define the concurrency control mechanism for FR-C-BOOK-07 (no double-booking).
3. Design the slot suggestion engine as a distinct, independently testable service (referenced in addendum.md Technical Considerations and PRD Section 5.1).
4. Produce the authoritative data schema, beginning from the conceptual model in PRD Section 9.
5. Break the PRD into epics and stories for the Developer agent.

### UX Designer agent
Read `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-05/prd.md` in full. Begin with:
1. Design the Customer discovery-to-booking flow (FR-C-LOC, FR-C-DISC, FR-C-DET, FR-C-BOOK).
2. Design the queue visibility UI for FR-C-DET-03 — anonymized count only, no personal data. NFR-PRIV-01 and NFR-PRIV-02 are hard constraints, not design options.
3. Design the Salon Partner console (FR-P-PROF through FR-P-DASH). Console must be usable on tablet and desktop.

## Completion Condition
This handoff is complete when both the Architect and UX Designer agents have acknowledged receipt of the PRD, confirmed it is sufficient to begin their respective work, and produced their first output artifact. If either agent finds the PRD insufficient for a specific requirement area, they should note the gap and escalate rather than filling it themselves.

## Escalation
The following require human (founder) decisions before the PRD can be updated or requirements can be added:
- Walk-in reconciliation policy.
- Service duration bootstrapping policy.
- Go-to-market and cold-start strategy.
- KPI numeric targets.
- Review moderation scope beyond FR-C-RAT-05.
- Data residency and regulatory compliance determination for the launch jurisdiction.

Any scope expansion beyond what is defined in PRD Section 5.1 (In Scope MVP) requires explicit human approval and a PRD update before the Architect or Developer may implement it.
