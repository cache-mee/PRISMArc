---
title: "PRD: Salon Time-Optimization Platform"
version: "1.1"
status: "approved — ready for Architect and UX Designer"
created: 2026-09-05
revised: 2026-09-04
revision-note: "v1.1 — Salon Partner surface changed from web console to mobile app (iOS and Android). Founder decision."
source-brief: "bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-04/brief.md"
source-addendum: "bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-04/addendum.md"
source-detailed-brief: "docs/adr/project-brief.md"
---

# PRD: Salon Time-Optimization Platform

---

## 1. Overview

The Salon Time-Optimization Platform is a two-sided mobile-first marketplace that makes salon visits predictable and time-efficient for customers, and operationally manageable for salon owners. Customers discover nearby salons, see real pricing and live queue state, and book a confirmed slot. Salon partners manage their profile, service catalog, staff roster, and live schedule from a mobile app (iOS and Android).

The platform launches in a single city, single locale, with pricing denominated in INR. No multi-region, multi-language, or multi-timezone logic is included in MVP.

**Monetization** is deferred entirely post-MVP. Candidates are booking commission or salon SaaS subscription. No monetization requirement appears in this document.

---

## 2. Problem Statement

Source: project-brief.md §2, brief.md executive summary

Time-conscious customers lose time to:

1. Waiting at a salon for a walk-in slot or a delayed appointment.
2. Coordinating separate bookings for different family members across potentially multiple salons.
3. Guessing which nearby salon has genuine availability and fair pricing at any given moment.
4. Making repeat trips because a chosen salon could not fulfil the visit as expected.

Salon owners, especially independent single-location operators, lack simple digital tools to represent their real service catalog, staff availability, and live schedule in a way that allows a booking system to show accurate availability to customers. Most operate on phone bookings and paper registers, leading to double-bookings and idle chair time.

---

## 3. Goals and Success Metrics

Source: project-brief.md §5

### Business Goals

- Achieve two-sided marketplace liquidity in the launch city: enough salons that customers reliably find nearby options; enough customer demand that salon partners maintain the app actively.
- Demonstrate measurable reduction in customer time-per-visit (wait plus coordination) versus walk-in or unoptimized booking.
- Convert salon partners from manual or phone-based booking to platform-managed scheduling.

### User Success Metrics

| Metric | Definition |
|---|---|
| Average customer wait time per visit (minutes) | Time between scheduled slot and service start, captured at visit completion |
| Booking completion rate | Bookings that result in a completed visit divided by all confirmed bookings |
| Salon partner active retention (monthly) | % of onboarded salons that processed at least one booking in the calendar month |
| Customer repeat-booking rate | % of customers who made a second booking within 60 days of their first |
| Customer review submission rate | % of completed visits that result in a submitted rating |

KPI targets are not set in this document. Targets are a founder decision, recorded separately, and do not block implementation.

---

## 4. Personas

Source: project-brief.md §11, addendum.md Persona Snapshots

### 4.1 Customer — Priya

Priya is a time-strapped parent who books haircuts for herself and two children approximately every four to six weeks. Her current experience involves calling two different salons or arriving and waiting thirty or more minutes with children. Her core need is a single app that lets her find a nearby salon, confirm it can serve all three of them without a long wait, and complete the booking in one interaction.

**Primary jobs to be done:**

- Discover nearby salons and compare them on distance, expected service time, and price.
- See a salon's real service list and pricing before committing.
- Book a confirmed slot for one service at a time (MVP).
- Know how busy a salon is before arriving so she can plan the trip.
- Leave a rating after the visit.

**Pain points the MVP must address:**

- Uncertainty about whether a salon has availability without calling ahead.
- No reliable estimate of how long the visit will actually take.
- Managing a booking (viewing, rescheduling, cancelling) through one interface.

### 4.2 Salon Partner — Ramesh

Ramesh runs a four-chair unisex salon with three staff. He currently manages bookings by phone and a paper register, leading to double-bookings and idle chair time between appointments. His core need is a simple way to present his real services and prices, keep staff schedules accurate, and see his day's bookings at a glance — all from a mobile app he can use on the go or at the front desk.

**Primary jobs to be done:**

- Create and maintain the salon's public profile.
- Define services, durations, and prices.
- Manage staff and their working hours.
- See incoming bookings in one dashboard without needing to cross-reference a paper log.
- Create occasional promotional offers.

