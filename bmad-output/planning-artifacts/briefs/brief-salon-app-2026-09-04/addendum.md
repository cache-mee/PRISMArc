---
title: "Addendum: Salon Time-Optimization Platform"
brief: brief.md
created: 2026-09-04
updated: 2026-09-04
---

# Addendum: Salon Time-Optimization Platform

*Supplementary depth for downstream agents (PRD, Architecture, UX). Not part of the brief narrative.*

---

## Persona Snapshots

**Priya, the time-strapped parent (Customer)**
Books haircuts for herself and two kids roughly every 4–6 weeks. Currently calls two different salons or waits 30+ minutes with children in tow. Wants one app to find a nearby salon, confirm it can handle all three without a long wait, and book it in one go.

**Ramesh, the salon owner (Salon Partner)**
Runs a 4-chair unisex salon with 3 staff. Currently manages bookings by phone and paper register — leading to double-bookings and idle chair time between appointments. Wants a simple way to show his real services/prices, keep staff schedules straight, and fill gaps in the day.

---

## Technical Considerations

*Starting points for the Architect phase — not commitments.*

- **Platforms:** Native or cross-platform mobile app (iOS/Android) for customers; web-based console (responsive, tablet/desktop) for salon owners
- **Two-sided real-time system:** backend must keep salon availability, staff schedules, and live queue state in sync in near-real-time so customers see accurate wait/availability
- **Scheduling/optimization engine:** designed as a distinct, independently testable service — core differentiator, must not be a bolt-on
- **Geolocation & maps:** required for location-based salon discovery and distance sorting
- **Notifications:** push/SMS for booking confirmations, reminders, and queue-position updates
- **Ratings/reviews:** moderated system tied to completed bookings (prevents fake reviews)
- **Queue visibility privacy:** "see other users' bookings" must surface only anonymized/aggregate queue information (e.g., "3 people ahead") — not other customers' personal details. Make explicit as a non-functional requirement in the PRD.

---

## Risks & Open Questions

| Risk / Question | Notes |
|---|---|
| **Two-sided cold start** | Customers need enough salons to find value; salons need enough customer demand to maintain the console. Needs explicit go-to-market sequencing strategy. |
| **Data accuracy dependency** | Core value proposition (accurate wait/time estimates) depends on salons keeping staff availability and service durations current. Stale data undermines trust quickly. |
| **Walk-ins vs. bookings conflict** | Salons that continue accepting walk-ins alongside app bookings could break the app's time estimates. Needs a defined policy or reconciliation mechanism. |
| **Average cutting time bootstrapping** | Should derive from historical completed-booking data per salon/staff/service — but there's no historical data at launch. How does the system bootstrap accurate estimates? |
| **Optimization scope for MVP** | How much scheduling intelligence is realistic to ship in v1 versus a simple heuristic? Technically the hardest part of the product — phasing must be deliberate. |
| **Monetization model** | Undecided. Likely candidates: commission-per-booking, salon subscription fees, featured-placement/advertising. Choice affects what features salons expect for free vs. paid. |
| **Launch geography & onboarding** | No confirmed launch geography or initial salon-acquisition strategy (how first salons are onboarded to solve cold-start). |
| **Budget, timeline, team size** | Not confirmed at time of brief formalization. |

---

## Confirmed Assumptions (to resolve during PRD elicitation)

- Initial geographic launch market not specified
- Salon size scope (independent vs. chain) not specified
- Whether barbershops/unisex salons/spas are MVP scope or only hair salons not specified
- In-app payments out of MVP scope (pay-at-salon assumed — confirm)
- Advanced multi-person/multi-service optimizer phased post-MVP (confirm phasing boundary)
- No confirmed monetization model

---

## Next Steps for Agentic SDLC

1. **PM Agent (John):** Use brief + addendum to produce a PRD with functional requirements grouped by persona (Customer, Salon Partner). Resolve all `[ASSUMPTION]` items through clarifying questions.
2. **UX Agent (Sally):** Design two distinct flows — Customer discovery-to-booking flow, and Salon Partner console — plus queue-visibility UI respecting the privacy note above.
3. **Architect Agent (Winston):** Design system architecture with scheduling/optimization engine as a distinct, independently evolvable service. Define data model for services, staff, availability, and bookings. Break PRD into epics and stories.
4. **Dev Agent:** Implement epics/stories starting with MVP core (discovery, catalog, basic booking) before the advanced multi-person/multi-service optimizer, per phased approach.
