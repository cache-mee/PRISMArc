---
title: "UX Spec — Customer Booking"
surface: "Customer Mobile App (iOS + Android)"
flow: "Service Selection → Slot Picker → Booking Confirmation"
prd-refs: "FR-C-BOOK-01 through FR-C-BOOK-08, NFR-REL-01, NFR-PERF-02, NFR-PERF-03, NFR-SEC-01"
created: 2026-09-05
---

# Customer Booking Flow

## Overview

The booking flow is the highest-criticality path in the customer app (NFR-REL-01).
It is three steps: the customer arrives having already selected a service from the
Salon Detail screen, picks an available time slot, and confirms. Payment is
pay-at-salon; no payment screen exists anywhere in this flow (FR-C-BOOK-08).

The slot engine is REST-only: slots are fetched via GET /slots. There are no
real-time slot updates. If a slot is taken between fetch and confirm, the booking
attempt returns a 409 Conflict and the customer is prompted to re-select
(FR-C-BOOK-07, base-rules.md §3.5).

Single service per booking. No multi-service selection (PRD Section 5.2).

---

## Screen: SlotPicker

**Entry point:** Tapping "Book" on a service row in SalonDetail (authenticated).

### Components

- `back_button`: Chevron left, top-left (44pt). Returns to SalonDetail.
- `screen_title`: "Choose a time".
- `booking_summary_card`: Non-interactive card at top showing:
  - `salon_name_text`: Salon name (from navigation context).
  - `service_name_text`: Selected service name (from `Service.name`).
  - `service_duration_text`: "{duration_minutes} min".
  - `service_price_text`: "₹{price_inr}".
  - `change_service_link`: "Change service" — text link. Tapping returns to
    SalonDetail (pops current screen). This is the only way to change service
    mid-flow (no in-flow service switch).
- `date_selector`: Horizontal scrollable row of date pills covering today +
  next 13 days (14 days total). Each pill:
  - `day_abbr`: "Mon", "Tue", etc.
  - `date_number`: Day of month.
  - Selected pill: filled background, primary color.
  - Disabled pill: dates on which the salon is closed per `operating_hours` —
    greyed out, not tappable.
  - "Today" label replaces `day_abbr` for the current date.
- `slots_area`: Main content area below `date_selector`.
  - `loading_state`: Shimmer placeholder grid while slots are being fetched.
  - `slots_grid`: Grid of `slot_chip` items arranged in rows (3 columns, or 2
    columns on narrow screens). Each `slot_chip`:
    - `time_text`: "10:30 AM" — formatted from `scheduled_start` UTC converted
      to device local time (base-rules.md: display conversion in Flutter layer).
    - Available chip: tappable, outlined, primary color border.
    - Selected chip: filled primary color, white text.
    - (No unavailable chips shown — only available slots are displayed, per
      FR-C-BOOK-02: system "shall display only available time slots".)
- `confirm_button`: "Confirm booking" — primary CTA, full-width, 52pt height,
  sticky at bottom. Disabled until a `slot_chip` is selected.
- `pay_at_salon_note`: Small caption above `confirm_button` — "Pay at the salon
  after your appointment. No payment needed now." (FR-C-BOOK-08 — explicit
  reassurance, prevents customer confusion about a missing payment step.)

### Interactions

- Screen opens → date_selector defaults to today. If salon is closed today, the
  first open day is selected by default.
- Date selected → fire GET /slots?business_id={id}&service_id={id}&date={date}.
  Show loading shimmer while awaiting response. Slots appear within 2 seconds
  (NFR-PERF-02).
- Tap `slot_chip` → chip transitions to selected state. Any previously selected
  chip deselects. `confirm_button` becomes enabled.
- Tap different date → clear selected slot (if any), fetch new slot list for
  that date.
- Tap `confirm_button` → POST /bookings with:
  - `business_id`, `service_id`, `scheduled_start` (UTC), customer auth token.
  Show loading state (spinner inside `confirm_button`, button disabled).
  Booking attempt must complete within 5 seconds (NFR-PERF-03).
  - Success (201) → navigate to BookingConfirmation screen.
  - 409 Conflict → show SlotConflict error state (see below).
  - Other error → show generic booking error state (see below).
- Tap `change_service_link` → pop SlotPicker, return to SalonDetail.
- Tap `back_button` → pop to SalonDetail. No partial booking created (server
  side: booking only exists after POST /bookings succeeds).

### Error / Edge States

- **No slots available on selected date:** `slots_area` shows "No available slots
  on {date}." with a note "Try a different date." No `slots_grid` shown.
- **Loading failure (GET /slots error):** `slots_area` shows "Couldn't load
  available times. Check your connection." with a "Try again" button that retries
  the fetch for the same date.
- **Slot conflict (409 on POST /bookings — FR-C-BOOK-07):** Do not navigate away.
  Show inline error within `slots_area` — "That slot was just booked by someone
  else. Please choose a different time." The previously selected slot chip is
  deselected and visually marked as unavailable (greyed out, not tappable) for
  the duration of this screen session. A background refresh of the slot list is
  triggered to show the current availability. `confirm_button` returns to disabled
  state. The error message auto-dismisses after 5 seconds or when the customer
  selects a new slot.
- **Network failure during confirm (POST timeout):** Show inline error — "Booking
  failed. Check your connection and try again." Do not assume the booking was
  created. Slot remains selected; customer retries manually.
- **Server error (5xx during confirm):** Same treatment as network failure — do
  not assume success.
- **All dates in the 14-day window closed:** `date_selector` shows all pills as
  disabled. `slots_area` shows "This salon has no available slots in the next
  2 weeks. Try again later or contact the salon."