**Pain points the MVP must address:**

- Double-bookings caused by manual coordination.
- Idle time caused by no-shows or last-minute gaps the salon cannot fill.
- No digital channel to show accurate pricing to prospective customers.

---

## 5. Scope

### 5.1 In Scope (MVP)

**Customer app (mobile — iOS and Android):**

- Location selection for discovery.
- Salon discovery list with distance, average service time, and price range.
- Salon detail view: service catalog, pricing, ratings, live queue state.
- Single-service slot booking (one service per booking session).
- Booking management: view, reschedule, cancel.
- Live queue visibility (anonymized aggregate only — see Section 8).
- Rating and review submission (tied to completed bookings only).

**Salon Partner app (mobile — iOS and Android):**

- Salon profile management.
- Service and pricing catalog management.
- Offers and discounts management.
- Staff management: add/edit staff, services each staff member can perform, and their working hours.
- Schedule configuration: salon operating hours, staff shift availability, and service slot durations.
- Booking dashboard: incoming bookings, current queue, and upcoming schedule.

**Slot suggestion engine (MVP scope only):**

- Given a customer's chosen salon and chosen single service, the system computes available slots from salon operating hours minus existing bookings (free/busy logic).
- No multi-service sequencing, no multi-staff optimization, no travel or ETA logic.

### 5.2 Out of Scope (MVP)

- In-app payments, PCI compliance, or any payment gateway integration. All transactions are pay-at-salon.
- Multi-service bundled bookings (one service per booking in MVP).
- Multi-person (family/group) bookings as a single coordinated transaction.
- Multi-location chain management. All salon accounts are single-location in MVP.
- Loyalty or rewards programs.
- Marketing automation or push-campaign tools for salons.
- Inventory or product management for salons.
- Advanced multi-service, multi-provider, or multi-person scheduling optimizer.
- Dynamic or demand-based slot pricing suggestions.
- Predictive wait-time estimates using historical per-staff duration data.

### 5.3 Future (Post-MVP)

- Full multi-service, multi-provider, multi-person scheduling optimizer: compute the optimal combination of services, providers, and time slots to minimize total visit time for a group booking.
- Predictive wait-time estimates using per-staff historical service-duration data accumulated on the platform.
- Dynamic scheduling suggestions (recommend off-peak slots to reduce wait).
- In-app payments, tipping, and digital receipts.
- Loyalty programs and personalized offers.
- Multi-branch chain management under one salon owner account.
- Expansion beyond salons to adjacent appointment-based services (spas, clinics, grooming).

---

## 6. Functional Requirements — Customer App

Requirements are grouped by feature area. "Shall" denotes a mandatory system behavior. "Can" denotes a capability the user has. Each requirement is independently testable.

### 6.1 Location Selection

**FR-C-LOC-01:** The system shall allow the user to grant device location permission, and when granted, shall automatically populate the search location with the user's current coordinates.

**FR-C-LOC-02:** The user can manually enter or select a location to use as the search center instead of, or in place of, their device location.

**FR-C-LOC-03:** The system shall store the most recently used search location and pre-populate it on the next session, until the user changes it.

Source: project-brief.md §6.1 "Location selection"; addendum.md Technical Considerations "Geolocation and maps"

### 6.2 Salon Discovery

**FR-C-DISC-01:** The system shall display a list of salons within a configurable radius of the selected search location, sorted by distance (nearest first) by default.

**FR-C-DISC-02:** The user can re-sort the discovery list by average service time (lowest first) or by starting price (lowest first).

**FR-C-DISC-03:** The system shall display for each salon in the list: salon name, distance from the search location, starting price (lowest service price in the catalog), and average service duration.

**FR-C-DISC-04:** The system shall display a current load indicator for each salon in the list (for example: "quiet", "moderate", "busy") derived from the count of active bookings relative to available capacity. The indicator MUST NOT reveal any individual customer's identity or booking details.

**FR-C-DISC-05:** The user can apply filters to the discovery list. Filters available at MVP: maximum distance, maximum price, and minimum average rating.

**FR-C-DISC-06:** The system shall display an empty state with explanatory text when no salons match the current search location and applied filters.

Source: project-brief.md §6.1 "Salon discovery list"; project-brief.md §3

### 6.3 Salon Detail View

**FR-C-DET-01:** The user can navigate from any salon in the discovery list to that salon's detail view.

