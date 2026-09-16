---
title: "UX Spec — Partner Booking Dashboard"
surface: "Salon Partner Mobile App (iOS + Android)"
flow: "Today's Timeline, Queue, Incoming Bookings, Mark Complete/No-Show"
prd-refs: "FR-P-DASH-01 through FR-P-DASH-06, FR-P-SCHED-03, NFR-PRIV-03"
created: 2026-09-05
---

# Partner Booking Dashboard Flow

## Overview

The Dashboard is the partner's operational home screen. It combines:
- Today's booking timeline across all staff (FR-P-SCHED-03).
- Current queue state (live count of confirmed bookings in the day's schedule).
- Upcoming bookings list, filterable by date and staff (FR-P-DASH-01).
- Per-booking actions: mark completed, mark no-show (FR-P-DASH-03, FR-P-DASH-04).

The partner receives push notifications for new bookings and customer cancellations
(FR-P-DASH-05, FR-P-DASH-06). The Dashboard is the landing screen after partner
login — it is the "hub" of the partner app.

Customer names are visible to the partner for their own salon's bookings
(NFR-PRIV-03). They must never be shared with other salon partners or exposed
beyond the partner's own view.

---

## Screen: PartnerDashboard

**Entry point:**
1. Default screen after successful login (PartnerSplash → PartnerDashboard).
2. "Dashboard" tab in partner bottom navigation.
3. Tapping a push notification for a new booking or cancellation.

### Components

**Header**

- `screen_title`: "Dashboard".
- `date_text`: "Today — {Day}, {Date}" e.g., "Today — Saturday, 6 Sep".
- `settings_button`: Gear/settings icon, top-right (44pt). Navigates to
  PartnerSettings (logout, profile link, notification preferences — Architect to
  confirm scope).

**Queue summary card (top of screen)**

- `queue_summary_card`: Prominent card showing current snapshot of today.
  - `active_now_count`: Large number — count of bookings currently in progress
    or immediately next (within 15 minutes). Label: "In chair / up next".
  - `total_today_count`: Secondary — "X bookings today".
  - `remaining_count`: "Y remaining" — confirmed bookings later today.
  - `load_label`: "Quiet" | "Moderate" | "Busy" — same categorical label as
    customer-facing queue, but the partner also has the underlying data available
    via the full booking list below.

**Today's Timeline (FR-P-SCHED-03)**

- `timeline_section_header`: "Today's Schedule".
- `staff_filter_tabs` (horizontal scrollable tab row): "All staff" (default) +
  one tab per staff member. Allows filtering the timeline by a specific staff
  member. (FR-P-DASH-01: filterable by staff member.)
- `timeline_view`: Horizontal time-scroll timeline, covering today's operating
  hours (from salon open to close). Each `booking_block` on the timeline:
  - `booking_block`: Color-coded rectangle sized proportionally to
    `slot_duration_minutes`. Contains:
    - `customer_name_text`: Customer name (truncated to fit block).
    - `service_name_text`: Service name.
    - `time_text`: "{start_time}".
    - Status-coded color: confirmed = primary color; completed = grey;
      no-show = amber strikethrough.
  - Blocks that would overlap (edge case from concurrency or schedule errors)
    are shown side-by-side within the same time band, not overlapping.
  - Current time indicator: vertical red line showing the current time within
    the timeline.
  - If `staff_filter_tabs` is on "All staff": bookings for different staff are
    shown in separate horizontal rows (one row per staff member), stacked
    vertically. Row header is the staff member's name.
  - If a specific staff member is selected in `staff_filter_tabs`: one row shown
    for that staff member only.
- `timeline_scroll_position`: Auto-positions the timeline to the current time
  minus 30 minutes on screen load (so the partner sees current and near-future
  bookings without scrolling).

**Upcoming Bookings list**

- `upcoming_section_header`: "Upcoming Bookings".
- `date_filter_bar`: Date picker row (same pattern as customer SlotPicker
  `date_selector` — horizontal scrollable date pills, today + next 13 days).
  Default: today. (FR-P-DASH-01: "filterable by date".)
- `staff_filter_dropdown`: Dropdown or segmented control — "All staff" +
  individual staff names. Separate from `staff_filter_tabs` (timeline tabs) —
  this filters the list below the timeline. Both filters are independent.
- `booking_list`: Vertical list of `partner_booking_card` items.
  - `time_chip`: "{scheduled_start time}" — left-aligned, prominent.
  - `customer_name_text`: Customer's name (FR-P-DASH-02, NFR-PRIV-03 —
    visible to this salon's partner only).
  - `service_name_text`: Service name.
  - `staff_name_text`: Assigned staff member name (if assigned; nullable per
    PRD data model). If unassigned: "Staff TBD" in muted text.
  - `booking_ref_text`: "Ref: {Booking.id}" — small, monospace.
  - `booking_status_chip`: "Confirmed" (green) | "Completed" (grey) |
    "Cancelled" (red) | "No-show" (amber).
  - `action_buttons_row` (for bookings with `status = confirmed` only):
    - `complete_button`: "Mark complete" — primary small button (44pt height).
    - `no_show_button`: "No-show" — secondary small outlined button (44pt height).
  - `completed_indicator` (for `status = completed`): Checkmark icon + "Completed
    at {time}". No action buttons.
  - `no_show_indicator` (for `status = no_show`): Amber dot + "No-show". No
    action buttons.
  - `cancelled_indicator` (for `status = cancelled`): Red cross icon +
    "Cancelled". No action buttons.
- `empty_state_list`: "No bookings on {date}." Shown when the filtered list
  is empty.

### Interactions

**Timeline:**

- Swipe left/right on `timeline_view` → scroll through the day's hours.
- Tap `booking_block` → open BookingDetailSheet for that booking (see below).
- Tap `staff_filter_tabs` tab → filter timeline to that staff member's row
  (or show all staff rows).

**Booking list:**

- Tap date pill in `date_filter_bar` → reload `booking_list` for that date.
  (Also updates `upcoming_section_header` to reflect selected date:
  "Bookings — {date}" when not today; "Today's Bookings" when today.)
- Select staff from `staff_filter_dropdown` → filter `booking_list` to that
  staff member.
- Tap `complete_button` on a `partner_booking_card` → show MarkCompleteConfirmation
  sheet (see below).
- Tap `no_show_button` → show MarkNoShowConfirmation sheet (see below).
- Tap `partner_booking_card` body (not action buttons) → open BookingDetailSheet.
- Pull-to-refresh on `booking_list` → re-fetch bookings for the currently
  selected date and staff filters. Also re-fetch `queue_summary_card` data.

**Push notifications (FR-P-DASH-05, FR-P-DASH-06):**

- New booking push notification tapped → deep-link to Dashboard, auto-scroll
  to the new booking in `booking_list` (today's date selected, highlight
  the new card briefly).
- Cancellation push notification tapped → same as above; the cancelled booking
  shows with `cancelled_indicator`.

**Auto-refresh:**

- Dashboard auto-refreshes `queue_summary_card` every 60 seconds while in
  foreground. `booking_list` does not auto-refresh (pull-to-refresh is the
  manual mechanism); this prevents list disruption while the partner is reading
  booking details. New bookings trigger a push notification which prompts the
  partner to check.

### Error / Edge States

- **Dashboard load failure:** Skeleton placeholders for timeline and list. Error
  banner at top: "Couldn't load bookings. Check your connection." Retry button.
- **Timeline load failure (partial):** Timeline shows error state — "Couldn't
  load today's schedule." Retry inline.
- **No bookings today (selected date):** Empty `timeline_view` (shows time axis
  with no blocks) + `empty_state_list`.
- **All bookings for the day are completed or no-show:** `queue_summary_card`
  shows "0 remaining" and "Quiet". Timeline shows completed blocks (grey).
  No action buttons in the list.
- **Booking list date filter = future date:** `upcoming_section_header` changes.
  Timeline is not shown for future dates (no timeline for future days — the
  timeline is always today's view). A note below `timeline_section_header`:
  "Timeline shows today's schedule only." `date_filter_bar` controls the list,
  not the timeline.
- **Date filter = past date:** Show bookings for that past date (read-only —
  no action buttons regardless of status, because past bookings cannot be
  actioned retroactively via mark-complete — the partner should have done so
  at the time). A note: "Viewing past bookings. Actions are available for
  today's confirmed bookings."

  Decision note: this rule (no actions on past dates) prevents late marking-as-
  complete from triggering stale rating prompts for visits that occurred days ago.
  If the Architect or Product Manager decides retroactive mark-complete is valid,
  this constraint should be revisited.

### Privacy / Accessibility

**Customer name visibility (NFR-PRIV-03):**
- Customer names (`customer_name_text`, `staff_name_text`) are visible on the
  partner dashboard. This is explicitly permitted: "The salon partner app may
  display customer names for bookings at that salon, as the salon partner has a
  direct service relationship with the customer."
- The partner app enforces access control server-side: a partner can only see
  bookings for their own `business_id` (NFR-SEC-04, FR-P-AUTH-02). No other
  salon's bookings are ever returned in this partner's API responses.
- Customer data must not be exported, shared, or displayed beyond this partner's
  own app view. The app provides no data export or share function for booking data.

**General accessibility:**
- `partner_booking_card` semantic label: "{time}, {customer_name}, {service_name},
  {staff_name or unassigned}, {status}. Booking reference {ref}.
  {If confirmed: Double-tap to view details and actions.}"
- `complete_button` semantic label: "Mark {customer_name}'s {service_name} booking
  as completed."
- `no_show_button` semantic label: "Mark {customer_name} as a no-show."
- `timeline_view` is a custom scroll view; it must provide a linear-accessible
  alternative. Each `booking_block` in the timeline is focusable with a semantic
  label: "{time}: {customer_name}, {service_name}, {status}."
- `queue_summary_card` semantic label: "{active_now_count} bookings in chair or
  up next. {total_today_count} bookings today. {remaining_count} remaining.
  {load_label}."
- All action buttons: 44pt minimum height (48pt preferred for frequently-used
  actions).

---

## Sheet: BookingDetailSheet

**Entry point:** Tapping `partner_booking_card` body or `booking_block` on timeline.

### Components

- `sheet_handle`: Drag indicator.
- `sheet_close_button`: X top-right (44pt).
- `sheet_title`: "Booking details".
- `customer_name_text`: Bold — customer name.
- `service_name_text`: Service name.
- `datetime_text`: Full date and time.
- `duration_text`: "{duration_minutes} min".
- `staff_name_text`: Staff member name, or "Staff TBD".
- `booking_ref_text`: Monospace booking reference.
- `status_chip`: Current status (colored chip).
- `action_row` (if `status = confirmed` and today's date):
  - `complete_button`: "Mark complete" — primary, full-width.
  - `no_show_button`: "No-show" — secondary outlined, full-width.

### Interactions

- Tap `complete_button` → dismiss sheet, show MarkCompleteConfirmation sheet.
- Tap `no_show_button` → dismiss sheet, show MarkNoShowConfirmation sheet.
- Tap `sheet_close_button` or swipe down → dismiss sheet. No action.

---

## Sheet: MarkCompleteConfirmation

**Entry point:** `complete_button` on `partner_booking_card` or BookingDetailSheet.

### Components

- `sheet_title`: "Mark as completed?".
- `confirmation_text`: "{customer_name}'s {service_name} appointment will be
  marked as completed. This will prompt the customer to leave a review."
- `booking_summary_line`: "{time} · {duration_minutes} min".
- `confirm_button`: "Mark complete" — primary (green fill), full-width, 52pt.
- `cancel_button`: "Cancel" — text button.

### Interactions

- Tap `confirm_button` → PATCH /bookings/{id}/complete. Show loading.
  - Success → dismiss sheet. Update `booking_status_chip` to "Completed" on
    the card and timeline block. Show toast: "Booking marked as completed.
    Customer will be prompted to review." (FR-C-RAT-01: system dispatches
    rating prompt after partner marks complete.)
  - Error → show inline error: "Couldn't mark complete. Try again." Re-enable.
- Tap `cancel_button` or swipe down → dismiss sheet. No change.

### Error / Edge States

- **Booking already completed:** "This booking is already marked as completed."
  Sheet closes, card updates.
- **Booking in wrong status (cancelled, no-show):** "This booking cannot be
  marked as completed." Sheet closes.

---

## Sheet: MarkNoShowConfirmation

**Entry point:** `no_show_button` on `partner_booking_card` or BookingDetailSheet.

### Components

- `sheet_title`: "Mark as no-show?".
- `warning_text`: "{customer_name} didn't show up? The slot will be released
  so other customers can book it. No review will be sent."
  (FR-P-DASH-04: no-show releases the slot and does not trigger a rating prompt.)
- `booking_summary_line`: "{time} · {service_name}".
- `confirm_button`: "Mark no-show" — destructive primary (amber fill), full-width.
- `cancel_button`: "Cancel" — text button.

### Interactions

- Tap `confirm_button` → PATCH /bookings/{id}/no-show. Show loading.
  - Success → dismiss sheet. Update card status to "No-show" (amber chip).
    Toast: "Marked as no-show. Slot released." (The slot is released — available
    for new bookings per FR-P-DASH-04.)
  - Error → inline error: "Couldn't update. Try again."
- Tap `cancel_button` or swipe down → dismiss without action.

### Error / Edge States

- **Booking already a no-show:** "This booking is already marked as no-show."
- **Booking in wrong status:** "This booking cannot be marked as no-show."

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Dashboard is the default tab (home screen) after login | Ramesh's primary daily use case is seeing his day's bookings at a glance (PRD Section 4.2: "See incoming bookings in one dashboard without needing to cross-reference a paper log"). Making this the landing screen is the correct default for his workflow. | Catalog as default — wrong for daily operational use; rejected. |
| Timeline is always today; date filter only changes the list | The timeline is a real-time operational view of today's appointments. Showing a timeline for a future date is useful for planning but adds complexity. MVP limits the timeline to today. The booking list filter allows checking future and past dates. | Future date timeline — noted as post-MVP enhancement. |
| No action buttons for past-date bookings | Late mark-complete would trigger a rating notification for a visit that occurred days ago, which is confusing for the customer. Preventing retroactive marking is the safer MVP default. | Allow retroactive mark-complete — risks stale rating prompts; deferred to post-MVP if use case is validated. |
| `booking_list` does not auto-refresh (pull-to-refresh only) | Auto-refreshing the list while the partner is reading it would cause disruption (items shifting, read state lost). Push notifications (FR-P-DASH-05) alert the partner to new bookings, so they know when to pull-refresh. | Auto-refresh list — disruptive; rejected. |
| Complete and no-show require confirmation sheets | Both actions are consequential and have downstream effects (rating prompt trigger, slot release). A confirmation step prevents accidental taps on the small action buttons. | Inline confirm (undo toast) — undo for "mark complete" triggering a customer rating prompt would be complex (need to suppress the notification). Confirmation sheet is cleaner. |
| Customer name visible in all booking views on the partner side | NFR-PRIV-03 explicitly permits this. The partner has a direct service relationship with the customer and needs the name to run their front desk. | Anonymize customer on partner side — contradicts NFR-PRIV-03 and breaks Ramesh's workflow entirely. |
