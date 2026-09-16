---
title: "UX Spec — Partner Staff Management"
surface: "Salon Partner Mobile App (iOS + Android)"
flow: "Add/Edit/Remove Staff, Working Hours"
prd-refs: "FR-P-STAFF-01 through FR-P-STAFF-05"
created: 2026-09-05
---

# Partner Staff Management Flow

## Overview

Staff management allows the partner to maintain their team: who works at the
salon, what services each staff member can perform, and what hours they work
each day. Staff working hours must fall within the salon's configured operating
hours (FR-P-STAFF-04, FR-P-STAFF-05). Removing a staff member does not cancel
existing confirmed bookings for that person (FR-P-STAFF-03).

The open architectural question — whether a booking is assigned to a specific
staff member at booking time or service time (PRD Section 10) — affects slot
computation but does not affect the staff management UX itself. This spec
documents the staff data (who, what services, what hours) without prescribing
how slot assignment uses it.

---

## Screen: StaffList

**Entry point:** "Staff" tab in partner bottom navigation.

### Components

- `screen_title`: "Staff".
- `add_staff_button`: FAB or "Add staff member" top-right button.
  Navigates to StaffForm (create mode).
- `staff_list`: Vertical list of `staff_card` items.
  - `staff_name_text`: Bold. Staff member's name.
  - `services_summary_text`: Comma-separated list of `qualified_service_ids`
    resolved to service names. If > 3 services: "Haircut, Beard Trim, +2 more".
  - `schedule_summary_text`: Compact hours summary. Example: "Mon–Fri
    9:00 AM – 6:00 PM, Sat 10:00 AM – 4:00 PM, Sun Closed." If hours are
    not yet configured: "No schedule set" in amber to signal incomplete setup.
  - `edit_button`: Pencil icon, 44pt. Navigates to StaffForm (edit mode).
  - `remove_button`: Trash icon, 44pt. Triggers RemoveStaffConfirmation sheet.
  - `inactive_badge`: "Removed" chip if `Staff.active = false` (soft-deleted).
    At MVP: hide inactive staff from the list (same rationale as services).
- `empty_state`: "No staff members yet. Add your team to manage their schedules."

### Interactions

- Tap `add_staff_button` → navigate to StaffForm (create mode).
- Tap `edit_button` or row body → navigate to StaffForm (edit mode).
- Tap `remove_button` → show RemoveStaffConfirmation sheet.

### Error / Edge States

- **Load failure:** "Couldn't load staff. Check your connection." Retry button.
- **No staff:** Empty state.
- **Staff with no services assigned:** `services_summary_text` shows "No
  services assigned" in amber. This is a warning state — a staff member with
  no services cannot be assigned to any booking.
- **Staff with incomplete schedule:** `schedule_summary_text` shows "No
  schedule set" in amber. Warns partner that this staff member has no available
  hours configured.

### Privacy / Accessibility

- Staff data is internal to the partner. It is not exposed to customers
  (customers do not see staff names on the customer app — assignment is
  handled behind the scenes).
- `staff_card` semantic label: "{staff_name}. Services: {services_summary}.
  Schedule: {schedule_summary}. Double-tap to edit."
- `remove_button` semantic label: "Remove {staff_name}."

---

## Screen: StaffForm (Create / Edit)

**Entry point:**
- "Add staff member" from StaffList (create mode).
- `edit_button` or row tap on StaffList (edit mode).

The form is organized into two logical sections: basic info and schedule.
On mobile, these are presented as a single scrollable form (not tabs) to
keep the form structure simple for Ramesh's use case (adding one staff member
at a time on a mobile device).

### Components

**Basic Information section**

- `back_button`: Returns to StaffList. Discard confirmation if unsaved changes.
- `screen_title`: "Add staff member" / "Edit staff member".
- `staff_name_field`: Text input. Label: "Name". Required. Max 100 chars.
  Placeholder: "e.g., Deepa, Suresh".