**FR-C-DET-02:** The salon detail view shall display: salon name, address, operating hours, contact information (as provided by the salon partner), full service catalog with service name, duration, and price for each service, average rating, and total review count.

**FR-C-DET-03:** The salon detail view shall display a live queue state indicator showing the current number of people in the queue or ahead in the schedule, expressed as an anonymized count (for example: "3 people ahead"). The indicator MUST NOT display any other customer's name, booking time, or personal information.

**FR-C-DET-04:** The salon detail view shall display all active offers and discounts currently configured by the salon partner.

**FR-C-DET-05:** The salon detail view shall display existing customer ratings and reviews for the salon, most recent first.

Source: project-brief.md §6.1 "Salon detail view"; addendum.md "Queue visibility privacy"

### 6.4 Slot Booking

**FR-C-BOOK-01:** The user can select one service from the salon's catalog and proceed to book a slot at that salon.

**FR-C-BOOK-02:** The system shall display only available (unbooked) time slots for the selected service, computed from the salon's operating hours minus all existing bookings for that service's required duration.

**FR-C-BOOK-03:** The system shall not display or offer a time slot that conflicts with an existing booking or falls outside the salon's configured operating hours.

**FR-C-BOOK-04:** The user can select one available time slot and confirm the booking.

**FR-C-BOOK-05:** Upon booking confirmation, the system shall send the customer a booking confirmation notification (push notification and/or SMS) containing: salon name, service name, date, time, and a booking reference identifier.

**FR-C-BOOK-06:** Upon booking confirmation, the system shall record the booking in the salon partner's booking dashboard and reduce available slots accordingly for other customers viewing that salon.

**FR-C-BOOK-07:** The system shall prevent double-booking: if two customers attempt to book the same slot concurrently, only one booking shall succeed. The other customer shall receive an error and be prompted to select a different slot.

**FR-C-BOOK-08:** The payment method for all bookings is pay-at-salon. The system shall not collect, process, or store any payment card information.

Source: project-brief.md §6.1 "Slot booking"; resolved assumption #3 (single service, free/busy slot suggestion); resolved assumption #5 (no in-app payments)

### 6.5 Booking Management

**FR-C-MGT-01:** The user can view a list of all their upcoming and past bookings in the app.

**FR-C-MGT-02:** Each booking in the list shall display: salon name, service, date, time, booking status (confirmed, cancelled, completed), and booking reference.

**FR-C-MGT-03:** The user can cancel an upcoming booking. On cancellation, the system shall mark the booking as cancelled, release the slot for other customers, and send a cancellation notification to the customer and the salon partner.

**FR-C-MGT-04:** The user can reschedule an upcoming booking by selecting a different available slot at the same salon for the same service. Rescheduling shall behave identically to a new booking for slot-conflict purposes.

**FR-C-MGT-05:** The system shall send the customer a reminder notification a configurable time before their scheduled booking (default: 24 hours before).

Source: project-brief.md §6.1 "Booking management"; addendum.md "Notifications"

### 6.6 Ratings and Reviews

**FR-C-RAT-01:** The system shall prompt the customer to submit a rating and optional written review after a booking is marked as completed by the salon partner.

**FR-C-RAT-02:** The customer can submit a rating on a 1-to-5 star scale, with an optional written review up to 500 characters.

**FR-C-RAT-03:** The system shall allow only one rating per booking. A customer cannot submit a second rating for the same booking.

**FR-C-RAT-04:** The system shall not permit a customer to submit a rating for a booking that is not in a completed state.

**FR-C-RAT-05:** Submitted ratings shall appear on the salon's detail view, attributed to "Verified customer" rather than the customer's full name, to protect privacy.

**FR-C-RAT-06:** The system shall compute and display the salon's average rating to one decimal place, based on all submitted ratings for that salon.

Source: project-brief.md §6.1 "Ratings and reviews"; addendum.md "Ratings/reviews — moderated system tied to completed bookings"

### 6.7 Authentication and Account

**FR-C-AUTH-01:** The user must create an account to make or manage a booking. Browsing the salon discovery list and salon detail view does not require an account.

**FR-C-AUTH-02:** The system shall authenticate customers using a phone-number-based flow (OTP via SMS) or email and password. The specific method is a decision for the Architect; this requirement states that at least one of these two methods must be supported.

**FR-C-AUTH-03:** The system shall associate all bookings, booking history, and submitted ratings with the authenticated customer account.

