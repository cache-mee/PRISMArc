---
title: "UX Spec — Customer Discovery"
surface: "Customer Mobile App (iOS + Android)"
flow: "Location Selection + Salon Discovery List + Filters"
prd-refs: "FR-C-LOC-01, FR-C-LOC-02, FR-C-LOC-03, FR-C-DISC-01 through FR-C-DISC-06, NFR-PRIV-01, NFR-PRIV-02, NFR-PERF-01"
created: 2026-09-05
---

# Customer Discovery Flow

## Overview

Discovery is the top of the customer funnel. It is fully unauthenticated (FR-C-AUTH-01).
The flow starts with location resolution, shows a filterable salon list, and each
card navigates to the Salon Detail view. Load indicators on each card are anonymized
aggregate values only (NFR-PRIV-01, NFR-PRIV-02).

---

## Screen: LocationResolution (Splash/Entry)

**Entry point:** App cold start, or when returning to discovery from any deeper
screen via bottom navigation tab "Discover".

### Components

- `location_prompt_card`: Appears on first launch (or after permission denial)
  asking for device location. Full-width card at top of screen.
  - `location_icon`: 24pt location pin icon.
  - `prompt_text`: "Allow location access to find salons near you."
  - `allow_button`: "Use my location" — primary outlined button. 44pt height.
  - `manual_entry_link`: "Enter a location instead" — text button below.
- `search_bar`: Always visible below `location_prompt_card` (or alone after
  permission is granted). Tap to open LocationSearch overlay. Displays:
  - Left: location pin icon (20pt).
  - Center: current search location text (address or "Current location").
  - Right: "Change" text label (44pt tap target).
- `salon_list`: Scrollable vertical list of `salon_card` items. Begins loading
  immediately when a search location is set.
- `filter_button`: Top-right of screen, above `salon_list`. Label: "Filter"
  with funnel icon. Badge count shows number of active filters (hidden when 0).
- `sort_control`: Segmented control or dropdown immediately above `salon_list`.
  Options: "Nearest" (default) | "Fastest" | "Lowest price". Maps to:
  "Nearest" = distance ascending; "Fastest" = average service duration ascending;
  "Lowest price" = starting price ascending (FR-C-DISC-02).

### Interactions

- App launch, no prior location stored:
  → Show `location_prompt_card` above an empty `salon_list`.
- Tap `allow_button` → trigger OS location permission dialog. If granted → resolve
  device coordinates, reverse-geocode to a readable address, set as search
  location, hide `location_prompt_card`, load salon list (FR-C-LOC-01).
- Tap `manual_entry_link` → open LocationSearch overlay (see below).
- Tap `search_bar` ("Change") → open LocationSearch overlay.
- App launch, prior location stored (FR-C-LOC-03) → skip `location_prompt_card`,
  pre-populate `search_bar` with stored location, load salon list.
- Tap sort option → reload `salon_list` with new sort order (no server round-trip
  if results are cached; re-sort locally from cached result set). Active sort option
  visually highlighted.
- Tap `filter_button` → open FilterSheet (see below).

### Error / Edge States

- Location permission denied by OS: `location_prompt_card` shows "Location access
  denied. Enter a location to find nearby salons." `allow_button` replaced by
  "Open Settings" (opens OS app settings). `manual_entry_link` remains.
- Location permission denied permanently (iOS "Don't Allow"): same as above.
  "Open Settings" deep-links to the app's permission settings page.
- Location resolved but no salons within radius: show empty state (see
  DiscoveryList Empty State below).
- Network error loading list: show `retry_card` in place of list — "Couldn't load
  salons. Check your connection." with "Try again" button (FR-C-DISC-01 requires
  a list; failure must surface a recovery path).
- Loading in progress: show 3 placeholder skeleton cards (shimmer animation) while
  awaiting API response. Must show initial results within 3 seconds (NFR-PERF-01).

### Privacy / Accessibility

- Device coordinates are used only for salon discovery; they are not stored
  permanently on the server beyond the API request.
- `search_bar` semantic label: "Current search location. Tap to change."
- `allow_button` semantic label: "Allow location access to find salons near you."
- Sort control options read their full labels to screen readers
  ("Sort by: Nearest, selected" etc.).

---

## Screen: LocationSearch (Overlay)

**Entry point:** Tapping `search_bar` or `manual_entry_link` on LocationResolution.

### Components

- `overlay_header`: Back button (chevron left, 44pt) + "Search location" title.
- `text_search_field`: Auto-focused text input, placeholder "Search area, street
  or landmark". Character limit: 200. Keyboard type: default.
