---
title: "UX Spec — Customer Salon Detail"
surface: "Customer Mobile App (iOS + Android)"
flow: "Salon Detail View — Live Queue, Offers, Reviews"
prd-refs: "FR-C-DET-01 through FR-C-DET-05, FR-C-BOOK-01, FR-C-AUTH-01, NFR-PRIV-01, NFR-PRIV-02, NFR-PRIV-03"
created: 2026-09-05
---

# Customer Salon Detail Flow

## Overview

The Salon Detail screen is the single screen that aggregates everything a customer
needs to evaluate a salon and initiate a booking. It is accessible unauthenticated
(FR-C-AUTH-01). The queue indicator on this screen is the highest-privacy-sensitivity
element in the customer-facing app; its information boundary is explicitly specified
below and must be enforced at the API layer.

---

## Screen: SalonDetail

**Entry point:** Tapping any `salon_card` in the DiscoveryList.

### Components

**Header section (above the fold)**

- `back_button`: Chevron left, top-left (44pt). Returns to DiscoveryList.
- `share_button`: Share icon, top-right (44pt). Share sheet with salon name and
  deep-link URL. (Post-MVP: implement if deep-link infrastructure is available;
  omit at MVP if not — share button hidden, not disabled.)
- `salon_name`: Large heading. Multi-line if needed.
- `address_text`: Full street address as stored in `Business.address` +
  `Business.city`.
- `phone_text`: Tappable phone number ("Call salon") — triggers `tel:` URI.
  Displayed as formatted Indian number (e.g., "+91 98765 43210"). Shown only if
  `Business.phone` is populated.
- `operating_hours_row`: Single summary line — "Open today {open_time}–{close_time}"
  or "Closed today". Tap to expand `operating_hours_expanded` section.
- `operating_hours_expanded` (collapsed by default): Per-day list showing each
  day of the week with open/close times or "Closed". Chevron on `operating_hours_row`
  indicates expanded/collapsed state.

**Queue and load section**

- `queue_indicator_card`: Full-width card with:
  - `queue_icon`: Clock or people icon (24pt).
  - `queue_count_text`: "{N} people ahead" where N is the current count of
    confirmed bookings in the live queue or ahead in the schedule. Wording
    options: "0 people ahead — walk right in", "1 person ahead",
    "{N} people ahead". (FR-C-DET-03 specifies "3 people ahead" as an example
    of the anonymized count format.)
  - `load_label`: Categorical label — "Quiet" | "Moderate" | "Busy" — same
    categories as the discovery list card, consistent labelling.
  - `refreshed_at_text`: "Updated just now" or "Updated {N} min ago". Timestamp
    is local-device-relative; the API response includes a `computed_at` UTC
    timestamp. Display as relative elapsed time. Auto-refreshes every 30 seconds
    while the screen is visible (a background GET to the queue endpoint only,
    not a full page reload).

**Privacy boundary for queue indicator:**
The `queue_count_text` and `load_label` are the only queue-related values
returned from the server for this customer-facing surface. The API response for
the queue indicator contains only:
- `queue_depth` (integer): count of confirmed bookings ahead of the current moment
- `load_category` (string enum: "quiet" | "moderate" | "busy")
- `computed_at` (UTC timestamp)

No booking IDs, customer names, scheduled times, service names, or any other
booking attribute is returned in this response. This is an API-layer enforcement
of NFR-PRIV-01 and NFR-PRIV-02, not a UI-layer soft constraint.

**Offers section**

- `offers_section_header`: "Offers & Deals" — section heading. Hidden entirely
  if no active offers exist for this salon (FR-P-OFFER-03: expired offers do not
  appear).
- `offer_card` (one per active offer, horizontal scroll or vertical list):
  - `offer_title`: Bold. Max display: 2 lines, truncated.
  - `offer_description`: Body text. Max display: 3 lines, "Show more" link if
    longer.
  - `offer_expiry_text`: "Valid until {date}" or "No expiry". Shown only if
    `Offer.expiry_date` is populated.
  - `offer_note`: Small caption — "Discount applied at salon on payment."
    (Persistent note — FR-P-OFFER-04: offers are informational only, discount
    is not applied in-app.)

**Service catalog section**

- `services_section_header`: "Services".
- `service_category_tabs` (optional, if salon has grouped services — post-MVP;
  MVP shows a flat list): omit tabs at MVP.
