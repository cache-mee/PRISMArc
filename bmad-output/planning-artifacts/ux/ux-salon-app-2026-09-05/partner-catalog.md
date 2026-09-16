---
title: "UX Spec — Partner Service Catalog and Offers"
surface: "Salon Partner Mobile App (iOS + Android)"
flow: "Service Catalog Management + Offers & Discounts"
prd-refs: "FR-P-SVC-01 through FR-P-SVC-05, FR-P-OFFER-01 through FR-P-OFFER-04"
created: 2026-09-05
---

# Partner Catalog Flow

## Overview

The catalog section has two sub-flows: Services (the salon's bookable service
list with pricing and duration) and Offers (promotional information displayed
to customers). Services drive slot computation; the `slot_duration_minutes` field
controls scheduling buffer and is distinct from `duration_minutes` (the display
duration shown to customers). Offers are informational only and no in-app discount
is applied (FR-P-OFFER-04).

---

## Screen: CatalogHome

**Entry point:** "Catalog" tab in partner bottom navigation.

### Components

- `screen_title`: "Catalog".
- `tab_bar`: Two tabs:
  - "Services" (default selected).
  - "Offers".
- Content area switches between ServiceList and OfferList based on active tab.

---

## Screen: ServiceList (within CatalogHome, "Services" tab)

### Components

- `add_service_button`: Floating action button (FAB) or top-right "Add service"
  text button. Navigates to ServiceForm (create mode).
- `service_list`: Vertical list of `service_row` items.
  - `service_name_text`: Bold.
  - `service_duration_text`: "{duration_minutes} min".
  - `service_price_text`: "₹{price_inr}".
  - `edit_button`: Pencil icon (44pt tap target), right-aligned. Navigates to
    ServiceForm (edit mode) for that service.
  - `delete_button`: Trash icon (44pt tap target), rightmost. Triggers delete
    confirmation.
  - `inactive_badge`: "Hidden from customers" — small chip shown if `Service.active
    = false`. This state occurs after a service is "deleted" (soft-delete sets
    active = false; FR-P-SVC-03: existing bookings are unaffected).
- `empty_state`: Shown when no services exist — "No services yet. Add your
  first service to get started." with an "Add service" button.
- `visibility_note`: Caption at bottom of list — "Your salon only appears to
  customers once you have at least one service." (FR-P-SVC-04.) Shown only when
  the service count is 0.

### Interactions

- Tap `add_service_button` → navigate to ServiceForm (create mode).
- Tap `edit_button` on a row → navigate to ServiceForm (edit mode) for that
  service.
- Tap `delete_button` → show DeleteServiceConfirmation bottom sheet.
- Tap anywhere on the row body (not buttons) → navigate to ServiceForm (edit mode).
  This provides a generous tap surface to reach the edit form.

### Error / Edge States

- **Load failure:** "Couldn't load services. Check your connection." with retry.
- **No services:** Empty state with `visibility_note`.

### Privacy / Accessibility

- Service data is public-facing (shown to customers). No PII involved.
- `service_row` semantic label: "{service_name}, {duration} minutes, ₹{price}.
  Double-tap to edit."
- `delete_button` semantic label: "Delete {service_name}."
- `edit_button` semantic label: "Edit {service_name}."

---

## Screen: ServiceForm (Create / Edit)

**Entry point:**
- "Add service" button from ServiceList (create mode).
- `edit_button` or row tap on ServiceList (edit mode).

### Components

- `back_button`: Chevron left. Returns to ServiceList. If changes have been made
  unsaved, shows DiscardChanges confirmation (same sheet pattern as partner-profile.md).
- `screen_title`: "Add service" (create) / "Edit service" (edit).
- `service_name_field`: Text input. Label: "Service name". Required. Max 100 chars.
  Placeholder: "e.g., Haircut, Beard Trim, Hair Color".
- `duration_field`: Numeric keyboard. Label: "Service duration (minutes)".
  Required. Positive integer only. Placeholder: "e.g., 30". This is `Service.duration_minutes`
  — the displayed duration customers see.
- `slot_duration_field`: Numeric keyboard. Label: "Slot duration (minutes)".
  Required. Positive integer only. Placeholder: "Same as service duration if
  no buffer needed." Hint text below field: "Include any prep or cleanup time.
  E.g., if a 30-min haircut needs 10 min cleanup, set 40 min."
  Defaults to the value of `duration_field` when `duration_field` is filled and
  `slot_duration_field` has not been manually changed. Partners can override.
  This is `Service.slot_duration_minutes` — used by the slot engine.
