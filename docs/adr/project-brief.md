# Project Brief: Salon Time-Optimization Platform

## Document Purpose

This brief is written as input to the BMAD Product Manager agent (John) for PRD generation, and downstream to the Architect, UX, and Development agents across the SDLC. It captures the problem, the proposed two-sided solution, target users, MVP scope, and known open questions. Sections marked **[ASSUMPTION]** are inferred, not confirmed by the founder, and should be validated or corrected during PRD elicitation — they are flagged rather than silently baked in.

---

## 1. Executive Summary

The product is a two-sided marketplace app that makes salon visits **predictable, coordinated, and time-efficient**. Unlike existing salon booking apps, which only reserve an individual time slot, this platform optimizes the *entire visit* — the combination of services, providers, family members, and available time slots — so customers spend less time waiting and salons run a tighter, more predictable schedule. The platform has two connected experiences: a **Customer app** for discovering salons and booking optimized visits, and a **Salon Partner console** for owners to manage their services, staff, pricing, and schedule.

## 2. Problem Statement

Time is one of the most valuable and limited resources people have, yet salon visits often consume far more of it than necessary. Customers routinely lose time to:

- Waiting at the salon for a walk-in slot or a delayed appointment
- Coordinating multiple, separate bookings for different services (e.g., haircut + coloring) or for multiple family members
- Making repeat trips because a salon didn't have everything needed in one visit
- Guessing which nearby salon actually has availability, reasonable pricing, and a manageable queue right now

Existing salon booking apps solve the narrow problem of "reserve a slot," but none of them optimize the *whole visit* — they don't reason about service duration, provider availability, family/group coordination, or real-time queue state together to minimize the customer's total time spent.

On the supply side, salon owners lack simple digital tools to represent their real service catalog, pricing, staff, and live schedule in a way that a smart booking system can use — most run on paper registers, phone bookings, or generic calendar tools not built for multi-chair, multi-service scheduling.

## 3. Proposed Solution

A mobile-first, two-sided platform:

1. **Customer side** — discover salons near a chosen location, compare them on distance, average service time, and price range, view a detailed service/price list and ratings, then book an optimized slot (or combination of slots/services) with minimal wait.
2. **Salon Partner side** — salon owners maintain their profile, service catalog and pricing, offers/discounts, staff roster, and live availability, and manage incoming bookings from a dashboard.

The core differentiator is the **scheduling intelligence layer**: rather than just checking "is 3pm free," the system reasons about service combinations, staff/provider specialization, per-service duration history, and current queue load to recommend the visit plan that minimizes the customer's total time — including for multi-service and multi-person (family) bookings. This intelligence layer is the platform's long-term moat and should be treated as a first-class system, not a bolt-on feature, from the Architecture phase onward.

## 4. Target Users

### Primary segment — Customers
Time-conscious individuals and families who get salon/grooming services regularly (haircuts, coloring, styling, grooming, etc.) and want to minimize time spent waiting or coordinating, including people booking on behalf of a family (e.g., booking for themselves and their children/spouse in one coordinated visit).

### Secondary segment — Salon Owners / Managers
Independent salons and small salon chains who want better chair/staff utilization, fewer scheduling conflicts, visibility into their booking pipeline, and a channel to advertise offers and discounts to attract and retain customers.

**[ASSUMPTION]** Initial geographic launch market, salon size (independent vs. chain), and whether barbershops/unisex salons/spas are all in scope or only a subset, are not yet specified and should be confirmed with the founder before PRD elicitation.

## 5. Goals & Success Metrics

### Business Objectives
- Achieve a critical mass of salons in a launch area sufficient for customers to reliably find options nearby (two-sided marketplace liquidity)
- Demonstrate measurable reduction in customer time-per-visit (wait + coordination time) versus walk-in or single-slot booking
- Convert salon partners from manual/phone-based booking to the platform's schedule management tools

### User Success Metrics
- Reduced average wait time at the salon versus a walk-in or a naively booked appointment
- Ability to complete a multi-service or multi-family-member visit in a single coordinated trip
- Confidence in choosing a salon before arriving (via transparent pricing, ratings, and expected duration)

