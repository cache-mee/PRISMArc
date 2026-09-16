---
title: "UX Spec — Customer Booking Management"
surface: "Customer Mobile App (iOS + Android)"
flow: "My Bookings List, View Detail, Cancel, Reschedule"
prd-refs: "FR-C-MGT-01 through FR-C-MGT-05, FR-C-AUTH-01, FR-C-BOOK-07"
created: 2026-09-05
---

# Customer Booking Management Flow

## Overview

Booking management is gated on authentication (FR-C-AUTH-01 — booking management
requires an account). The flow covers: viewing the booking list, viewing a single
booking's detail, cancelling an upcoming booking, and rescheduling an upcoming
booking (which reuses the SlotPicker flow with the same service and salon).

---

## Screen: BookingList

**Entry point:**
1. "My Bookings" tab in bottom navigation (unauthenticated → shows AuthGate modal).
2. "View my bookings" button on BookingConfirmation screen.

### Components

- `screen_title`: "My Bookings".
- `tab_bar`: Two tabs:
  - "Upcoming" (default selected): shows bookings with `status = confirmed` and
    `scheduled_start` in the future.
  - "Past": shows bookings with `status = completed`, `status = cancelled`,
    `status = no_show`, or `status = confirmed` with `scheduled_start` in the past.
- `booking_card` (per booking in the active tab, FR-C-MGT-02):
  - `salon_name_text`: Bold. Salon name.
  - `service_name_text`: Service name.
  - `booking_datetime_text`: "{Day}, {Date} at {Time}" in device local time.
  - `booking_status_chip`: Status badge:
    - Confirmed: filled green chip, "Confirmed".
    - Cancelled: filled red chip, "Cancelled".
    - Completed: filled grey chip, "Completed".
    - No-show: filled amber chip, "No-show".
  - `booking_ref_text`: "Ref: {Booking.id}" — small caption, monospace.
  - `action_area` (upcoming tab only, `status = confirmed`):
    - `reschedule_button`: "Reschedule" — outlined secondary button.
    - `cancel_button`: "Cancel" — text button, destructive color (red).

### Interactions

- Tap tab → switch list content. No network call if list was already loaded in
  this session (cached in BLoC state); pull-to-refresh forces a re-fetch.
- Tap anywhere on `booking_card` (outside action buttons) → navigate to
  BookingDetail for that booking.
- Tap `reschedule_button` → navigate to RescheduleFlow (see below).
- Tap `cancel_button` → show CancelConfirmation bottom sheet (see below).
- Pull-to-refresh → re-fetch both upcoming and past lists. Update BLoC state.

### Error / Edge States

- **Loading failure:** Show "Couldn't load bookings. Check your connection." with
  "Try again" button.
- **Upcoming tab empty:** Illustration + "No upcoming bookings." + "Book a salon"
  CTA (navigates to DiscoveryList).
- **Past tab empty:** "No past bookings yet. Your completed visits will appear
  here."
- **Tab switches while loading:** Show shimmer placeholder cards for the new tab
  while loading.
- **Booking status changed externally (e.g., partner marked as no-show):** Pull-
  to-refresh reflects the change. No real-time push update on the list (the push
  notification for the reminder is handled separately, FR-C-MGT-05, not a list
  update). The list is eventually consistent with the pull-to-refresh pattern.

### Privacy / Accessibility

- All bookings shown are the authenticated customer's own bookings only
  (FR-C-AUTH-03, NFR-SEC-04 enforced server-side: customer can only see their
  own booking records).
- `booking_card` semantic label: "{salon_name}, {service_name}, {datetime},
  {status}. Booking reference {ref}. Double-tap to view details."
- Tab bar announces selected state: "Upcoming, selected" / "Past".
- `cancel_button` semantic label: "Cancel this booking." (Full sentence, not
  just "Cancel" — avoids ambiguity with "cancel the current screen action".)

---

## Screen: BookingDetail

**Entry point:** Tapping a `booking_card` on BookingList.

### Components

- `back_button`: Chevron left, returns to BookingList.
- `screen_title`: "Booking details".
- `booking_status_chip`: Same as on BookingList card — large, top of screen.
- `salon_section`:
  - `salon_name_text`: Bold.
  - `address_text`: Salon address.
  - `phone_text`: Tappable — calls the salon. "Call salon" label.
  - `view_salon_button`: "View salon" — text link. Navigates to SalonDetail
    for this salon. Allows customer to check queue before leaving home.