- `price_field`: Numeric keyboard with decimal support. Label: "Price (₹)".
  Required. Positive value. Placeholder: "e.g., 250". Prefix "₹" shown as
  non-editable text. All prices in INR (FR-P-SVC-05).
- `save_button`: "Save service" (create) / "Save changes" (edit) — primary CTA,
  full-width, 52pt. At bottom of screen.

### Interactions

- Fill fields → `save_button` enabled when all required fields are non-empty and
  valid.
- `duration_field` filled for the first time AND `slot_duration_field` is still
  empty or equal to the previous `duration_field` value → auto-populate
  `slot_duration_field` with the same value.
- `slot_duration_field` manually changed by the partner → no longer auto-populated
  from `duration_field` (user has expressed intent; respect it).
- Tap `save_button` → validate, then:
  - Create mode: POST /services.
  - Edit mode: PATCH /services/{id}.
  Show loading state. On success → return to ServiceList. On error → show error.

### Validation

Run on save (not per-keystroke).

- `service_name_field`: Required. Min 1 char (trimmed). Max 100 chars. Error:
  "Service name is required."
- `duration_field`: Required. Must be a positive integer (≥ 1). Error: "Enter
  a duration in minutes (whole number, at least 1)."
- `slot_duration_field`: Required. Must be a positive integer ≥ `duration_field`
  value. Error if less than duration: "Slot duration must be at least as long as
  the service duration ({N} min)." Rationale: a slot shorter than the service
  itself would guarantee scheduling conflicts.
- `price_field`: Required. Must be a positive value (> 0). Max 2 decimal places.
  Error: "Enter a valid price greater than 0."

### Error / Edge States

- **Duplicate service name:** Server returns 400. Inline error below
  `service_name_field`: "A service with this name already exists."
- **Network failure:** "Couldn't save. Check your connection." Re-enable form.
- **Edit: service has active bookings (informational only):** When editing a
  service that has upcoming confirmed bookings, show an informational banner at
  the top of the form: "Changes to price or duration will apply to new bookings
  only. Existing bookings are not affected." This is an advisory note, not a
  blocking error. (FR-P-SVC-03: removing a service does not cancel existing
  bookings; same principle applies to edits.)

### Privacy / Accessibility

- `service_name_field` semantic label: "Service name, required. Maximum 100
  characters."
- `duration_field` semantic label: "Service duration in minutes, required.
  This is the time shown to customers."
- `slot_duration_field` semantic label: "Slot duration in minutes, required.
  Include buffer time. Defaults to service duration."
- `price_field` semantic label: "Service price in Indian Rupees, required."
- `save_button` disabled state: "Save service. Fill in all required fields."

---

## Sheet: DeleteServiceConfirmation

**Entry point:** `delete_button` on a ServiceList row.

### Components

- `sheet_title`: "Remove service?".
- `warning_text`: "'{service_name}' will no longer appear to customers. Existing
  bookings for this service will not be affected." (FR-P-SVC-03.)
- `remove_button`: "Remove service" — destructive primary (red), full-width, 52pt.
- `keep_button`: "Keep service" — secondary outlined, full-width, 52pt.

### Interactions

- Tap `remove_button` → PATCH /services/{id} setting `active = false` (soft-
  delete). On success: service row disappears from ServiceList (or shows
  `inactive_badge` if the partner needs to see it for reference — design choice:
  at MVP, hide inactive services from the list; the partner can re-add if needed).
  Show toast: "'{service_name}' removed from catalog."
- Tap `keep_button` or swipe down → dismiss without action.

---

## Screen: OfferList (within CatalogHome, "Offers" tab)

### Components

- `add_offer_button`: FAB or "Add offer" top-right button. Navigates to OfferForm
  (create mode).
- `offer_list`: Vertical list of `offer_card` items.
  - `offer_title_text`: Bold.
  - `offer_description_text`: 2 lines max, truncated.
  - `expiry_text`: "Expires {date}" or "No expiry". If expired: "Expired {date}"
    in red.
  - `active_badge`: "Active" (green chip) or "Expired" (grey chip).
  - `edit_button`: Pencil icon, 44pt.
  - `delete_button`: Trash icon, 44pt.
- `informational_note`: Banner at top of tab (always visible) — "Offers are shown
  to customers as promotional information. Discounts are applied manually at the
  salon on payment." (FR-P-OFFER-04.) This note prevents partner confusion about
  in-app discount application.
- `empty_state`: "No offers yet. Add a promotional offer to attract customers."

### Interactions