### Key Performance Indicators (KPIs) **[ASSUMPTION — targets to be set with founder]**
- Average customer wait time per visit (minutes)
- % of bookings that are multi-service or multi-person (a proxy for the optimization feature's usage)
- Booking completion rate (slot picked → visit completed, low no-show/cancellation rate)
- Salon partner retention / active-salon rate month over month
- Customer repeat-booking rate and average rating submitted

## 6. MVP Scope

### 6.1 Core Features — Customer App (Must Have)
- **Location selection** — set or detect a location to search around
- **Salon discovery list** — salons sorted by distance, average service/cutting time, and price range, with filtering
- **Salon detail view** — full service list with costs, salon info, ratings/reviews
- **Slot booking** — pick a service (or combination of services) and an available time slot
- **Visibility into current load** — see other users' bookings/queue status at a salon to gauge expected wait before booking
- **Ratings & reviews** — view existing ratings; submit a rating/review after a visit
- **Booking management** — view, reschedule, or cancel an upcoming booking

### 6.2 Core Features — Salon Partner Console (Must Have)
- **Salon profile management** — name, location, hours, contact/business details
- **Service & pricing catalog** — add/edit/remove services and their costs
- **Offers & discounts management** — create and manage promotions
- **Staff management** — add/edit salon staff ("salon guys"), their specialties/services offered, and availability
- **Schedule/time management** — configure working hours, staff shift availability, and slot durations
- **Booking dashboard** — view incoming bookings, current queue, and upcoming schedule

### 6.3 Out of Scope for MVP **[ASSUMPTION — confirm with founder]**
- In-app payments / point-of-sale integration (assume pay-at-salon for MVP)
- Multi-location chain management tools (assume single-location salon accounts for MVP)
- Loyalty/rewards programs beyond basic ratings
- Marketing automation or push-campaign tooling for salons
- Inventory/product management for salons
- The full scheduling-optimization engine in its most advanced form (multi-person, multi-service, cross-provider optimization) may be phased — an MVP version could start with single-service, single-person smart slot suggestions and grow from there. To be scoped with the PM/Architect.

### 6.4 MVP Success Criteria
The MVP is successful if customers in the launch area can find a salon, see accurate pricing and expected wait, book a visit, and complete it with measurably less friction than calling or walking in — and salon partners can run their day-to-day booking operations from the console without reverting to phone/paper.

## 7. Post-MVP Vision

- Full multi-service, multi-provider, multi-person scheduling optimizer that computes the best combination of services/providers/time slots to minimize total visit time for a whole family or group booking in one trip
- Dynamic/demand-based scheduling suggestions (e.g., recommend off-peak slots)
- In-app payments, tipping, and receipts
- Loyalty programs and personalized offers
- Support for salon chains with multiple branches under one owner account
- Predictive wait-time estimates using historical service-duration data per staff member
- Expansion beyond salons to adjacent appointment-based services (spas, barbershops, grooming, etc., if not already included in MVP)

## 8. Technical Considerations

**[ASSUMPTION — all items in this section are starting points for the Architect phase, not commitments]**

- **Platforms:** Native or cross-platform mobile app (iOS/Android) for customers; a web-based console (responsive, usable on tablet/desktop) for salon owners, since they'll manage it from the shop
- **Two-sided real-time system:** requires a backend that keeps salon availability, staff schedules, and live queue state in sync in near-real-time so customers see accurate wait/availability
- **Scheduling/optimization engine:** a distinct service responsible for computing recommended slots/combinations — should be designed as a separate, testable component given it's the core differentiator
- **Geolocation & maps:** needed for location-based salon discovery and distance sorting
- **Notifications:** push/SMS for booking confirmations, reminders, and queue-position updates
- **Ratings/reviews:** standard moderated review system tied to completed bookings (to prevent fake reviews)
- **Data privacy note:** "see bookings of other users" (Section 6.1) should surface only anonymized/aggregate queue information (e.g., "3 people ahead"), not other customers' personal details — to be made explicit as a non-functional requirement in the PRD

## 9. Constraints & Assumptions

- No confirmed budget, timeline, or team size at the time of writing **[ASSUMPTION]**
- No confirmed monetization model — likely candidates are commission-per-booking, salon subscription fees, or featured-placement/advertising for salons, but none is chosen **[ASSUMPTION]**
- No confirmed launch geography or initial salon-acquisition strategy (how the first salons are onboarded to solve the cold-start problem) **[ASSUMPTION]**
- Assumes salon owners are willing and able to keep digital schedules/staff availability accurate and up to date, since the optimization quality depends on good input data

## 10. Risks & Open Questions

- **Two-sided cold start:** customers need enough salons to find value; salons need enough customer demand to bother maintaining the console. Needs an explicit go-to-market sequencing strategy.
- **Data accuracy dependency:** the core value proposition (accurate wait/time estimates) depends entirely on salons keeping staff availability and service durations current; stale data undermines trust quickly.
- **Walk-ins vs. bookings conflict:** salons that continue accepting walk-in customers alongside app bookings could break the app's time estimates; needs a defined policy or reconciliation mechanism.
- **"Average cutting time" definition:** should be derived from historical completed-booking data per salon/staff/service rather than a fixed estimate — but there's no historical data at launch (bootstrapping problem).
- **Privacy of queue visibility:** showing "other users' bookings" must be handled carefully (see Section 8).
- **Monetization and pricing model:** undecided, and will affect what features salons expect for free vs. paid.
- **Optimization scope for MVP:** how much of the "best combination of services/providers/time" intelligence is realistic to ship in v1 versus a simpler heuristic, given it's technically the hardest part of the product.

## 11. Appendix — Persona Snapshots

**Customer persona (working name: "Priya, the time-strapped parent"):** Books haircuts for herself and two kids roughly every 4-6 weeks. Currently calls two different salons or waits 30+ minutes with children in tow. Wants one app to find a nearby salon, see it can handle all three of them without a long wait, and book it in one go.

**Salon Partner persona (working name: "Ramesh, the salon owner"):** Runs a 4-chair unisex salon with 3 staff. Currently manages bookings by phone and a paper register, leading to double-bookings and idle chair time between appointments. Wants a simple way to show his real services/prices, keep his staff's schedules straight, and fill gaps in the day.

## 12. Next Steps for the Agentic SDLC

1. **PM Agent (John):** Use this brief to produce a PRD with functional requirements grouped by the two personas (Customer, Salon Partner), explicitly resolving the "[ASSUMPTION]" items above through clarifying questions where possible.
2. **UX Agent (Sally):** Design two distinct flows/experiences — the Customer discovery-to-booking flow and the Salon Partner console — plus the queue-visibility UI that respects the privacy note in Section 8.
3. **Architect Agent (Winston):** Design the system architecture with the scheduling/optimization engine as a distinct, independently evolvable service; define the data model for services, staff, availability, and bookings that the optimizer depends on; break the PRD into epics and stories.
4. **Dev Agent (Amelia):** Implement epics/stories, starting with the MVP core (discovery, catalog, basic booking) before the advanced multi-person/multi-service optimizer, per the phased approach noted in Section 6.3.