**Services section**

- `services_section_header`: "Services this person can perform".
- `services_instruction_text`: "Select the services this staff member is qualified
  to do." (edit mode: always shown; create mode: shown).
- `service_checkbox_list`: List of all active services in the salon's catalog.
  Each row:
  - `service_checkbox`: Checkbox (44pt tap target including label area).
  - `service_name_label`: Service name.
  - `service_detail_label`: "{duration_minutes} min · ₹{price_inr}" — sub-text.
- `no_services_available_note`: Shown when the salon has no active services —
  "Add services to the catalog first before assigning them to staff." With a
  "Go to Catalog" link. In this state the services section is non-interactive.

**Working Hours section**

- `hours_section_header`: "Working hours".
- `hours_instruction_text`: "Set working hours for each day within the salon's
  operating hours." (Reference: salon operating hours displayed as read-only
  context below the header: "Salon hours: {day_summary}".)
- `salon_hours_context_text`: Small caption showing the salon's operating hours
  per day. Read-only. Helps Ramesh recall the salon boundary when setting staff
  hours. Example: "Salon: Mon–Sat 9 AM – 7 PM, Sun Closed."
- `staff_day_row` (one per day, Monday through Sunday):
  - `day_label`: "Monday" etc.
  - `working_toggle`: Switch — "Working". When OFF: day is a day off for this
    staff member; time pickers are disabled.
  - `start_time_picker`: Time picker. Label context: "Start". Disabled when
    `working_toggle` is OFF or when the salon is closed that day (if the salon
    is closed on Sunday, this row's `working_toggle` is permanently OFF and
    grayed with the note "Salon closed").
  - `separator_text`: "to".
  - `end_time_picker`: Time picker. Label context: "End".
  - `salon_closed_note` (inline, if salon is closed that day): "Salon closed"
    in grey text. `working_toggle` is hidden (redundant); row is non-interactive.
- `save_button`: "Save staff member" / "Save changes" — primary CTA,
  full-width, 52pt. At bottom of screen.

### Interactions

- Fill `staff_name_field`, check services, set hours → `save_button` enabled
  when name is non-empty. Services and hours are not strictly required to save
  (partner may add incrementally — they might add the name, then add services
  later). However, if `working_toggle` is ON for a day, times must be set.
- Tap `service_checkbox` → toggle service assignment for that staff member.
- Toggle `working_toggle` ON for a day → `start_time_picker` and
  `end_time_picker` become active.
- Toggle `working_toggle` OFF → time pickers clear and disable.
- Tap `save_button` → validate, then:
  - Create: POST /staff with name, `qualified_service_ids`, `working_hours`.
  - Edit: PATCH /staff/{id} with changed fields.
  On success → return to StaffList.

### Validation (FR-P-STAFF-04, FR-P-STAFF-05)

Run on save.

- `staff_name_field`: Required. Min 1 char (trimmed). Max 100 chars.
  Error: "Name is required."