- Tap `add_offer_button` → navigate to OfferForm (create mode).
- Tap `edit_button` → navigate to OfferForm (edit mode).
- Tap `delete_button` → show DeleteOfferConfirmation sheet.
- Tap row body → navigate to OfferForm (edit mode).

---

## Screen: OfferForm (Create / Edit)

**Entry point:**
- "Add offer" from OfferList (create mode).
- `edit_button` or row tap on OfferList (edit mode).

### Components

- `back_button`: Returns to OfferList. Discard confirmation if unsaved changes.
- `screen_title`: "Add offer" / "Edit offer".
- `offer_title_field`: Text input. Label: "Offer title". Required. Max 100 chars.
  Placeholder: "e.g., 20% off haircut this weekend".
- `offer_description_field`: Multi-line text input. Label: "Description". Required.
  Max 500 chars. Character counter visible when typing. Placeholder: "Describe the
  offer, any conditions, and how the customer can claim it."
- `expiry_date_section`:
  - `no_expiry_toggle`: Switch — "No expiry date". Default ON for new offers
    (FR-P-OFFER-01: expiry date is optional).
  - `expiry_date_picker`: Date picker field (disabled when `no_expiry_toggle`
    is ON). Label: "Valid until". Tapping opens a date picker dialog (calendar
    view). Only future dates are selectable; past dates are greyed out.
  - When `no_expiry_toggle` OFF: `expiry_date_picker` becomes active.
- `save_button`: "Save offer" / "Save changes" — primary CTA, full-width, 52pt.

### Interactions

- Fill fields → `save_button` enabled when required fields are non-empty.
- Toggle `no_expiry_toggle` OFF → `expiry_date_picker` becomes active, partner
  must select a date.
- Toggle `no_expiry_toggle` ON → `expiry_date_picker` clears and disables.
- Tap `save_button` → validate, then POST /offers (create) or PATCH /offers/{id}
  (edit). On success → return to OfferList.

### Validation

- `offer_title_field`: Required. Max 100 chars. Error: "Offer title is required."
- `offer_description_field`: Required. Max 500 chars. Error: "Description is
  required."
- `expiry_date_picker` (when `no_expiry_toggle` is OFF): Required to have a date.
  Must be today or a future date. Error: "Select a future expiry date."

### Error / Edge States

- **Network failure:** "Couldn't save. Check your connection."
- **Creating offer when profile is incomplete:** Not blocked at catalog level —
  the partner can create offers at any time. However, offers only appear to
  customers when the salon is live (profile complete, at least one service).

---

## Sheet: DeleteOfferConfirmation

**Entry point:** `delete_button` on an OfferList row.

### Components

- `sheet_title`: "Delete offer?".
- `warning_text`: "'{offer_title}' will be removed and will no longer appear to
  customers."
- `delete_button`: "Delete offer" — destructive primary (red), full-width.
- `keep_button`: "Keep offer" — secondary outlined, full-width.

### Interactions

- Tap `delete_button` → DELETE /offers/{id} (or set `Offer.active = false`).
  On success: offer removed from OfferList. Toast: "Offer deleted."
- Tap `keep_button` or swipe down → dismiss without action.

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| `slot_duration_minutes` shown to partner separately from `duration_minutes` | FR-P-SCHED-01 explicitly requires the partner to configure slot duration per service. Making this a separate field on the ServiceForm (rather than a hidden Schedule screen) is more discoverable and directly tied to the service it affects. | Separate Schedule screen only — less discoverable; partner may not realize it exists. |
| `slot_duration_field` defaults to `duration_field` value | Most services need no buffer. Making the partner fill out a separate buffer field when they just want the standard duration adds friction. Auto-defaulting and allowing override is the right balance. | No default — every partner must manually set slot duration; unnecessary friction. |
| Slot duration must be ≥ service duration (validation rule) | A slot shorter than the service itself is logically inconsistent and would produce overlapping bookings. This is a hard validation error, not a warning. | Warning only — allows creation of invalid schedules; rejected on data integrity grounds. |
| Offers show a persistent "pay at salon" banner | FR-P-OFFER-04 is an MVP constraint. Without this banner, partners may expect the system to apply their discount automatically and will troubleshoot phantom issues. The banner sets the correct expectation once and permanently. | No banner — higher partner confusion and support burden during MVP. |
| Inactive services hidden from ServiceList (after delete) | Partners are managing active services. Showing deactivated services clutters the list. If a partner needs to reactivate, they can re-add the service. The soft-delete preserves existing booking integrity server-side. | Show inactive services with badge — clutters list; the main management view should show actionable items only. |