- `current_location_row`: List row at top of results, icon + "Use my current
  location". Always shown if device location is available or permission not yet
  determined. Hidden if permission permanently denied and OS settings not opened.
- `results_list`: Scrollable list of address suggestion rows. Each row:
  - `address_primary`: Bold, main address or place name.
  - `address_secondary`: Lighter text, city/district qualifier.
- `clear_button`: X icon inside `text_search_field`, visible when field is
  non-empty. Clears field and restores previous suggestions.

### Interactions

- Type into `text_search_field` → debounce 300ms → call location search API
  (maps/geocoding). Show results in `results_list`. Minimum 3 characters before
  API call is triggered; below 3 characters, show "Use my current location" row
  only.
- Tap `current_location_row` → request/use device location (same flow as
  `allow_button` on LocationResolution). Dismiss overlay. Store location (FR-C-LOC-01).
- Tap any result row → set as search location, dismiss overlay, store location
  (FR-C-LOC-03), load salon list with new coordinates.
- Tap back button → dismiss overlay without changing current location.

### Error / Edge States

- No results for search query: show "No locations found for '{query}'." Row with
  suggestion to try a different term.
- Network failure during search: show "Couldn't search locations. Check your
  connection." Results list shows last valid results (or empty if first search).
- Empty field (field cleared): show only `current_location_row`.

### Privacy / Accessibility

- Search queries are not stored locally beyond the session.
- Most-recently-selected location is stored for pre-population (FR-C-LOC-03) —
  this is a single value, not a history list; no history browsing UI is needed.
- `text_search_field` auto-focuses on overlay open (keyboard appears immediately).
- Each result row minimum 44pt height.

---

## Screen: DiscoveryList

**Entry point:** Location set (device or manual). Reached from LocationResolution
once `salon_list` loads.

Note: DiscoveryList is the same screen as LocationResolution — the `salon_list`
region is the primary content. This screen descriptor covers the loaded state.

### Components — Salon Card (`salon_card`)

Each card in the `salon_list`. Tappable as a whole unit (entire card is a single
tap target).

- `salon_name`: Bold, primary text. Single line, truncated with ellipsis if longer
  than card width.
- `distance_chip`: "0.8 km" — small chip, left-aligned below name. Computed
  from search location to salon coordinates.
- `load_indicator_chip`: Anonymized aggregate load label. Values: "Quiet" |
  "Moderate" | "Busy". Color-coded: green / amber / red. Derived from count of
  active bookings relative to available capacity (FR-C-DISC-04). **No individual
  booking data is exposed** (NFR-PRIV-02). Right-aligned on same row as
  `distance_chip`.
- `price_range_text`: "From ₹{min_price_inr}" — starting price, lowest service
  in catalog (FR-C-DISC-03). Displayed as integer if value has no paise, or with
  2 decimal places if non-zero paise. All values in INR.
- `avg_duration_text`: "Avg {N} min" — average service duration across catalog
  (FR-C-DISC-03).
- `rating_row`: Star icon + "{average_rating}" (1 decimal place, e.g., "4.3") +
  "({review_count} reviews)". Hidden if no reviews yet (shows nothing — not
  "0 reviews", which implies the salon is unrated; prefer omission to avoid
  misleading new salons).
- `card_divider`: 1pt separator between cards.

### Interactions

- Tap anywhere on `salon_card` → navigate to SalonDetail for that salon
  (FR-C-DET-01).
- Swipe list vertically → standard scroll.
- Pull-to-refresh gesture on `salon_list` → re-fetch list with current location
  and active filters/sort. Show inline refresh indicator.
- Tap `sort_control` option → re-sort results (FR-C-DISC-02).
- Tap `filter_button` → open FilterSheet.

### Error / Edge States

- Empty state (no salons match location + filters): Show centered illustration,
  headline "No salons found nearby", body "Try a different location or adjust
  your filters." (FR-C-DISC-06). If filters are active, show secondary CTA
  "Clear filters" to reset to default. If no filters active, show only location
  change prompt.
- Salon has no reviews: omit `rating_row` from that card.
- Salon name truncated: full name accessible via navigation to SalonDetail.
- Load indicator data unavailable (API partial failure): omit `load_indicator_chip`
  from that card. Do not show a placeholder or "unknown" label.

### Privacy / Accessibility

- `load_indicator_chip` information boundary: the chip shows only a categorical
  label ("Quiet / Moderate / Busy"). The underlying count of bookings is computed
  server-side and the category label alone is returned. No per-customer booking
  information is present in the API response for this surface.
