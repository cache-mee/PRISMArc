---
title: "UX Spec — Partner Schedule Configuration"
surface: "Salon Partner Mobile App (iOS + Android)"
flow: "Slot Duration Configuration, Operating Hours Override"
prd-refs: "FR-P-SCHED-01, FR-P-SCHED-02, FR-P-SCHED-03"
created: 2026-09-05
---

# Partner Schedule Configuration Flow

## Overview

Schedule configuration covers two related but distinct concepts:

1. **Slot duration per service** (FR-P-SCHED-01): How long a slot is blocked
   in the calendar for each service, including any buffer time. This is
   `Service.slot_duration_minutes` — already configurable in ServiceForm
   (partner-catalog.md). This screen provides a consolidated overview and
   quick-edit surface for slot durations across all services, to support a
   scheduling-focused mental model.

2. **Operating hours override** (FR-P-SCHED-03): The partner can view the
   current day's schedule as a timeline from the booking dashboard. Operating
   hours themselves are set in Salon Profile (partner-profile.md). This screen
   does not duplicate the profile's hours editor.

Decision note: FR-P-SCHED-01 requires `slot_duration_minutes` to be configurable
"per service, separate from the service's listed duration." This field exists in
ServiceForm. The Schedule screen provides a dedicated view for slot-duration
management specifically, because Ramesh's scheduling mental model may think about
"how long do I block for each service" as a scheduling question, not a catalog
question. Both routes reach the same data.

The "Schedule" tab in the partner app therefore contains:
- A slot duration summary (per service, with inline editing).
- An operating hours summary (read-only link to Profile for editing).

The day's schedule timeline is in the Dashboard (partner-dashboard.md, FR-P-SCHED-03).

---

## Screen: ScheduleConfig

**Entry point:** "Schedule" tab in partner bottom navigation.

### Components

**Slot Durations section**

- `section_header`: "Slot Durations".
- `section_description`: "These control how long each appointment blocks your
  calendar. Add buffer time for prep or cleanup."
- `slot_duration_list`: Vertical list of `slot_duration_row` items (one per
  active service).
  - `service_name_text`: Bold.
  - `service_duration_chip`: Small chip — "{duration_minutes} min" (the
    customer-facing duration).
  - `slot_duration_field`: Inline editable numeric field — "{slot_duration_minutes}
    min". Tapping this field makes it editable in-place. The field accepts only
    positive integers. A checkmark (save) icon appears adjacent when the value
    is changed. Cancel (X) icon also appears to revert without saving.
    Field shows the current `Service.slot_duration_minutes` value.
  - `slot_duration_label`: "Slot" in small text beside `slot_duration_field`.
  - `buffer_note`: Shown below the row when `slot_duration_minutes` >
    `duration_minutes`: "+{buffer} min buffer" in muted text. This provides
    instant feedback about how much buffer is configured.
  - `buffer_warning`: Shown when `slot_duration_minutes` < `duration_minutes`:
    "Slot is shorter than service duration" in amber. This is the same validation
    as in ServiceForm.
- `empty_state`: "No services in your catalog. Add services to configure slot
  durations." with a "Go to Catalog" link.

**Operating Hours summary section**

- `section_header`: "Operating Hours".
- `hours_summary_list`: Read-only list of each day of the week with open/close
  times or "Closed". Same content as the expanded `operating_hours_expanded` in
  SalonDetail.
- `edit_hours_link`: "Edit in Salon Profile" — text link. Navigates to the
  SalonProfile screen (profile tab). Reinforces that operating hours are edited
  in Profile, not here.

### Interactions

- Tap `slot_duration_field` for a service → field becomes editable (numeric
  keyboard). Save (checkmark) and cancel (X) icons appear.
- Edit slot duration value → buffer note updates live.
- Tap save icon (checkmark) → validate and PATCH /services/{id} with new
  `slot_duration_minutes`. On success: field reverts to display mode, value
  updated. Brief success indicator (checkmark animation or green flash).
  On error: inline error (see below), field remains editable.
- Tap cancel (X) → revert to original value, field reverts to display mode.
- Tap `edit_hours_link` → navigate to SalonProfile screen (profile tab).
  Back button on Profile returns here.

### Validation (for inline slot duration edit)

- Must be a positive integer (≥ 1). If not: "Enter a whole number greater than 0."
  Inline error below the field.
- Must be ≥ `Service.duration_minutes`. If not: "Slot must be at least
  {duration_minutes} min (service duration)." Inline error below the field.
  Save icon disabled until the value is valid.
- Validation runs immediately on field change (not deferred to save, since the
  save action is per-row and immediate).

### Error / Edge States

- **Load failure:** "Couldn't load schedule config. Check your connection." Retry.
- **Save failure (PATCH error):** Inline error below the `slot_duration_field`:
  "Couldn't save. Try again." X icon reverts the change. The field remains
  editable.
- **Service catalog empty:** Show empty state (see above).
- **Operating hours not yet configured:** `hours_summary_list` shows "Not
  configured — set hours in Salon Profile." `edit_hours_link` still active.
- **All services have slot durations equal to their service durations (no buffer):**
  This is the default state and is valid. No warning shown.

### Privacy / Accessibility

- Schedule configuration data is internal to the partner. No customer data is
  displayed here.
- `slot_duration_field` semantic label (display mode): "Slot duration for
  {service_name}: {value} minutes. Double-tap to edit."
- `slot_duration_field` semantic label (edit mode): "Editing slot duration for
  {service_name}. Current value: {value} minutes. Enter a whole number."
- Save icon semantic label: "Save slot duration for {service_name}."
- Cancel icon semantic label: "Cancel edit for {service_name}."
- `buffer_note` announced via `LiveRegion` when value changes: "+{N} min buffer."
- `buffer_warning` announced via `LiveRegion`: "Warning: slot is shorter than
  service duration."
- All interactive elements ≥ 44pt.

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Slot duration is also editable in ServiceForm (partner-catalog.md) | Two entry points to the same data field exist by design. `slot_duration_minutes` is both a service attribute (belongs in ServiceForm) and a scheduling configuration (belongs in ScheduleConfig). Keeping both in sync is straightforward since they write to the same field. | Single entry point in ServiceForm only — less discoverable for scheduling-focused partners. Single entry point in ScheduleConfig only — less discoverable for catalog-focused partners. |
| Inline edit per row (not a form) | Changing a slot duration is a small, targeted action. Opening a full form screen to change one number is disproportionate. Inline editing provides immediate feedback and saves a navigation round-trip. | Full form screen per service — unnecessary navigation for a single field change. |
| Operating hours shown read-only with a link to Profile | Displaying operating hours in the Schedule tab alongside slot durations gives the partner the context they need to understand their scheduling setup holistically. Making hours editable here too would create two screens that can edit the same data — risking confusion about where the canonical edit lives. | Make hours editable here too — duplicates the edit surface; rejected. |
| Slot duration list shows the service's `duration_minutes` as a reference chip | Ramesh needs to know the service duration in order to set a meaningful slot duration. Without the reference, the partner cannot tell whether a configured slot duration is a buffer or matches the service itself. | Service duration not shown — removes essential context. |
| Timeline of today's bookings belongs in Dashboard, not Schedule | FR-P-SCHED-03 says the partner "can view the current day's schedule as a timeline of confirmed bookings across all staff, displayed in the mobile app's booking dashboard." The PRD locates this explicitly in the dashboard. This spec follows that assignment. | Timeline in Schedule tab — contradicts PRD assignment to dashboard. |