- `service_list`: Vertical list of `service_row` items.
  - `service_name`: Bold, primary.
  - `service_duration_text`: "{duration_minutes} min" — value from
    `Service.duration_minutes` (display duration, not `slot_duration_minutes`
    which is internal scheduling buffer; do not show buffer to customer).
  - `service_price_text`: "₹{price_inr}" — value from `Service.price_inr`.
    Integer display if no paise; 2 decimal places if non-zero paise.
  - `book_button`: "Book" — secondary outlined button, right-aligned on the row.
    44pt height. Tapping initiates booking for this specific service. One `book_button`
    per service row (FR-C-BOOK-01: customer selects one service to proceed).

**Ratings and reviews section**

- `ratings_section_header`: "Reviews".
- `average_rating_display`:
  - Large numeric rating: "{average_rating}" (1 decimal place — FR-C-RAT-06).
  - Star row: filled/partial/outline stars reflecting the average.
  - `review_count_text`: "Based on {count} review{s}".
  - Hidden entirely if `Business.average_rating` is null (no reviews yet).
- `review_list`: Vertical list of `review_card` items, most recent first
  (FR-C-DET-05).
  - `reviewer_attribution`: "Verified customer" — always. Never the customer's
    real name (FR-C-RAT-05, NFR-PRIV-01).
  - `review_stars`: 1–5 filled star icons.
  - `review_date`: Relative date — "3 days ago", "2 weeks ago", "6 months ago".
    Full date shown on tap (accessible via `Tooltip` or inline expand).
  - `review_text`: Body text of the written review. Max display: 3 lines,
    "Read more" inline link if truncated.
  - `verified_badge`: Small "Verified visit" chip (green tick). All reviews are
    tied to completed bookings — this badge is always present on all reviews in
    this MVP, and communicates that the review is from a genuine customer.
- `no_reviews_state`: Shown when `review_list` is empty — "No reviews yet. Be
  the first to review after your visit."
- `show_more_reviews_button`: "Show more reviews" — text button, shown when
  there are more reviews than the initial page (pageSize: 10). Loads next page
  inline (appends to list, no full-page navigation).

**Bottom CTA (sticky)**

- `book_now_cta`: Sticky bottom bar (sits above OS navigation area). Contains:
  - `cta_text`: "Book at {salon_name}".
  - `select_service_prompt`: "Select a service above to book." (shown when no
    service has been tapped; replaces with the actual book button once a service
    is tapped — see interaction below).
  
  Decision note: the sticky CTA at the bottom is an alternative booking entry
  point for users who scroll to the bottom without tapping a specific service's
  "Book" button. Tapping it scrolls the screen to `service_list` and highlights
  the section with a brief pulse animation. It does not initiate booking until
  a service is selected.

### Interactions