- `appointment_section`:
  - `service_name_text`: Service name.
  - `date_time_text`: Full date and time, device local time.
  - `duration_text`: "{duration_minutes} min".
  - `price_text`: "₹{price_inr} — pay at salon".
- `booking_ref_section`:
  - `booking_ref_text`: "{Booking.id}" in monospace.
  - `copy_ref_button`: Copy icon. Copies to clipboard, shows "Copied" toast.
- `reminder_note`: "A reminder will be sent 24 hours before your appointment."
  (FR-C-MGT-05 — informational note. Shown for confirmed upcoming bookings only.)
- `action_section` (confirmed upcoming bookings only):
  - `reschedule_button`: "Reschedule appointment" — secondary outlined, full-width.
  - `cancel_button`: "Cancel booking" — destructive outlined button, full-width,
    red border and text.
- `rate_now_button`: "Rate your visit" — primary CTA, full-width (shown only when
  `status = completed` AND no rating exists yet for this booking). Navigates to
  RatingSubmission screen.

### Interactions

- Tap `back_button` → return to BookingList.
- Tap `phone_text` → launch `tel:` URI.
- Tap `view_salon_button` → navigate to SalonDetail (pushes onto stack; back
  returns to BookingDetail).
- Tap `reschedule_button` → navigate to RescheduleFlow.
- Tap `cancel_button` → show CancelConfirmation bottom sheet.
- Tap `copy_ref_button` → copy booking reference. Toast: "Booking reference copied."
- Tap `rate_now_button` → navigate to RatingSubmission (only for completed,
  unrated bookings).

### Error / Edge States

- **Booking load failure:** "Couldn't load booking details. Check your connection."
  Retry button. Back button functional.
- **Completed booking already rated:** `rate_now_button` is hidden. A non-
  interactive "You've rated this visit" confirmation text replaces it, with a
  star summary (the rating the customer submitted).
- **Cancelled booking:** `action_section` hidden. `booking_status_chip` shows
  "Cancelled" in red. No `reminder_note`. No `rate_now_button`.
- **No-show booking:** same as cancelled — action section hidden, chip shows
  "No-show". No `rate_now_button` (FR-P-DASH-04: no-show must not trigger
  rating prompt).

### Privacy / Accessibility

- Customer sees their own booking data only. Salon's customer name visible to
  partner (FR-P-DASH-02) but never to other customers.
- `reschedule_button` and `cancel_button` have 52pt height (larger than minimum —
  these are consequential actions and should be easier to tap accurately).
- `cancel_button` uses destructive visual treatment (red) to signal irreversibility.
- `rate_now_button` semantic label: "Rate your visit to {salon_name}."

---

## Sheet: CancelConfirmation

**Entry point:** Tapping `cancel_button` on BookingList card or BookingDetail.

### Components

- `sheet_handle`: Drag indicator.
- `sheet_title`: "Cancel booking?".
- `warning_text`: "Your slot will be released and someone else may book it.
  This cannot be undone."
- `booking_summary`: Read-only mini summary:
  - `salon_name_text`
  - `service_name_text`
  - `datetime_text`
- `confirm_cancel_button`: "Cancel booking" — destructive primary button
  (red fill), full-width, 52pt.
- `keep_button`: "Keep my booking" — secondary outlined, full-width, 52pt.
  Dismisses sheet without cancellation.

### Interactions

- Tap `confirm_cancel_button` → PATCH /bookings/{id}/cancel. Show loading spinner
  inside button. Disable both buttons.
  - Success → dismiss sheet, return to BookingList or BookingDetail. Update the
    booking's `status_chip` to "Cancelled". Show brief success toast: "Booking
    cancelled." (FR-C-MGT-03: slot is released, cancellation notifications sent
    to customer and partner — notification is server-initiated, not shown in UI
    beyond the toast.)
  - Error → re-enable buttons. Show inline error: "Couldn't cancel. Try again."
- Tap `keep_button` or swipe down → dismiss sheet. No change to booking.

### Error / Edge States

- **Booking already cancelled (concurrent cancellation from another session):**
  API returns error. Message: "This booking is already cancelled."
  Sheet closes, BookingList refreshes.
- **Booking already completed or no-show:** API returns error. Message:
  "This booking can no longer be cancelled." Sheet closes.

### Privacy / Accessibility

- `confirm_cancel_button` semantic label: "Confirm cancellation of {service_name}
  at {salon_name} on {datetime}."
- `keep_button` semantic label: "Keep my booking and go back."
- Sheet is announced as a dialog to screen readers.
- Warning text is the first focusable element in the sheet for screen reader
  navigation.

