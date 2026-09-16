---
title: "UX Spec — Partner Salon Profile"
surface: "Salon Partner Mobile App (iOS + Android)"
flow: "Salon Profile Creation and Edit"
prd-refs: "FR-P-PROF-01, FR-P-PROF-02, FR-P-PROF-03"
created: 2026-09-05
---

# Partner Salon Profile Flow

## Overview

The Salon Profile screen allows the partner to create and edit their salon's
public-facing information: name, address, phone, and operating hours per day of
the week. Changes must propagate to the customer-facing discovery list and salon
detail view within 60 seconds (FR-P-PROF-03).

Profile completion is a prerequisite for the salon to appear in customer discovery
(FR-P-SVC-04: at least one service required; the profile itself must be complete
for the service requirement to be meaningful). The app routes a new partner with
no profile to profile creation before the dashboard.

---

## Screen: SalonProfile (View/Edit)

**Entry point:**
1. "Profile" tab in partner bottom navigation.
2. First login when no salon profile exists (create mode).

The same screen handles both create and edit modes. In create mode, all fields
are empty and the primary button says "Save profile". In edit mode, all fields
are pre-populated and the button says "Save changes". The structure is identical.

### Components

**Header**

- `back_button` (edit mode only): Chevron left. Returns to whichever screen
  navigated to Profile (e.g., Dashboard). Not shown in create mode (partner must
  save before accessing the rest of the app).
- `screen_title`: "Salon Profile".
- `edit_button` / `cancel_edit_button` (edit mode only): The profile can be
  displayed in a read-only view with an "Edit" button (top-right) that switches
  the screen to an editable state. While editing, an "X" cancel button appears.
  Cancelling discards unsaved changes and reverts to the read-only view.

Decision note: read-only + edit toggle is preferred over always-editable because
the partner frequently visits this screen to check their profile (e.g., to
confirm hours are correct). Always-editable creates accidental edits. However,
in **create mode** the screen is always editable — there is nothing to read-only.

**Salon Information section**

- `salon_name_field`: Text input. Label: "Salon name". Required. Max 100 chars.
  Placeholder: "e.g., Ramesh's Cuts & Style".
- `address_field`: Multi-line text input (2 rows). Label: "Street address".
  Required. Max 200 chars. Placeholder: "e.g., 42 Main Road, Koramangala".
  (Address is free-text in MVP — no map pin or address autocomplete required;
  noted as post-MVP enhancement.)
- `city_field`: Text input. Label: "City". Read-only display in MVP (fixed to
  the launch city — PRD Section 2: "single city, single locale"). Display the
  city name as non-editable text. If the launch city changes, this is a backend
  configuration change, not a UX change.
- `phone_field`: Numeric keyboard. Label: "Phone number". Max 10 digits. Prefix
  "+91" shown as non-editable text adjacent to field (same as customer PhoneEntry).
  Required.

**Operating Hours section**

- `hours_section_header`: "Operating Hours".
- `hours_instruction_text`: "Set your opening and closing times for each day.
  Mark days you're closed." (Shown in edit mode only, below header.)
- `day_hours_row` (one per day, Monday through Sunday):
  - `day_label`: "Monday", "Tuesday", etc. — fixed width, left-aligned.
  - `open_toggle`: Switch/checkbox — "Open". When OFF, the day is marked closed
    and `open_time_picker` and `close_time_picker` are disabled (greyed out).
  - `open_time_picker`: Time input. Label context: "Open". Display: "HH:MM AM/PM"
    or 24h format per device locale. Tapping opens a time picker dialog.
  - `separator_text`: "to" — between open and close pickers.
  - `close_time_picker`: Time input. Label context: "Close". Same time picker.

  Default state (new profile, create mode): all days default to closed (toggle
  OFF). Partner must explicitly set each day open.

  In read-only view: `day_hours_row` shows day name + "Closed" or "{open} –
  {close}" without interactive controls.

**Save section**

- `save_button`: "Save profile" (create mode) / "Save changes" (edit mode) —
  primary CTA, full-width, 52pt. At the bottom of the screen. Always visible
  (not sticky-bottom — the screen scrolls; the save button is at the end of
  the content, not fixed).
  Disabled when: (a) required fields are empty (in create mode), or (b) no
  changes have been made since last save (in edit mode).

### Interactions