- Per working day (for each day where `working_toggle` is ON):
  - Both `start_time_picker` and `end_time_picker` must be set.
    Error: "Set start and end times for {day_name}."
  - `end_time_picker` must be after `start_time_picker`.
    Error: "End time must be after start time for {day_name}."
  - `start_time_picker` must be ≥ salon's `operating_hours[day].open`.
    Error: "Start time for {day_name} is before the salon opens
    ({salon_open_time})."
  - `end_time_picker` must be ≤ salon's `operating_hours[day].close`.
    Error: "End time for {day_name} is after the salon closes
    ({salon_close_time})."
  (FR-P-STAFF-05: "Staff working hours must fall within the salon's configured
  operating hours".)
- Show all validation errors simultaneously (same rationale as partner-profile.md).
- Scroll to first error after failed save attempt.

### Error / Edge States

- **Salon operating hours not yet configured (all days closed):**
  `salon_hours_context_text` shows "Operating hours not yet set." All
  `staff_day_row` `working_toggle` switches are disabled. Inline note:
  "Set salon operating hours in Profile before configuring staff schedules."
  With a "Go to Profile" link. `save_button` still works for name and services
  (the partner can save the staff member's name without setting hours yet).
- **Service catalog is empty:** `service_checkbox_list` shows empty-catalog note
  (see above). Staff can be saved with no services initially.
- **Network failure on save:** "Couldn't save. Check your connection."
- **Concurrent modification (staff member's schedule changed by another session):**
  Edge case; treat same as profile concurrent edit (see partner-profile.md).
- **Staff member has upcoming bookings and is being edited:** If the Architect
  implements staff assignment to bookings (PRD Section 10 open question), editing
  a staff member's hours that affect upcoming bookings may be significant. Until
  that question is resolved, the form shows no booking-conflict warning. If the
  Architect resolves that bookings are staff-assigned, a booking-conflict warning
  should be added here (post-resolution UX update required).

### Privacy / Accessibility

- Staff working hours are internal data. They are not displayed to customers.
- `staff_name_field` semantic label: "Staff member name, required."
- `service_checkbox_list` container: "Select services this staff member can
  perform."
- Each `service_checkbox` semantic: "{service_name}, {checked or unchecked}."
- `staff_day_row` semantic (per day): "{day_name}. {Working toggle: Working or
  Day off}. Start time {value or not set}. End time {value or not set}."
- `salon_closed_note` announces: "{day_name}: salon is closed, not selectable."
- All time pickers use the system `showTimePicker` dialog (platform accessible).
- All toggles and checkboxes have ≥ 44pt hit area including label.

---

## Sheet: RemoveStaffConfirmation

**Entry point:** `remove_button` on a StaffList card.

### Components

- `sheet_title`: "Remove {staff_name}?".
- `warning_text`: "{staff_name} will be removed from your team. Existing bookings
  assigned to them will not be affected." (FR-P-STAFF-03.)
- `remove_button`: "Remove staff member" — destructive primary (red), full-width.
- `keep_button`: "Keep {staff_name}" — secondary outlined, full-width.

### Interactions

- Tap `remove_button` → PATCH /staff/{id} setting `active = false`. On success:
  staff member disappears from StaffList. Toast: "{staff_name} removed."
- Tap `keep_button` or swipe down → dismiss without action.

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Single scrollable form for name + services + hours | StaffForm has three logical sections. On mobile, separate tabs or screens for each section would require more navigation and context-switching. Ramesh's workflow is "add person, check what they do, set their hours" in one session. A single scroll keeps this workflow linear. | Tabbed form (Info / Services / Schedule) — adds navigation complexity; rejected for single-staff-at-a-time workflow. |
| Salon operating hours shown as read-only context in StaffForm | FR-P-STAFF-05 requires validation against salon hours. Showing the salon hours inline helps the partner set valid staff hours without needing to navigate away to check Profile. | Partner navigates to Profile to check hours — creates friction and context loss. |
| Save allowed without services and without complete hours | Partners manage staff incrementally. Forcing complete setup in one session is friction. The cost of partial data is that the staff member can't be assigned to bookings yet — acceptable because incomplete staff records affect scheduling capability, not data integrity. | Require complete form before save — high friction for Ramesh who may be onboarding in bursts. |
| Staff working hours validation is client-side + server-side | Client-side validation gives immediate feedback. Server-side validation (FR-P-STAFF-05) ensures integrity even if the client is bypassed. Both are required. | Client-side only — not secure. Server-side only — poor UX (round-trip for each error). |
| Booking conflict warning deferred until Architect resolves staff assignment | PRD Section 10 explicitly leaves staff-to-booking assignment open. Designing a conflict warning before that decision is made risks designing the wrong interaction. This is flagged as a post-resolution UX update. | Design warning now based on an assumed resolution — risks having to undo the design if the Architect resolves differently. |
