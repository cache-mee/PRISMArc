---
title: "UX Spec — Customer Ratings"
surface: "Customer Mobile App (iOS + Android)"
flow: "Rating Prompt After Completed Visit + Review Submission"
prd-refs: "FR-C-RAT-01 through FR-C-RAT-06, NFR-PRIV-01"
created: 2026-09-05
---

# Customer Ratings Flow

## Overview

Ratings are strictly tied to completed bookings (FR-C-RAT-01, FR-C-RAT-04).
The prompt appears only after the salon partner marks a booking as completed
in the partner app. Only one rating per booking is permitted (FR-C-RAT-03).
Reviews are attributed to "Verified customer" — never the customer's real name
(FR-C-RAT-05, NFR-PRIV-01).

---

## Trigger: RatingPrompt

**Entry point (two surfaces):**

1. **Push notification** (primary path): The system dispatches a push notification
   after the partner marks a booking complete. Notification text: "How was your
   visit at {salon_name}? Share your feedback." Tapping the notification deep-links
   to the RatingSubmission screen for that booking.
2. **In-app prompt** (secondary path): When the customer opens the app and has
   a completed, unrated booking, a non-intrusive banner or card appears at the top
   of the BookingList "Past" tab and on the BookingDetail screen for that booking.
   The `rate_now_button` on BookingDetail also serves this path (see
   customer-booking-management.md).

Decision note: the push notification is the primary mechanism to drive ratings
after a visit. In-app surfaces serve customers who return to the app organically.
Both paths lead to the same RatingSubmission screen.

### RatingPrompt Banner (in-app, BookingList "Past" tab)

- `banner_card`: Appears above the list, full-width, distinct background color
  (light amber/warm tone to signal a positive request, not an alert).
  - `banner_icon`: Star icon, 24pt.
  - `banner_text`: "How was your visit to {salon_name}?" (if one pending rating).
    "You have {N} visits to rate." (if multiple).
  - `rate_now_link`: "Rate now" — text button, right-aligned. Tapping navigates
    to RatingSubmission for the most recent pending-rating booking.
  - `dismiss_icon`: X button, 44pt, top-right of card. Dismisses the banner for
    the current session only. The `rate_now_button` on BookingDetail remains
    accessible.

---

## Screen: RatingSubmission

**Entry point:**
- Tap push notification for a completed booking.
- Tap `rate_now_button` on BookingDetail.
- Tap `rate_now_link` in RatingPrompt Banner.

### Components

- `back_button`: Chevron left (44pt). Returns to the originating screen (BookingDetail,
  BookingList, or app root if opened from notification cold-start).
- `screen_title`: "Rate your visit".
- `visit_summary_card`: Non-interactive, top of screen:
  - `salon_name_text`: Salon name.
  - `service_name_text`: Service name.
  - `visit_date_text`: "{Day}, {Date}".
- `rating_instruction_text`: "How would you rate your experience?"
- `star_selector`: Row of 5 large star icons (min 48pt each, with sufficient
  spacing for touch accuracy — stars should be at least 52pt wide with 8pt gap).
  - Initial state: all outline (no stars selected).
  - Tap Nth star → fill stars 1 through N with primary color; outline stars N+1
    through 5. Tapping a filled star deselects: if star N is tapped when all ≤ N
    are filled, deselect all stars (reset to 0). This allows the customer to clear
    a misselection.
  - `rating_label_text`: Dynamic text below stars describing the selected rating.
    0 stars (none): empty / hidden.
    1 star: "Poor".
    2 stars: "Fair".
    3 stars: "Good".
    4 stars: "Great".
    5 stars: "Excellent".
- `review_section_header`: "Add a comment (optional)".
- `review_text_field`: Multi-line text input. Placeholder: "Tell us about your
  experience..." Max length: 500 characters (FR-C-RAT-02). Character counter
  shown below field: "{N}/500". Character counter becomes visible when the customer
  begins typing.
- `submit_button`: "Submit review" — primary CTA, full-width, 52pt. Disabled
  until at least 1 star is selected. Star selection is the only required input;
  `review_text_field` is optional.
- `skip_link`: "Skip for now" — text button, centered below `submit_button`.
  Navigates back without submitting. The rating prompt will re-appear in the
  banner but not re-trigger a push notification.

### Interactions

- Tap a star → update `star_selector` and `rating_label_text`. `submit_button`
  becomes enabled.
- Tap the same star as currently the highest selected → deselect all (reset to 0
  stars). `submit_button` returns to disabled.
- Type in `review_text_field` → character counter increments. Field enforces
  `maxLength: 500` (Flutter `TextField.maxLength`).
- Tap `submit_button` (at least 1 star selected) → POST /ratings with:
  - `booking_id`: the booking being rated.
  - `stars`: integer 1–5.
  - `review_text`: string or null (if `review_text_field` is empty).
  Show loading spinner inside `submit_button`, disable inputs.
  - Success → navigate to RatingConfirmation screen.
  - Error → show inline error (see below).
- Tap `skip_link` → pop to originating screen. No rating submitted.
- Tap `back_button` → same as `skip_link`.

### Validation

- `stars`: Required, must be 1–5. Enforced client-side by disabling `submit_button`
  when 0 stars. Server also rejects `stars = 0` with a 400 error.
- `review_text`: Optional. Max 500 chars enforced by `maxLength`. Server also
  validates max 500 chars and returns 400 if exceeded (should not occur with
  client enforcement).
