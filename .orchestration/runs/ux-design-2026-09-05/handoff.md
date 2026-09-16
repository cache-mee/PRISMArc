# Handoff

## Work ID
ux-design-2026-09-05

## Objective
Produce complete UX screen specifications for the salon-app Customer and Salon
Partner mobile surfaces, grounded in the approved PRD and approved Flutter + BLoC
stack rules.

## Acceptance Criteria

1. All 12 UX specification files exist at
   `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/`.
2. Every screen in every file includes: entry point, components with field names,
   interaction rules, error/edge states, and privacy/accessibility notes.
3. Queue visibility (NFR-PRIV-01, NFR-PRIV-02) is explicitly documented in every
   screen where queue data appears, naming the information boundary at the API level.
4. No payment screen appears anywhere in the customer flow (FR-C-BOOK-08).
5. Slot picker shows only available slots (FR-C-BOOK-02).
6. Rating flow is gated on `status = completed` (FR-C-RAT-01, FR-C-RAT-04).
7. All field names use the PRD data model names where applicable
   (`duration_minutes`, `slot_duration_minutes`, `price_inr`, etc.).
8. All design decisions with non-obvious rationale include a decision record.

## Current State

UX specification is complete. All 12 files written to disk. No application source
code was created or modified. Branch: `feature/bmad-setup`. Only planning artifacts
were written.

## Completed

- Read PRD at `bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-05/prd.md` (full).
- Read `stack/rules/base-rules.md` (full — Flutter + BLoC, REST-only slot engine confirmed).
- Read `bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-04/addendum.md`.
- Read `.orchestration/runs/pm-prd-2026-09-05/handoff.md` (incoming handoff).
- Read `.claude/STANDARDS.md` and `.orchestration/schemas/handoff.md`.
- Produced all 12 UX specification files:
  1. `customer-auth.md` — 5 screens (AuthGate, PhoneEntry, OTPVerification,
     RegistrationName, EmailLogin, EmailRegistration — 5 primary + 1 conditional)
  2. `customer-discovery.md` — 3 screens (LocationResolution/DiscoveryList,
     LocationSearch, FilterSheet)
  3. `customer-salon-detail.md` — 1 screen (SalonDetail, with queue privacy
     boundary explicitly specified at API level)
  4. `customer-booking.md` — 2 screens (SlotPicker, BookingConfirmation)
  5. `customer-booking-management.md` — 3 screens + 1 sheet + 2 reschedule screens
     (BookingList, BookingDetail, CancelConfirmation, RescheduleSlotPicker,
     RescheduleConfirmation)
  6. `customer-ratings.md` — 2 screens + 1 trigger/banner
     (RatingPrompt banner, RatingSubmission, RatingConfirmation)
  7. `partner-auth.md` — 3 screens (PartnerSplash, PartnerLogin, ForgotPassword)
     + session management rules
  8. `partner-profile.md` — 1 screen (SalonProfile view/edit) + 1 sheet
     (DiscardChanges)
  9. `partner-catalog.md` — 4 screens + 2 sheets (ServiceList, ServiceForm,
     OfferList, OfferForm, DeleteServiceConfirmation, DeleteOfferConfirmation)
  10. `partner-staff.md` — 2 screens + 1 sheet (StaffList, StaffForm,
      RemoveStaffConfirmation)
  11. `partner-schedule.md` — 1 screen (ScheduleConfig)
  12. `partner-dashboard.md` — 1 screen + 3 sheets (PartnerDashboard,
      BookingDetailSheet, MarkCompleteConfirmation, MarkNoShowConfirmation)

Evidence note: UX specification production is a design/writing task. No
deterministic automated validation applies. This record is labelled a **judgement**:
all files were written against the PRD requirements, the stack rules, and the
NFR privacy constraints. Human design review is the appropriate gate for UX
approval. File existence on disk is verifiable; content quality is a judgement.

## Failed / Unresolved

None. All 12 files produced.

Open design questions passed to the Product Manager:

1. **Partner self-serve registration:** The partner app has no in-app registration
   screen (see `partner-auth.md`). If the founder decides on self-serve onboarding,
   a PartnerRegistration screen must be designed. Blocked on go-to-market decision
   (PRD Section 10 — Founder to decide).

2. **Staff assignment to booking:** PRD Section 10 leaves open whether a booking
   is assigned to a specific staff member at booking time or service time. The
   `partner-staff.md` notes that if bookings are staff-assigned, a scheduling
   conflict warning must be added to StaffForm when editing hours. The Architect
   must resolve this first; a UX update will follow.

3. **Retroactive mark-complete on past dates:** `partner-dashboard.md` specifies
   that action buttons are hidden for past-date bookings. If the Product Manager
   decides retroactive mark-complete is a valid operation, the date-based
   restriction must be lifted and the rating-prompt timing logic revisited.

4. **App deep-link infrastructure:** `customer-salon-detail.md` notes the share
   button is post-MVP unless deep-link infrastructure is confirmed. Architect to
   confirm.

## Constraints

- Scope: UX specification only. No application source code created or modified.
- All screens derive exclusively from PRD requirements. No feature was invented
  outside PRD scope.
- Post-MVP ideas are recorded as notes, not designed.
- Queue visibility: API-level enforcement of NFR-PRIV-01/02 is documented in
  every queue-displaying screen. The UX spec names the API boundary explicitly.
- No payment screens anywhere (FR-C-BOOK-08).
- Single service per booking (PRD Section 5.2).
- Rating only for completed bookings (FR-C-RAT-01, FR-C-RAT-04).
- All prices in INR (`price_inr` field name), all durations in minutes
  (`duration_minutes`, `slot_duration_minutes`).
- Flutter + BLoC, touch-first, all tap targets ≥ 44pt.

## Decisions

- **Authentication gate deferred to booking action (customer app):** PRD
  FR-C-AUTH-01 permits unauthenticated browsing. Auth gate appears when a booking
  is initiated, not at app open.