Source: implied by booking management (FR-C-MGT-01–05) and rating moderation (FR-C-RAT-03–04); addendum.md "Ratings/reviews — moderated system"

---

## 7. Functional Requirements — Salon Partner App

Requirements are grouped by feature area. The Salon Partner app is a native mobile app (iOS and Android), touch-first. "Shall" denotes a mandatory system behavior. "Can" denotes a capability the user has. Each requirement is independently testable.

### 7.1 Authentication and Account

**FR-P-AUTH-01:** The salon partner must authenticate to access the app. The system shall support email and password authentication for salon partner accounts.

**FR-P-AUTH-02:** A salon partner account corresponds to exactly one salon location. Multi-location accounts are not supported in MVP.

Source: resolved assumption #2 (generic Business model, single location); project-brief.md §6.2

### 7.2 Salon Profile Management

**FR-P-PROF-01:** The salon partner can create and edit the salon's public profile from within the mobile app. Profile fields: salon name, street address, city, phone number, operating hours (open and close time per day of the week, with ability to mark days as closed).

**FR-P-PROF-02:** The system shall validate that operating hours are internally consistent (close time is after open time for any day marked as open) and shall reject the save with an explanatory error message if validation fails.

**FR-P-PROF-03:** Changes saved to the salon profile shall be reflected in the customer-facing discovery list and detail view within 60 seconds of saving.

Source: project-brief.md §6.2 "Salon profile management"; resolved assumption #1 (single city, single locale, INR)

### 7.3 Service and Pricing Catalog

**FR-P-SVC-01:** The salon partner can add a service to the catalog using a mobile form. Required fields: service name, duration in minutes (positive integer), price in INR (positive value).

**FR-P-SVC-02:** The salon partner can edit any field of an existing service.

**FR-P-SVC-03:** The salon partner can remove a service from the catalog. Removing a service shall not cancel existing confirmed bookings for that service; those bookings shall remain and be fulfilled.

**FR-P-SVC-04:** The system shall require at least one service in the catalog for the salon's profile to be visible to customers in the discovery list.

**FR-P-SVC-05:** All prices in the catalog shall be stored and displayed in INR.

Source: project-brief.md §6.2 "Service and pricing catalog"; resolved assumptions #1 (INR), #2 (generic services array)

### 7.4 Offers and Discounts

**FR-P-OFFER-01:** The salon partner can create an offer from within the mobile app. Required fields: offer title, description (free text), and an optional expiry date. Optional fields: discount amount or percentage off a named service.

**FR-P-OFFER-02:** The salon partner can edit or delete an active offer.

**FR-P-OFFER-03:** The system shall display active (non-expired) offers on the salon's customer-facing detail view. Expired offers shall not appear to customers.

**FR-P-OFFER-04:** Offers are informational at MVP. The system shall not automatically apply a discount to a booking's price calculation. The salon partner applies any discount at the point of payment (pay-at-salon).

Source: project-brief.md §6.2 "Offers and discounts"; resolved assumption #5 (no in-app payments)

### 7.5 Staff Management