---

## Flow: RescheduleFlow

**Entry point:** Tapping `reschedule_button` on BookingList or BookingDetail.

### Overview

Rescheduling reuses the SlotPicker screen with the same salon and service context.
It behaves identically to a new booking for slot-conflict purposes (FR-C-MGT-04).
The difference from a new booking: on confirm, the existing booking is updated
(its `scheduled_start` changes) rather than a new booking being created.

### Screen: RescheduleSlotPicker

This is the SlotPicker screen (see customer-booking.md) with the following
differences:

- `screen_title`: "Reschedule — Choose a new time".
- `booking_summary_card` shows:
  - `current_appointment_text`: "Current appointment:" + existing date/time.
  - `salon_name_text`, `service_name_text`, `service_duration_text`,
    `service_price_text` (same as standard SlotPicker).
  - No `change_service_link` (service cannot be changed during reschedule; to
    change service, cancel and make a new booking).
- `date_selector`: The date of the existing booking is not disabled (customer
  can pick a different time on the same day).
- `confirm_button` label: "Confirm new time" (instead of "Confirm booking").
- `pay_at_salon_note`: Unchanged.
- On tap of `confirm_button` → PATCH /bookings/{id}/reschedule with new
  `scheduled_start`. Same conflict handling as POST /bookings (FR-C-MGT-04):
  409 returns the slot conflict error (see customer-booking.md SlotPicker error
  states). On success → navigate to RescheduleConfirmation screen.

### Screen: RescheduleConfirmation

- `success_icon`: Same checkmark animation as BookingConfirmation.
- `headline`: "Booking updated!".
- `confirmation_card`: Shows new date/time, salon, service, booking ref.
  (Booking ref does not change on reschedule — same Booking.id.)
- `notification_note`: "A confirmation of your new time has been sent to your
  phone."
- `view_booking_button`: "View booking" → navigates to BookingDetail.
- `done_button`: "Done" → navigates to BookingList.
- OS back is overridden to navigate to BookingList (same rationale as
  BookingConfirmation: the SlotPicker is no longer useful after confirmation).

### Error / Edge States

All error states from SlotPicker apply identically (see customer-booking.md).
Additional reschedule-specific state:

- **Booking not in a reschedulable state (e.g., completed or cancelled between
  the reschedule intent and the confirm):** API returns error. Show: "This booking
  can no longer be rescheduled." Navigate back to BookingDetail on dismiss.

### Privacy / Accessibility

- Same as SlotPicker (see customer-booking.md). The existing booking date is
  shown in `current_appointment_text` — this is the customer's own data and is
  correct to display.

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Upcoming / Past tabs instead of a single list | FR-C-MGT-01 requires both upcoming and past bookings to be visible. A single chronological list with mixed statuses is hard to scan. Priya's primary use case is managing upcoming visits; past bookings are secondary. Tabs give quick access to both without clutter. | Single list with status filter — more steps to reach past bookings. Accepted tabs as the lower-friction pattern. |
| Cancel confirmation is a bottom sheet, not an in-line confirmation | Cancellation is irreversible (slot is released — FR-C-MGT-03). A confirmation step is appropriate for any destructive, irreversible action. A bottom sheet is less disorienting than a full screen for this confirmation. | In-line "Are you sure?" toggle — too easy to accidentally confirm. Full-screen confirmation — disproportionate for a brief confirmation. |
| Reschedule reuses SlotPicker | The slot picking interaction is identical (FR-C-MGT-04: "behaves identically to a new booking for slot-conflict purposes"). Reusing the screen avoids duplicating a complex interaction. The differences are handled by navigation context (screen title, confirm button label, API endpoint). | Separate reschedule screen — no value in duplication; unnecessary development work. |
| Service cannot be changed during reschedule | PRD FR-C-MGT-04 specifies "the same service" for reschedule. Changing the service is semantically a cancel + new booking, not a reschedule. Simplifying to same-service avoids a complex service-switch-during-reschedule state machine. | Allow service change during reschedule — post-MVP if there is user demand; out of scope per PRD. |
| "Keep my booking" is the secondary action on CancelConfirmation | The sheet's visual hierarchy should reflect that continuation (keep) is the safer default and cancellation is the consequential action. "Keep" is secondary (outlined) but is the last button tapped in the natural reading order, making it easy to reach without confirmation fatigue. | "Keep" as primary (prominent) — would draw the eye away from the cancel action when the user intent is to cancel, creating confusion. Current ordering: warning first, cancel second, keep last. |