- **Queue indicator on discovery list uses categorical labels ("Quiet/Moderate/
  Busy"), not counts:** Detail view exposes the numeric count ("3 people ahead").
  List card uses lower-precision label because the count lacks context without
  knowing the salon's capacity. Both comply with NFR-PRIV-02.
- **API-level queue boundary, not UI-level:** Queue data returned to the customer
  API contains only `queue_depth` (integer), `load_category` (enum), and
  `computed_at` (timestamp). No booking records are returned to customer-facing
  clients. This is specified as a developer implementation requirement in
  `customer-salon-detail.md`.
- **`slot_duration_minutes` not shown to customers:** Internal scheduling buffer
  is not a customer-facing value. Customers see only `duration_minutes`.
- **Slot picker shows only available slots (no greyed-out unavailable):**
  FR-C-BOOK-02 explicit requirement.
- **Slot conflict (409) shows inline error, not a new screen:** Lowest-friction
  recovery path.
- **Partner self-serve registration deferred:** Go-to-market decision pending
  (PRD Section 10). PartnerLogin directs unregistered partners to contact support.
- **Timeline is today-only; date filter applies only to the booking list:**
  Future-date timeline deferred to post-MVP.
- **No action buttons for past-date bookings in partner dashboard:** Prevents
  retroactive mark-complete triggering stale rating prompts.
- **DiscardChanges confirmation sheet on back/cancel in all partner edit forms:**
  Consistent pattern across ProfileForm, ServiceForm, OfferForm, StaffForm.

## Evidence

- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/customer-auth.md`
  — exists on disk; 5+ screens, OTP flow, privacy notes.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/customer-discovery.md`
  — exists on disk; 3 screens, filter sheet, queue privacy.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/customer-salon-detail.md`
  — exists on disk; 1 screen, API-level queue boundary specified.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/customer-booking.md`
  — exists on disk; 2 screens, slot conflict handling, no payment screen.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/customer-booking-management.md`
  — exists on disk; 5 screens + sheet, reschedule reuses SlotPicker.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/customer-ratings.md`
  — exists on disk; 2 screens, gated on completed status.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/partner-auth.md`
  — exists on disk; 3 screens, session management rules.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/partner-profile.md`
  — exists on disk; 1 screen, hours validation.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/partner-catalog.md`
  — exists on disk; 4 screens, slot duration field specified.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/partner-staff.md`
  — exists on disk; 2 screens, operating hours validation.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/partner-schedule.md`
  — exists on disk; 1 screen, slot duration inline edit.
- `bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/partner-dashboard.md`
  — exists on disk; 1 screen + 3 sheets, mark-complete/no-show flows.

All evidence is judgement (content quality) + verifiable (file existence).

## Next Action

### Architect agent

Read the 12 UX spec files at
`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/` before finalizing
the system architecture. Priority items:

1. **Resolve the staff assignment question** (PRD Section 10 open) before
   designing the slot engine. The UX spec for `partner-staff.md` notes that a
   booking-conflict warning must be added to StaffForm if bookings are staff-
   assigned. This is a UX update dependency on the Architect's resolution.

2. **Confirm the API boundary for the queue indicator:** `customer-salon-detail.md`
   specifies that the queue endpoint returns only `queue_depth`, `load_category`,
   and `computed_at`. The Architect must implement this as a separate endpoint from
   the booking list — not an aggregate computed client-side from booking records
   returned to the customer client.

3. **Confirm deep-link support:** `customer-ratings.md` (push notification deep-
   link to RatingSubmission) and `partner-dashboard.md` (push notification deep-
   link to Dashboard + booking highlight) require deep-link routing. Architect to
   confirm FCM/APNs deep-link support and the URL scheme.

4. **Confirm 409 Conflict response for slot conflict:** `customer-booking.md`
   specifies that a slot-taken conflict returns 409 (base-rules.md §3.5 already
   defines this). Architect must confirm the response body shape matches the
   customer-facing "slot no longer available" message mapping.

### Developer agent

Read the 12 UX spec files before implementing any screen. Priority first-sprint
items:

1. Implement customer auth flow (`customer-auth.md`) — OTP or email/password
   depending on Architect's method selection. Auth BLoC must preserve booking
   intent context through the auth flow.

2. Implement customer discovery + salon detail (`customer-discovery.md`,
   `customer-salon-detail.md`) — the queue indicator must use a dedicated endpoint,
   not the booking list. Queue data boundary is an implementation constraint, not
   a UI decision.

3. Implement partner login (`partner-auth.md`) — straightforward email/password,
   JWT stored in `flutter_secure_storage`.

4. For every screen: implement the error states specified in each file. They are
   not optional. Empty states, network failures, and edge cases are first-class
   requirements.

## Completion Condition

The UX specification phase is complete when:
1. The Architect agent confirms the UX artefacts are sufficient to begin API and
   data model design (specifically: queue endpoint shape, slot conflict response,
   staff assignment resolution).
2. The Developer agent confirms the UX artefacts are sufficient to begin screen
   implementation (no ambiguity that would require a product decision mid-sprint).
3. Any open design questions listed above have been routed to the appropriate
   owner (Product Manager or Founder for scope questions; Architect for technical
   questions).

## Escalation

The following require human (founder or Product Manager) decisions:

1. **Partner self-serve registration:** Is partner account creation self-serve
   (via the app) or off-app (back-office provisioning)? This determines whether
   a PartnerRegistration screen must be designed. Until decided, the spec has no
   self-serve registration screen.

2. **Retroactive mark-complete:** Can a partner mark a booking complete after the
   booking date has passed? Currently blocked (no action buttons on past dates).
   If allowed, the rating prompt timing and the UX restriction both need revision.

3. **Walk-in reconciliation policy** (PRD Section 10 — Founder to decide): If the
   founder decides walk-ins must be logged in the app, a walk-in logging screen
   must be designed. Currently out of scope.