**FR-P-STAFF-01:** The salon partner can add a staff member using a mobile form. Required fields: name, list of services the staff member is qualified to perform (selected from the salon's service catalog).

**FR-P-STAFF-02:** The salon partner can edit a staff member's name or list of qualified services.

**FR-P-STAFF-03:** The salon partner can remove a staff member. Removing a staff member shall not cancel existing confirmed bookings already assigned to that staff member.

**FR-P-STAFF-04:** The salon partner can configure working hours for each staff member using touch controls: for each day of the week, the staff member's start time, end time, or mark as not working. Staff working hours must fall within the salon's operating hours.

**FR-P-STAFF-05:** The system shall validate that a staff member's working hours do not extend beyond the salon's configured operating hours, and shall reject the save with an error if they do.

Source: project-brief.md §6.2 "Staff management"

### 7.6 Schedule Configuration

**FR-P-SCHED-01:** The salon partner can configure service slot duration (in minutes) per service, separate from the service's listed duration. This allows buffer time between appointments.

**FR-P-SCHED-02:** The slot suggestion engine shall use slot duration (not service duration alone) when computing available slots for customer booking.

**FR-P-SCHED-03:** The salon partner can view the current day's schedule as a timeline of confirmed bookings across all staff, displayed in the mobile app's booking dashboard.

Source: project-brief.md §6.2 "Schedule/time management"; resolved assumption #3 (free/busy slot suggestion)

### 7.7 Booking Dashboard

**FR-P-DASH-01:** The salon partner can view all upcoming bookings for the salon from the mobile app, filterable by date and by staff member.

**FR-P-DASH-02:** Each booking in the dashboard shall display: customer name (as entered at account creation), service, scheduled date and time, booking status, and booking reference.

**FR-P-DASH-03:** The salon partner can mark a booking as completed using a touch action. Only confirmed bookings can be marked completed.

**FR-P-DASH-04:** The salon partner can mark a booking as a no-show using a touch action. A no-show booking shall release the slot (it does not count against available capacity going forward) and shall not trigger a review prompt for the customer.

**FR-P-DASH-05:** The system shall send the salon partner a push notification when a new booking is confirmed for their salon.

**FR-P-DASH-06:** The system shall send the salon partner a push notification when a customer cancels a booking, allowing the slot to be filled.

Source: project-brief.md §6.2 "Booking dashboard"; addendum.md "Notifications"

---

## 8. Non-Functional Requirements

### 8.1 Queue Visibility Privacy (Explicit)

**NFR-PRIV-01:** The system shall never expose any individual customer's name, booking time, contact information, or any other personally identifiable information to any other customer, at any point in any customer-facing interface.

**NFR-PRIV-02:** Queue depth and load indicators displayed to customers (in both the discovery list and the salon detail view) shall be expressed exclusively as anonymized aggregate counts or categorical labels (for example: "3 people ahead", "busy", "quiet"). No individual booking record may be surfaced.

**NFR-PRIV-03:** The salon partner app may display customer names for bookings at that salon, as the salon partner has a direct service relationship with the customer. Customer information visible in the app is not to be exposed to any third party or other salon partner.

Source: project-brief.md §8 "Data privacy note"; addendum.md "Queue visibility privacy" — stated as explicit NFR requirement

### 8.2 Performance

**NFR-PERF-01:** The salon discovery list shall load (initial results visible) within 3 seconds on a standard 4G mobile connection under normal load.

**NFR-PERF-02:** Available slot computation for a selected service at a selected salon shall return results to the customer within 2 seconds under normal load.

**NFR-PERF-03:** Booking confirmation (slot reserved, dashboard updated, notification dispatched) shall complete within 5 seconds of the customer submitting the booking.

**NFR-PERF-04:** Salon profile and catalog changes made by the salon partner shall be reflected in customer-facing views within 60 seconds.

Source: derived from two-sided real-time system requirement, addendum.md Technical Considerations; targets are a starting constraint, reviewable with the Architect.

### 8.3 Availability and Reliability

**NFR-REL-01:** The slot booking path (FR-C-BOOK-01 through FR-C-BOOK-07) is the highest-criticality path and shall be designed to prevent double-booking under concurrent load. The Architect shall specify the concurrency control mechanism.

**NFR-REL-02:** The system shall prevent loss of a confirmed booking record under any single component failure. Booking records are durable once confirmation is returned to the customer.

Source: project-brief.md §8; operational risk of double-booking identified in brief.md Risks

### 8.4 Security

**NFR-SEC-01:** All data in transit between client and server shall be encrypted (TLS). The Architect shall specify the minimum TLS version.

**NFR-SEC-02:** Customer passwords (if email/password authentication is supported) shall be stored using an industry-standard password hashing algorithm (for example, bcrypt or Argon2). Plaintext passwords shall never be stored.

**NFR-SEC-03:** OTP codes (if SMS authentication is supported) shall expire within 10 minutes of generation and be invalidated after one use.

**NFR-SEC-04:** The salon partner mobile app must enforce access control so that a salon partner can only view and modify data belonging to their own salon account.

Source: standard security baseline; addendum.md Technical Considerations; authentication requirements FR-C-AUTH-01–03, FR-P-AUTH-01–02

### 8.5 Data Privacy

**NFR-PRIV-04:** The system shall comply with applicable data protection obligations for the launch jurisdiction. Specific regulatory requirements (for example, PDPB in India) are a human decision; the Architect shall flag any data handling pattern that requires legal review.

**NFR-PRIV-05:** Customer personal data (name, phone number, email) shall not be shared with third parties other than for the purposes of delivering the service (for example, SMS OTP delivery).

Source: resolved assumption #1 (single city, Indian market implied by INR); addendum.md Risks

---

## 9. Data Model (Conceptual)

This section defines the key entities, their attributes, and their relationships for the purposes of shared understanding across PRD, Architecture, and UX. It is not a database schema. The Architect owns the authoritative schema.

### Business (Salon)

Represents a single salon location. One Business per salon partner account in MVP.

| Attribute | Type | Notes |
|---|---|---|
| id | identifier | System-generated |
| name | string | Required |
| address | string | Street address, single city |
| city | string | Fixed to launch city |
| phone | string | |
| operating_hours | map<DayOfWeek, TimeRange> | Open/close per day; null = closed |
| average_rating | decimal | Computed from Ratings |
| created_at | timestamp | |

### Service

A service offered by a Business. Belongs to exactly one Business.

| Attribute | Type | Notes |
|---|---|---|
| id | identifier | |
| business_id | foreign key → Business | |
| name | string | Required |
| duration_minutes | integer | Service duration, positive |
| slot_duration_minutes | integer | Duration used for slot blocking (includes buffer); defaults to duration_minutes |
| price_inr | decimal | Price in INR, positive |
| active | boolean | Soft-delete: false = not shown to customers, existing bookings unaffected |

### Staff

A staff member employed by a Business.

| Attribute | Type | Notes |
|---|---|---|
| id | identifier | |
| business_id | foreign key → Business | |
| name | string | Required |
| qualified_service_ids | list<foreign key → Service> | Services this staff member can perform |
| working_hours | map<DayOfWeek, TimeRange> | Must be within Business operating hours |
| active | boolean | |

### Booking

A confirmed reservation by a Customer for one Service at one Business.

| Attribute | Type | Notes |
|---|---|---|
| id | identifier | Booking reference |
| customer_id | foreign key → Customer | |
| business_id | foreign key → Business | |
| service_id | foreign key → Service | |
| staff_id | foreign key → Staff (nullable) | MVP: may be unassigned; Architect to decide if auto-assignment is in scope |
| scheduled_start | datetime | |
| scheduled_end | datetime | scheduled_start + slot_duration_minutes |
| status | enum | confirmed, cancelled, completed, no_show |
| created_at | timestamp | |

### Customer

A registered customer account.

| Attribute | Type | Notes |
|---|---|---|
| id | identifier | |
| name | string | |
| phone | string | Used for OTP and notifications |
| email | string (nullable) | Used for email/password auth |
| created_at | timestamp | |

### Rating

A review submitted by a Customer for a Booking. One rating per booking.

| Attribute | Type | Notes |
|---|---|---|
| id | identifier | |
| booking_id | foreign key → Booking | Unique; one rating per booking |
| customer_id | foreign key → Customer | |
| business_id | foreign key → Business | Denormalized for query efficiency |
| stars | integer | 1–5 |
| review_text | string (nullable) | Max 500 characters |
| created_at | timestamp | |

### Offer

A promotional offer created by a salon partner for their Business.

| Attribute | Type | Notes |
|---|---|---|
| id | identifier | |
| business_id | foreign key → Business | |
| title | string | |
| description | string | Free text |
| expiry_date | date (nullable) | Null = no expiry |
| active | boolean | |

### Slot (computed, not persisted)

Slots are not stored as records. The slot suggestion engine computes available slots on demand from Business operating hours, Staff working hours, Service slot_duration_minutes, and existing Bookings with status = confirmed.

The Architect shall define the slot computation algorithm and any caching strategy.

---

## 10. Open Questions and Deferred Decisions

The following items are explicitly open at the time of PRD completion. Each has an identified owner. None of these blocks the Architect or UX Designer from beginning their work on the MVP core.

### Resolved — Not Open

The following items were open assumptions in the source brief, or decisions made by the founder after initial PRD production. They are treated as closed decisions.

| Item | Resolution |
|---|---|
| Launch geography | Single city, single locale. No multi-region. |
| Salon types in scope | Generic Business model. All salon types (hair, barber, unisex, spa) are included as data differentiation, not logic differentiation. |
| Multi-service / multi-person in MVP | Out of MVP. Single service per booking. Free/busy slot suggestion only. |
| Monetization model | Deferred entirely post-MVP. No monetization requirement in this PRD. |
| In-app payments | Out of scope for MVP. Pay-at-salon only. No payment integration, no PCI scope. |
| Currency | INR. Fixed. No currency selection. |
| Salon Partner platform | Mobile app (iOS and Android) — confirmed by founder. The Salon Partner surface is not a web console. |

### Open — Architect to Resolve

| Question | Notes |
|---|---|
| Staff assignment to bookings | The data model marks staff_id as nullable in MVP. Is a booking assigned to a specific staff member at the time of booking, or only at the time of service? If assigned at booking, the slot engine must be per-staff, not per-salon. This is an architectural and UX decision — do not resolve in the PRD. |
| Slot computation caching | For high-traffic salons, computing available slots on every request may be expensive. The Architect shall decide whether slots are cached and what the invalidation strategy is. |
| Concurrency control for bookings | FR-C-BOOK-07 mandates no double-booking. The Architect shall specify the locking or reservation mechanism. |
| Authentication methods | FR-C-AUTH-02 requires at least one of OTP-SMS or email/password. The Architect shall select and document the method(s) supported at launch. |
| Notification delivery | FR-C-BOOK-05, FR-C-MGT-05, FR-P-DASH-05–06 require notifications. Push vs. SMS vs. email is an Architect decision. FR-P-DASH-05 and FR-P-DASH-06 are written as push notifications given the mobile app form factor; the Architect shall confirm the delivery mechanism. |
| Minimum TLS version | NFR-SEC-01 requires TLS. The Architect shall specify the minimum version. |
| Data residency and regulatory compliance | NFR-PRIV-04 flags this. The specific regulatory requirements for the launch city/jurisdiction require legal review — a human decision. |

### Open — Founder to Decide

| Question | Notes |
|---|---|
| Walk-in reconciliation policy | Salons that continue accepting walk-in customers alongside app bookings may invalidate slot accuracy. The platform requires a defined policy (for example, salons must commit to no walk-ins, or walk-ins must be manually logged in the app). This is a go-to-market and product policy decision. |
| Bootstrapping average service duration | At launch there is no historical data. Initial service durations are entered manually by the salon partner. The policy for verifying or correcting inaccurate durations is a product decision. |
| Go-to-market and cold-start strategy | How the first salons are onboarded is a business decision not covered in this PRD. The two-sided cold-start risk is noted in the brief and remains open. |
| KPI targets | Section 3 defines the KPI definitions. Numeric targets are a founder decision. |
| Review moderation policy | FR-C-RAT-05 hides the customer's full name. Additional moderation (for example, profanity filtering, dispute resolution) is a product policy decision. |

---

## Appendix A: Requirement Traceability Summary

| Requirement Group | Source |
|---|---|
| FR-C-LOC (Location) | project-brief.md §6.1; addendum.md Technical Considerations |
| FR-C-DISC (Discovery) | project-brief.md §6.1, §3 |
| FR-C-DET (Salon Detail) | project-brief.md §6.1; addendum.md Queue visibility privacy |
| FR-C-BOOK (Booking) | project-brief.md §6.1; resolved assumptions #3, #5 |
| FR-C-MGT (Booking Management) | project-brief.md §6.1; addendum.md Notifications |
| FR-C-RAT (Ratings) | project-brief.md §6.1; addendum.md Ratings/reviews |
| FR-C-AUTH (Customer Auth) | Implied by FR-C-MGT, FR-C-RAT; addendum.md Ratings/reviews |
| FR-P-AUTH (Partner Auth) | project-brief.md §6.2; resolved assumption #2 |
| FR-P-PROF (Profile) | project-brief.md §6.2; resolved assumption #1 |
| FR-P-SVC (Catalog) | project-brief.md §6.2; resolved assumptions #1, #2 |
| FR-P-OFFER (Offers) | project-brief.md §6.2; resolved assumption #5 |
| FR-P-STAFF (Staff) | project-brief.md §6.2 |
| FR-P-SCHED (Schedule) | project-brief.md §6.2; resolved assumption #3 |
| FR-P-DASH (Dashboard) | project-brief.md §6.2; addendum.md Notifications |
| NFR-PRIV (Privacy) | project-brief.md §8; addendum.md Queue visibility privacy — explicit NFR |
| NFR-PERF (Performance) | addendum.md Technical Considerations |
| NFR-REL (Reliability) | addendum.md Technical Considerations; brief.md Risks |
| NFR-SEC (Security) | Standard baseline; FR-C-AUTH, FR-P-AUTH |
| Data Model | project-brief.md §3, §6; addendum.md Technical Considerations |