- Tap `back_button` → pop to DiscoveryList (current scroll position preserved
  in DiscoveryList's BLoC state).
- Tap `operating_hours_row` → toggle `operating_hours_expanded` in-place.
- Tap `phone_text` → launch `tel:+91XXXXXXXXXX` URI (OS call dialog).
- Tap `book_button` on a service row → if authenticated, navigate to SlotPicker
  screen for that service. If not authenticated, show AuthGate modal (FR-C-AUTH-01).
  The selected service is held in BLoC state during auth; after auth, SlotPicker
  opens automatically.
- Tap `book_now_cta` (when no service selected) → scroll to `service_list` with
  animated highlight.
- Tap `show_more_reviews_button` → load next page of reviews, append to list.
- Auto-refresh queue indicator → every 30 seconds while screen is in foreground,
  fire a background GET to the queue endpoint. Update `queue_count_text`,
  `load_label`, `refreshed_at_text` without full page reload (BLoC emits a partial
  state update). The rest of the screen does not re-render.
- App goes to background while SalonDetail is visible → cancel auto-refresh timer.
  Resume timer when app returns to foreground.

### Error / Edge States

- **Initial load failure (full screen):** Show error state with salon name if
  available from list, body "Couldn't load salon details. Check your connection."
  Retry button. Back button still functional.
- **Queue indicator load failure:** Show `queue_indicator_card` with
  `queue_count_text` = "Queue info unavailable" and omit `load_label`. Do not
  show a count of 0 (which would be misleading). `refreshed_at_text` = "Couldn't
  update — tap to retry". Tapping the card manually retries the queue fetch.
- **No active offers:** `offers_section_header` and offer cards are hidden entirely.
  No "no offers" placeholder.
- **Empty catalog (salon has no services):** Service section shows "This salon
  hasn't added services yet." `book_button` does not appear. `book_now_cta`
  is hidden. (Per FR-P-SVC-04, the salon should not appear in discovery without
  a service, but this guards against a race condition where the last service is
  deleted after discovery.)
- **Salon marked as closed today:** `operating_hours_row` shows "Closed today".
  `queue_indicator_card` shows "Closed today — no queue." `book_button` remains
  visible so the customer can book a future slot (slot picker will show available
  future dates, not today's).
- **No reviews yet:** Show `no_reviews_state` text. Average rating display hidden.
- **Offer description exceeds 3 lines:** Truncate with "Show more" inline link.
  Tapping "Show more" expands the full text in-place (no navigation). "Show less"
  link collapses it.
- **Reviews page load failure:** Show inline "Couldn't load more reviews. Try
  again." below the last visible review.

### Privacy / Accessibility

**Queue indicator information boundary (NFR-PRIV-01, NFR-PRIV-02):**

- The `queue_count_text` shows only an integer count of people ahead. It does
  not name any person, time, service, or booking reference.
- The API endpoint serving this data returns only `queue_depth`, `load_category`,
  and `computed_at`. The full booking list is never returned to any customer-facing
  client — only the aggregate.
- Developer implementation note: the queue endpoint must be a separate API call
  from the booking list endpoint. Do not return the booking list and aggregate
  client-side — aggregate server-side and return only the aggregate.

**Review attribution (NFR-PRIV-01, FR-C-RAT-05):**

- All reviews are attributed to "Verified customer". The reviewer's name is stored
  server-side but is never transmitted to the customer-facing API for the reviews
  list.
- The `rating_row` semantic label: "Verified customer, {N} stars, {relative_date}.
  {review_text if present}."

**General accessibility:**

- `book_button` per service row: semantic label — "Book {service_name}, {price},
  {duration} minutes."
- `operating_hours_expanded` announces state: "Operating hours, expanded" /
  "Operating hours, collapsed."
- `queue_indicator_card` semantic label: "{N} people ahead. {load_label}. Updated
  {relative time}."
- `offer_card` semantic label: "{offer_title}. {offer_description}. {expiry if
  present}. Discount applied at salon."
- All star ratings use a numeric-first semantic label: "Rating: {N} out of 5
  stars." (Prevents ambiguity when star icons are read individually.)
- Minimum tap targets: all interactive elements ≥ 44pt.
- SalonDetail is a long-scroll screen; it must pass accessibility scroll audit
  (no content clipped by sticky bottom bar — bottom of page has padding equal to
  `book_now_cta` height + safe area).

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Queue indicator auto-refreshes every 30 seconds, not real-time WebSocket | Slot availability is REST-only (base-rules.md §3.6). The WebSocket channel from the server is for queue aggregate updates only; however, the stack spec states this is a Redis Pub/Sub relay. At MVP, polling every 30 seconds is a safe and simpler implementation that avoids the need for a WebSocket connection on the customer side. WebSocket push is noted as a post-MVP enhancement if polling latency is unacceptable. | WebSocket subscription — acceptable per backend spec but adds client complexity; deferred to post-MVP. Real-time slot push — explicitly prohibited (base-rules.md §3.6). |
| `slot_duration_minutes` not shown to customer | `slot_duration_minutes` is an internal scheduling buffer configured by the partner. Showing it to the customer is confusing ("haircut takes 30 min, slot is 45 min") and is not required by any PRD requirement. Customers see `duration_minutes` only. | Show slot duration — rejected: not a PRD requirement, creates confusion. |
| Offers use "Discount applied at salon" disclaimer | PRD FR-P-OFFER-04: offers are informational; no in-app discount calculation. The disclaimer prevents customers arriving with incorrect price expectations. | No disclaimer — rejected: creates partner trust issues and support burden when customers dispute prices. |
| Book buttons are per-service-row, not a single "Book" action | PRD FR-C-BOOK-01: customer selects one service and proceeds. Having one button per service row makes the selection action and the booking action a single gesture. A separate service selection step and then a global Book button would add a tap. | Two-step (select service, then tap Book) — higher friction; eliminated a tap for Priya's scenario where she knows what she wants. |
| Sticky bottom CTA scrolls to service list rather than booking | When no service is selected, a sticky "Book" CTA that leads to an error state ("select a service first") is confusing. Scrolling to the service list is the correct next action. | Sticky "Book" showing error on tap — rejected: error on a CTA is a bad pattern; the CTA should guide the user. |