- **Session expired during slot picking:** If the JWT expires mid-flow (edge case
  for a long-idle session), the POST /bookings returns 401. Show AuthGate modal.
  After re-auth, retry the confirm automatically (slot and service context
  preserved in BLoC state).

### Privacy / Accessibility

- No other customer's information is shown anywhere on this screen. Slots are
  computed time windows only — no indication of who occupies other slots.
- `slot_chip` semantic label: "Available at {time}. Double-tap to select."
  Selected: "Selected time {time}. Double-tap to deselect."
- Closed-day pills in `date_selector`: semantic label "{day_abbr} {date},
  closed." Not reachable by swipe navigation (skip in focus order).
- `confirm_button` when disabled: "Confirm booking. Select a time first."
- `pay_at_salon_note` is read by screen reader as part of the page, not skipped.
- `date_selector` is a scrollable row — accessible horizontal scroll via swipe.
- `slots_grid` slots in chronological order left-to-right, top-to-bottom.

---

## Screen: BookingConfirmation

**Entry point:** Successful POST /bookings (201 response from server).

### Components

- `success_icon`: Large checkmark animation (Lottie or Flutter animation).
  Plays once on screen entry. After animation: static large checkmark.
- `headline`: "You're booked!".
- `confirmation_card`: Card showing:
  - `salon_name_text`: Salon name.
  - `service_name_text`: Service name.
  - `booking_date_time_text`: "{Day}, {Date} at {Time}" — formatted in device
    local time. Example: "Tuesday, 9 Sep at 2:30 PM".
  - `duration_text`: "{duration_minutes} min".
  - `price_text`: "₹{price_inr} — pay at salon".
  - `booking_ref_text`: "Booking ref: {Booking.id}". Displayed in monospace or
    distinct typeface for readability.
  - `copy_ref_button`: Copy icon adjacent to `booking_ref_text`. Tapping copies
    the booking reference to clipboard. Brief "Copied" toast confirmation.
- `notification_note`: "A confirmation has been sent to your phone." (FR-C-BOOK-05:
  booking confirmation notification dispatched. Customer is informed without
  displaying the notification content on screen.)
- `pay_at_salon_reminder`: Card or inline note — "Remember: pay at the salon
  after your appointment. No payment now." (FR-C-BOOK-08.)
- `view_booking_button`: "View my bookings" — secondary outlined button.
  Navigates to BookingList screen.
- `done_button`: "Done" — primary CTA, full-width, 52pt. Navigates to
  DiscoveryList (root). Clears the booking navigation stack.

### Interactions

- Screen appears → success animation plays. No user action required.
- Tap `copy_ref_button` → copy `Booking.id` to clipboard. Show toast: "Booking
  reference copied."
- Tap `view_booking_button` → navigate to BookingList. BookingConfirmation is
  removed from navigation stack (user cannot go back to it via back button).
- Tap `done_button` → navigate to DiscoveryList (root). Booking stack cleared.
- Tap `back_button` (OS back gesture) → same as `done_button` (booking is already
  confirmed; going "back" to SlotPicker would be confusing and serve no purpose).
  Override OS back to navigate to root.

### Error / Edge States

- No error states on this screen — the screen only appears after a confirmed
  successful booking.
- If the app crashes or is killed immediately after this screen appears: the booking
  is already persisted server-side (NFR-REL-02). The customer sees it in BookingList.

### Privacy / Accessibility

- `booking_ref_text`: The booking reference (Booking.id) is the customer's own
  data. Displaying it to the authenticated customer is correct.
- `notification_note` does not reveal the channel (SMS vs. push) — the channel
  is an Architect decision and may vary.
- `success_icon` animation: must respect the OS "Reduce Motion" accessibility
  setting. If Reduce Motion is enabled, show a static checkmark immediately
  instead of the animation.
- `confirmation_card` semantic description: read as a single block — "{service_name}
  at {salon_name} on {date} at {time}. {duration} minutes. ₹{price}, pay at
  salon. Booking reference: {booking_ref}."
- `copy_ref_button` semantic label: "Copy booking reference {booking_ref}."

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Only available slots shown (no greyed-out unavailable slots) | PRD FR-C-BOOK-02 explicitly requires showing "only available time slots." Showing unavailable slots creates a denser grid and can frustrate customers who repeatedly tap grey slots. The cognitive model is simpler: everything on screen is bookable. | Show unavailable slots greyed out — rejected: PRD FR-C-BOOK-02 prohibits it and it adds noise to the grid. |
| 14-day forward horizon for date picker | A two-week window is sufficient for a first-visit scheduling scenario (Priya's primary use case is near-term bookings). Beyond two weeks, slot accuracy degrades if staff or hours change. A configurable horizon allows the Architect to tune this. | 7 days — too short for customers who plan ahead. 30 days — slot accuracy risk; left as backend-configurable. |
| Slot conflict shows inline error, not a new screen | The customer needs to re-select a slot on the same screen. Navigating to a new screen and back would lose their context and feel like a worse error. Inline is the lowest-friction recovery. | Modal dialog — adds extra dismissal tap; rejected. Navigate to error screen — loses context; rejected. |
| BookingConfirmation overrides OS back button | Once a booking is confirmed, the SlotPicker has no remaining purpose. Returning to it via back would let a customer attempt to book the same slot again (they're already booked). Override prevents confusion and double-booking attempts. | Let OS back navigate to SlotPicker — rejected: confusing state and double-booking risk. |
| "Pay at salon" reminder on both SlotPicker and BookingConfirmation | PRD FR-C-BOOK-08 is an explicit constraint. Customers may be confused by the absence of a payment step. Two placement points (before confirm + after confirm) ensures the message lands. | Once only — risk of customers missing the message and arriving expecting an in-app payment screen. |