- One rating per booking: enforced server-side. If a rating already exists for
  `booking_id`, server returns 409. Client-side, the `rate_now_button` on
  BookingDetail is hidden after rating submission; this state persists via
  the booking's rating status in BLoC state.

### Error / Edge States

- **Network failure on submit:** Re-enable inputs. Inline error below
  `submit_button`: "Couldn't submit. Check your connection and try again."
  Stars and typed text preserved.
- **409 — rating already exists for this booking:** "You've already rated this
  visit." Navigate back to BookingDetail. (This should not occur in normal flow
  but guards against double submission via notification tap.)
- **400 — booking not in completed state (FR-C-RAT-04):** "You can only rate
  a completed visit." Navigate back. (Should not occur if the trigger is correct,
  but guards against race conditions.)
- **Server error (5xx):** "Couldn't submit your review. Please try again later."
  Inputs re-enabled.
- **App opened via stale notification (booking already rated):** RatingSubmission
  opens, immediately detects existing rating from the API and shows:
  "You've already submitted a review for this visit." with a "Close" button.
  No rating controls shown.

### Privacy / Accessibility

**Attribution boundary (NFR-PRIV-01, FR-C-RAT-05):**
- The submitted rating is stored server-side with `customer_id` and displayed
  publicly as "Verified customer". The customer's name is never transmitted to
  any customer-facing API for the review display.
- The `review_text` is the customer's own free-text input. It is displayed
  publicly on the salon's detail page. A note in the UI makes this clear:
  below `review_text_field`, a small caption: "Your comment will be visible
  to everyone as 'Verified customer'." This sets the correct expectation
  without alarming the customer.

**Accessibility:**
- `star_selector` stars: semantic label — "Rate {N} out of 5 stars" when
  selecting. Row container announces: "Star rating, required. Currently {N}
  stars selected." or "Star rating, required. No stars selected."
- Each star has a semantic label: "1 star — Poor", "2 stars — Fair", etc.
  Screen reader does not just read "star icon".
- `rating_label_text` changes are announced via `LiveRegion` (Flutter
  `Semantics(liveRegion: true)`).
- `review_text_field` semantic label: "Optional comment, maximum 500 characters.
  {N} characters used."
- `submit_button` disabled state: "Submit review. Select a star rating first."
- `skip_link` semantic label: "Skip rating for now and return."
- Star icons are minimum 48pt with 8pt gaps — total interactive width per star
  ≥ 56pt including gap.

---

## Screen: RatingConfirmation

**Entry point:** Successful POST /ratings.

### Components

- `success_icon`: Animated star fill (or checkmark — same Lottie/Flutter animation
  approach as BookingConfirmation). Static star after animation.
- `headline`: "Thanks for your feedback!".
- `subtext`: "Your review helps other customers find great salons."
- `submitted_rating_display`: Read-only star row showing the submitted rating
  (filled stars 1–N, outline N+1–5) + `rating_label_text` for the submitted value.
- `submitted_review_text`: The submitted `review_text` displayed as a blockquote,
  if the customer provided text. Hidden if `review_text` was empty.
- `done_button`: "Done" — primary CTA, full-width, 52pt. Returns to BookingDetail
  (or BookingList if BookingDetail is not in the navigation stack).

### Interactions

- Tap `done_button` → pop to BookingDetail or BookingList.
- OS back → same as `done_button` (RatingSubmission no longer accessible —
  rating is submitted and cannot be changed per FR-C-RAT-03).

### Error / Edge States

- No error states — screen only appears after a confirmed successful submission.

### Privacy / Accessibility

- `submitted_review_text` (if shown) announces: "Your comment: {text}."
- `success_icon` animation respects "Reduce Motion" OS setting.
- `done_button` semantic label: "Done. Return to your booking."

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Star selection is the only required field; review text is optional | PRD FR-C-RAT-02: "a rating on a 1-to-5 star scale, with an optional written review." This is the exact requirement. Requiring a review text would reduce submission rate (Priya is time-pressed and may not write a comment). | Required text — directly contradicts FR-C-RAT-02. |
| Tap filled highest star to deselect all (reset to 0) | On mobile, misselecting a star is easy. A reset mechanism prevents frustration without adding a separate "Clear" button. The pattern of re-tapping the highest selected star is a common mobile idiom. | Separate "Clear rating" button — more UI elements; tapping the star is more direct. |
| Attribution caption shown in the submission form | Customers should know their review will appear publicly before they type it, not after. This is a transparency measure. | Show attribution only on the published review — too late; customer's expectation is already set at submission. |
| No re-rating after submission | PRD FR-C-RAT-03 is unambiguous: one rating per booking. No override in the UX. | Allow editing — directly contradicts FR-C-RAT-03. |
| Push notification is the primary rating trigger | The goal is high review submission rate (PRD Section 3, "Customer review submission rate" success metric). A push notification immediately after the visit, when the experience is fresh, is the highest-conversion trigger. The in-app banner is a fallback. | In-app only — lower conversion; customers who don't re-open the app immediately miss the prompt. |
| "Skip for now" label (not "Skip forever") | The customer can still rate later via BookingDetail. Using "Skip for now" is honest — the opportunity does not disappear. "Skip" alone could be read as a permanent dismissal. | "Don't rate" — implies permanence, which is incorrect. |