- `salon_card` semantic label (screen reader): "{salon_name}. {distance_chip}.
  {load_indicator_chip}. From ₹{price}. Average {duration} minutes.
  {rating_row if present}. Double-tap to view salon."
- `filter_button` announces badge count: "Filter, {N} filters active" or
  "Filter, no filters active".
- List items are `ListTile` or equivalent with `onTap` — entire card is one
  focus element for screen reader, not each sub-element.

---

## Screen: FilterSheet

**Entry point:** Tapping `filter_button` on DiscoveryList.

### Components

- `sheet_handle`: Drag indicator at top of bottom sheet.
- `sheet_title`: "Filter salons".
- `close_button`: X icon, top-right (44pt). Dismisses without applying changes.
- `max_distance_section`:
  - `section_label`: "Maximum distance".
  - `distance_slider`: Slider, range 0.5 km – 20 km, step 0.5 km.
  - `distance_value_label`: "{N} km" adjacent to slider, updates live.
- `max_price_section`:
  - `section_label`: "Maximum price".
  - `price_slider`: Slider, range ₹50 – ₹5000, step ₹50.
    (Range bounds are configurable by backend; these are design defaults.)
  - `price_value_label`: "Up to ₹{N}" adjacent to slider, updates live.
- `min_rating_section`:
  - `section_label`: "Minimum rating".
  - `rating_selector`: Row of 5 star icons, tappable. Selecting N stars means
    "show only salons with average rating ≥ N". Selected state: filled stars up
    to N, outline stars beyond N. Label beside stars: "{N}+ stars" or "Any" when
    no rating filter set.
- `apply_button`: "Apply filters" — primary CTA, full-width, 52pt. Applies
  filters and dismisses sheet. Badge count on `filter_button` updates.
- `reset_link`: "Reset filters" — text button, centered, above `apply_button`.
  Resets all three controls to their defaults (max distance = system default,
  price and rating unconstrained). Does not auto-close sheet.

### Interactions

- Adjust slider or star selector → values update live in labels. No API call
  until "Apply" is tapped.
- Tap `apply_button` → dismiss sheet, reload `salon_list` with new filters.
- Tap `reset_link` → reset all controls to default, remain on sheet.
- Tap `close_button` or swipe down → dismiss without applying changes (restore
  previously applied filter values in controls, not the just-adjusted values).
- Re-open FilterSheet with active filters → controls pre-populated with the
  currently applied values.

### Error / Edge States

- No salons match applied filters: FilterSheet closes, DiscoveryList shows empty
  state (FR-C-DISC-06). Customer can tap "Clear filters" from the empty state.
- Slider at minimum (all salons included): equivalent to no filter on that
  dimension — same as unconstrained.

### Privacy / Accessibility

- FilterSheet does not display any salon booking or queue data.
- Sliders have semantic labels: "Maximum distance, {N} kilometres" etc.
- Star selector announces: "Minimum rating filter: {N} stars selected" or
  "Minimum rating filter: no minimum set."
- `reset_link` semantic label: "Reset all filters to defaults."
- `apply_button` semantic label: "Apply filters and show results."

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Discovery is fully unauthenticated | PRD FR-C-AUTH-01 explicit. Priya needs to evaluate options before committing to an account. | Gated on auth — rejected: directly contradicts FR-C-AUTH-01. |
| Load indicator uses 3 categorical labels, not a number | NFR-PRIV-02 requires anonymized aggregate only. A categorical label ("Busy") is less precise than a count, which is an additional privacy margin. However, FR-C-DISC-04 permits counts on the list ("3 people ahead" is cited in FR-C-DET-03 for the detail view, not the list). List uses category; detail view exposes the count. Decision: list uses lower-precision label to avoid confusing customers about what "3" means without salon-capacity context. | Raw count on list card — acceptable per PRD but deferred to detail view where context exists. |
| Rating row hidden when zero reviews | "0 reviews" label signals that a salon is new and unreviewed, which could disadvantage legitimate new salons. Omitting the row is neutral. | "0 reviews" label — rejected: penalizes newly onboarded salons during cold-start period. |
| Sort is client-side after initial fetch | For a bounded result set (one city, one radius), sorting the cached list avoids extra round-trips and feels instantaneous. If the result set grows beyond what is cacheable, server-side sort must be added. | Server-side sort on every sort change — adds latency; unnecessary for MVP single-city scope. |
| Stored location is a single value, not a history | PRD FR-C-LOC-03 says "most recently used" — singular. Building a history list is post-MVP scope. | History list — recorded as post-MVP note. |