**Create mode:**
- Partner fills fields and opens/closes days → `save_button` enabled when all
  required fields are non-empty (salon_name, address, phone). At least zero open
  days is valid on save (the salon can exist with all-closed hours, though it
  won't accept bookings until hours are set — the partner may save incrementally).
- Tap `save_button` → validate, then POST /businesses with profile data. Show
  loading spinner inside button, disable form.
  - Success → navigate to PartnerDashboard. A non-intrusive success banner:
    "Profile saved." is shown on the dashboard.
  - Error → show error (see below). Form re-enabled.

**Edit mode:**
- Tap `edit_button` → switch to editable state. Fields become interactive.
  `cancel_edit_button` appears.
- Make changes → `save_button` enabled.
- Tap `save_button` → validate, then PATCH /businesses/{id} with changed fields.
  - Success → switch back to read-only view. Changes are reflected immediately
    in the local state. Customer-facing propagation within 60 seconds (FR-P-PROF-03)
    is a backend responsibility; no UI acknowledgement of propagation time is
    needed beyond "Profile saved."
  - Error → show error (see below). Remain in editable state.
- Tap `cancel_edit_button` → revert fields to last saved values. Switch to
  read-only view. Confirm discard if more than one field was changed:
    DiscardChanges bottom sheet (see below).

**Time picker (all modes):**
- Tap `open_time_picker` or `close_time_picker` → open system time picker dialog
  (Flutter `showTimePicker`). After selection, value updates in the row.
- Toggling `open_toggle` OFF → `open_time_picker` and `close_time_picker` clear
  their values and become disabled. `Business.operating_hours[day] = null` on
  save (FR-P-PROF-01).
- Toggling `open_toggle` back ON → times remain blank; partner must set them.
  `save_button` is disabled until times are also set for the newly-enabled day
  (a day toggled ON but with no times set is an invalid state).

### Validation (FR-P-PROF-02)

All validation runs on save, not on every keystroke.

- `salon_name_field`: Required. Min 1 char (trimmed). Max 100 chars. Error:
  "Salon name is required."
- `address_field`: Required. Min 1 char (trimmed). Max 200 chars. Error:
  "Street address is required."
- `phone_field`: Required. Exactly 10 digits. Error: "Enter a valid 10-digit
  phone number."
- Per-day hours (for each day where `open_toggle` is ON):
  - Both `open_time_picker` and `close_time_picker` must be set. Error:
    "Set opening and closing times for {day_name}."
  - `close_time_picker` must be after `open_time_picker` (FR-P-PROF-02).
    Error: "Closing time must be after opening time for {day_name}."
- If multiple validation errors exist, show all errors simultaneously (one error
  message per failing field/day, displayed inline below the relevant control).
  Do not show one error at a time with the others hidden.

### Error / Edge States

- **Validation failure:** Inline error messages below each failing field. Scroll
  to the first error after tapping save.
- **Network failure on save:** "Couldn't save. Check your connection and try
  again." `save_button` re-enabled.
- **Server error (5xx):** "Something went wrong. Please try again."
- **Concurrent edit from another session (unlikely but possible):** If server
  returns 409 on PATCH (optimistic concurrency — Architect to implement if needed),
  show "Your profile was updated in another session. Reload to see the latest
  version." with a "Reload" button that fetches and displays current server data,
  discarding local edits. This is a safeguard; the Architect determines whether
  optimistic concurrency is implemented.

### Privacy / Accessibility

- Salon profile data is public-facing (visible in customer discovery and salon
  detail). No PII of individual customers is involved on this screen.
- Partner phone number is displayed to customers in the salon detail view
  (FR-C-DET-02 — "contact information as provided by the salon partner"). This
  is a voluntary business contact number.
- `salon_name_field` semantic label: "Salon name, required. Maximum 100 characters."
- `day_hours_row` semantic label (per day): "{day_name}. {Open toggle state: Open
  or Closed}. Opening time {value or not set}. Closing time {value or not set}."
- `open_toggle` announces state change: "{day_name} marked as {open/closed}."
- `save_button` disabled state: "Save profile. Fill in the required fields first."
- All `day_hours_row` items have ≥ 44pt height. Time pickers use system dialog
  which meets platform accessibility standards.

---

## Sheet: DiscardChanges

**Entry point:** Tapping `cancel_edit_button` when changes were made.

### Components

- `sheet_title`: "Discard changes?".
- `warning_text`: "Your unsaved changes will be lost."
- `discard_button`: "Discard changes" — destructive primary (red fill), full-width.
- `keep_editing_button`: "Keep editing" — secondary outlined, full-width.

### Interactions

- Tap `discard_button` → revert all field values to last-saved state. Switch to
  read-only view.
- Tap `keep_editing_button` or swipe down → dismiss sheet, remain in editable
  state with changes intact.

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Read-only view with explicit Edit button | Partners visit the profile screen to review hours, not always to change them. An always-editable screen risks accidental edits (especially for Ramesh who may show the screen to a customer on the device). | Always editable — rejected: accidental edit risk; confirmed-on-save would mitigate but adds friction. |
| All-closed default for new profiles | A new partner has not set hours yet. Defaulting to a specific set of hours (e.g., 9am–6pm Mon–Sat) would likely be wrong for many salons. A clean default forces explicit setup. | Default to a common schedule — likely wrong for many salon types; rejected. |
| City field is read-only in MVP | PRD Section 2: single city, single locale. No partner can change their city. Making it editable would be misleading. | Omit city field entirely — the customer-facing address must include city; the field must exist. |
| Validation shows all errors at once | Partners save after making many changes; discovering one error, fixing it, and discovering the next is frustrating (Ramesh is running a salon and has limited time). Show all errors at once so one save attempt reveals all issues. | Show first error only — creates a whack-a-mole experience. Rejected. |
| Address is free-text (no map/autocomplete) | PRD does not specify map integration for profile address. Address autocomplete requires a maps API. MVP keeps it simple. Noted as post-MVP enhancement. | Address autocomplete — post-MVP; adds external API dependency. |
