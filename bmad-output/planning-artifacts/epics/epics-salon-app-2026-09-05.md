# Epics & Stories — salon-app
Generated: 2026-09-05
Source PRD: bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-05/prd.md
Source UX: bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-05/

---

## Sizing reference

| Size | Meaning | Approximate effort |
|---|---|---|
| S | Straightforward, single-layer change | ~1 day |
| M | Spans 2–3 layers or has moderate logic | ~2–3 days |
| L | Complex logic, multiple components, or external integration | ~4–5 days |

---

## Dependency notation

`>` means "depends on". Stories marked with the same epic number share the epic's
foundational setup implicitly. Cross-epic dependencies are stated explicitly.

---

## Epic 1: Infrastructure & CI Setup

This epic delivers the project scaffold — repositories, CI pipelines, shared
tooling, environment configuration, and the empty-but-building app shells —
so that all subsequent epics have a working foundation to build on. It produces
no user-visible features; it produces a system that compiles, lints, and passes
an empty test suite on every pull request.

### Story 1.1: Backend project scaffold

**As a** developer, **I want** a Node.js/TypeScript backend project initialised
with the approved folder structure, tooling, and CI checks, **so that** all
backend stories have a consistent, lint-clean starting point.

**Acceptance criteria:**
- [ ] Repository contains `src/` with sub-folders `routes/`, `controllers/`,
  `services/`, `repositories/`, `middleware/`, `lib/`, `types/` as specified in
  base-rules.md §3.9.
- [ ] `tsconfig.json` has `"strict": true`; `tsc --noEmit` passes with zero errors.
- [ ] ESLint is configured with `@typescript-eslint/no-explicit-any: error`; `eslint src/ --max-warnings 0` passes.
- [ ] `vitest` is installed; `npm test` runs and exits 0 (no tests yet, but the runner executes).
- [ ] A `src/lib/logger.ts` module exists; no `console.log` calls are present anywhere in `src/`.
- [ ] A `src/middleware/errorHandler.ts` exists with a stub that maps `AppError` subclasses to HTTP status codes.
- [ ] `Dockerfile` builds successfully (`docker build .` exits 0).
- [ ] CI pipeline runs `tsc --noEmit`, `eslint`, `npm test`, and `docker build` on every pull request to main.

**Dependencies:** none
**Complexity:** M

---

### Story 1.2: Database and Redis infrastructure setup

**As a** developer, **I want** PostgreSQL and Redis provisioned with migration
tooling and connection pooling configured, **so that** backend services can
interact with durable storage and the cache layer from the first feature story.

**Acceptance criteria:**
- [ ] A migration runner is configured (e.g., `node-pg-migrate` or Kysely migrations);
  `npm run migrate` applies pending migrations and exits 0.
- [ ] `src/lib/db.ts` exposes a `pg` connection pool; no route, controller, or
  service imports `pg` directly.
- [ ] `src/lib/redis.ts` exposes a Redis client; the client is a singleton.
- [ ] A seed script creates a minimal test database schema and exits 0 in the CI environment.
- [ ] Environment variables `DATABASE_URL` and `REDIS_URL` are the sole connection
  configuration; no hard-coded connection strings exist in source.
- [ ] CI pipeline can run `npm run migrate` and `npm test` against a test database
  (Docker Compose or equivalent) without manual setup.

**Dependencies:** 1.1
**Complexity:** M

---

### Story 1.3: Flutter customer app project scaffold

**As a** developer, **I want** a Flutter project for the customer app initialised
with the approved architecture, packages, and CI checks, **so that** all customer
app stories have a consistent starting point.

**Acceptance criteria:**
- [ ] Flutter project created with `go_router` for navigation and a single `AppRouter`
  class; no `Navigator.push` with anonymous routes exists.
- [ ] `get_it` is configured; `injection_container.dart` (or equivalent) exists
  and registers singletons.
- [ ] `flutter_secure_storage` is installed and used in a stub `AuthRepository`.
- [ ] `freezed` and `json_serializable` are installed; build runner generates code
  without errors.
- [ ] `flutter analyze` exits with zero errors and zero warnings.
- [ ] `flutter test` exits 0 (empty test suite is acceptable at scaffold stage).
- [ ] `dart format --output=none --set-exit-if-changed .` passes.
- [ ] CI pipeline runs `flutter analyze`, `flutter test`, and `dart format` on
  every pull request.

**Dependencies:** none
**Complexity:** M

---

### Story 1.4: Flutter partner app project scaffold

**As a** developer, **I want** a Flutter project for the salon partner app
initialised with the same architecture and CI checks as the customer app, **so
that** all partner app stories have a consistent starting point.

**Acceptance criteria:**
- [ ] Same structural checks as Story 1.3 apply to the partner app project.
- [ ] Partner app has its own `go_router` `AppRouter`, `injection_container.dart`,
  and stub `PartnerAuthRepository`.
- [ ] `flutter analyze`, `flutter test`, and `dart format` all pass in CI.
- [ ] The partner app and customer app are separate Flutter projects (or separate
  flavours in a monorepo); they do not share a single `main.dart` entry point.

**Dependencies:** none
**Complexity:** M

---

## Epic 2: Customer Authentication

This epic delivers the full customer authentication flow: phone-OTP registration
and login (primary), email/password registration and login (secondary, if the
Architect enables it), account creation, and JWT session management. Discovery
and browsing remain unauthenticated per PRD FR-C-AUTH-01.

### Story 2.1: Auth API — OTP send and verify endpoints

**As a** customer, **I want** to receive an SMS one-time code and verify it,
**so that** I can prove ownership of my phone number and gain access to booking features.

**Acceptance criteria:**
- [ ] `POST /api/v1/auth/otp/send` accepts `{ phone: string }` (10-digit Indian
  mobile, `+91` prefix normalised server-side). Returns `200` on success; returns
  `400` for invalid format; returns `429` when rate-limited (configurable limit,
  minimum: block after 5 requests within 60 seconds from the same phone).
- [ ] OTP is a 6-digit numeric code stored as a bcrypt hash in the database with
  a 10-minute expiry timestamp (NFR-SEC-03, base-rules.md §3.7).
- [ ] `POST /api/v1/auth/otp/verify` accepts `{ phone, otp }`. Returns `200` with
  a JWT (RS256) on first correct submission. Returns `401` for wrong OTP. Returns
  `410` for expired OTP. OTP is invalidated after first successful use
  (NFR-SEC-03).
- [ ] Incorrect OTP submissions do not consume the OTP; only a correct submission
  or expiry invalidates it.
- [ ] The response body on successful verify indicates whether the phone is a new
  user (`{ isNewUser: true }`) or returning user (`{ isNewUser: false }`), so
  the Flutter client knows whether to route to registration or dashboard.
- [ ] No OTP value is logged at any log level in production (base-rules.md §1 Logging).
- [ ] Unit tests cover: OTP generated and hashed, correct OTP verifies and issues
  JWT, incorrect OTP returns 401 without consuming, expired OTP returns 410.

**Dependencies:** 1.1, 1.2
**Complexity:** M

---

### Story 2.2: Auth API — customer registration and email/password endpoints

**As a** new customer, **I want** to create an account with my name after OTP
verification, **so that** my bookings are associated with a persistent account.

**Acceptance criteria:**
- [ ] `POST /api/v1/auth/register` accepts `{ phone, name }` with a valid OTP
  session token. Creates a `Customer` record. Returns `201` with a JWT. Returns
  `409` if the phone is already registered.
- [ ] Customer `name` is stored as UTF-8, max 100 characters; leading/trailing
  whitespace is trimmed before storage.
- [ ] Customer `phone` is stored normalised (digits only, no spaces or formatting).
- [ ] `POST /api/v1/auth/email/register` accepts `{ name, email, phone, password }`.
  Password is hashed with bcrypt (min cost factor 12) before storage
  (NFR-SEC-02). Plaintext password is never stored or logged. Returns `201` on
  success, `409` if email already exists.
- [ ] `POST /api/v1/auth/email/login` accepts `{ email, password }`. Returns `200`
  with JWT on correct credentials. Returns `401` for wrong email or password
  (single undifferentiated message — do not reveal whether the account exists).
- [ ] Passwords are never logged at any level (base-rules.md §1 Logging).
- [ ] Unit tests cover: successful registration, duplicate phone/email returns 409,
  password hashing verified (stored value differs from input), login with wrong
  password returns 401.

**Dependencies:** 2.1
**Complexity:** M

---

### Story 2.3: Customer app — auth gate and OTP flow (Flutter)

**As a** customer, **I want** an authentication prompt to appear only when I
attempt to book or manage bookings, **so that** I can browse salons freely
without being forced to log in first.

**Acceptance criteria:**
- [ ] Tapping "Book" on a service row when unauthenticated shows the `AuthGate`
  bottom-sheet modal; no auth prompt appears on app launch or during discovery
  browsing (FR-C-AUTH-01).
- [ ] `AuthGate` presents "Continue with phone number" (primary) and optionally
  "Continue with email" (secondary, shown only if the Architect has enabled email
  auth). "Maybe later" dismisses the sheet and returns to the originating screen
  without queuing the booking action.
- [ ] `PhoneEntry` screen: 10-digit numeric field with `+91` prefix; "Send code"
  button is disabled until exactly 10 digits are entered; tapping "Send code"
  calls `POST /api/v1/auth/otp/send` and navigates to `OTPVerification` on success.
- [ ] Rate-limit response (429) shows the error message "Too many attempts. Please
  wait 60 seconds before trying again." with a visible 60-second countdown.
- [ ] `OTPVerification` screen: 6-cell OTP input auto-advances on digit entry and
  auto-submits on the 6th digit. `autofillHints: [AutofillHints.oneTimeCode]`
  is set. Resend link is disabled for 30 seconds after OTP dispatch.
- [ ] Expired OTP (410) shows "This code has expired. Request a new one." and
  enables the resend link immediately.
- [ ] Maximum 5 incorrect attempts locks the OTP field and enables resend.
- [ ] On successful verify for a new user, app navigates to `RegistrationName`.
  On successful verify for a returning user, `AuthGate` is dismissed and the
  booking action resumes automatically with the service selection context preserved
  in BLoC state.
- [ ] `RegistrationName` screen: name field required, max 100 chars;
  `continue_button` disabled until trimmed value is non-empty; tapping calls
  `POST /api/v1/auth/register` and dismisses `AuthGate` on success.
- [ ] JWT is stored in `flutter_secure_storage` (base-rules.md §2.6). On next app
  cold-start with a valid JWT, `AuthGate` is never shown for the booking action.
- [ ] Phone number is displayed in masked form on `OTPVerification` (first 6
  digits replaced with X, last 4 visible).
- [ ] All interactive elements meet 44pt minimum tap target.
- [ ] Widget tests cover: AuthGate shown when unauthenticated, hidden when
  authenticated; OTP 6th digit auto-submits; expired OTP shows correct error state.

**Dependencies:** 2.1, 2.2, 1.3
**Complexity:** L

---

### Story 2.4: Customer app — email/password auth flow (Flutter)

**As a** customer who prefers email, **I want** to register and log in with my
email and password, **so that** I have an alternative to phone OTP if the Architect
enables it.

**Acceptance criteria:**
- [ ] `EmailLogin` screen: email field + password field with visibility toggle;
  "Sign in" button disabled until both fields are non-empty; calls
  `POST /api/v1/auth/email/login`; on success, stores JWT and dismisses `AuthGate`.
- [ ] Invalid credentials show "Incorrect email or password." (single message,
  does not distinguish email from password).
- [ ] "Don't have an account? Create one" navigates to `EmailRegistration`.
- [ ] `EmailRegistration` screen: name, email, phone (10 digits, required for
  booking notifications per FR-C-BOOK-05), password (min 8 chars), confirm password.
  Calls `POST /api/v1/auth/email/register` on submit.
- [ ] Password too short (< 8 chars): inline error "Password must be at least 8 characters."
- [ ] Passwords not matching: inline error on confirm field "Passwords don't match."
- [ ] Duplicate email: "An account with this email already exists. Sign in instead?"
  with link to `EmailLogin`.
- [ ] Password field uses `obscureText: true` with a visibility toggle (44pt); password
  is never logged or stored in BLoC state after the API call completes.
- [ ] Widget tests cover: submit disabled until all fields valid, password mismatch
  shows error, duplicate email shows 409 error message.

**Dependencies:** 2.2, 1.3
**Complexity:** M

---

## Epic 3: Salon Discovery & Detail (Customer)

This epic delivers the fully unauthenticated discovery experience: location
resolution, the filterable and sortable salon list, and the salon detail screen
with live queue indicator, offers, service catalog, and reviews. Booking initiation
(the "Book" tap) is in scope here only as a trigger that hands off to the auth
gate or to the slot picker.

### Story 3.1: Salon discovery API

**As a** customer, **I want** the server to return a list of nearby salons with
distance, pricing, average duration, average rating, and load category, **so that**
I can compare options before visiting.

**Acceptance criteria:**
- [ ] `GET /api/v1/salons?lat={}&lng={}&radius_km={}&sort={}&max_price_inr={}&min_rating={}`
  returns salons within `radius_km` (default configurable, max 20 km) of the
  given coordinates, sorted by `sort` (`distance` | `avg_duration` | `min_price`;
  default `distance`).
- [ ] Each salon in the response includes: `id`, `name`, `distance_km` (computed
  from coordinates), `min_price_inr` (lowest `Service.price_inr` where `active = true`),
  `avg_duration_minutes` (average of `Service.duration_minutes` where `active = true`),
  `average_rating` (1 decimal place, null if no ratings), `review_count`,
  `load_category` (`"quiet"` | `"moderate"` | `"busy"`).
- [ ] `load_category` is computed server-side from the count of confirmed bookings
  in the next 2 hours relative to available capacity (capacity = number of active
  staff × concurrent slots). The raw booking list is not returned
  (NFR-PRIV-01, NFR-PRIV-02).
- [ ] Salons with `active = false` services only (no active services) are excluded
  from results (FR-P-SVC-04).
- [ ] Response is paginated: `{ data: [], meta: { total, page, pageSize } }` per
  API contract rules.
- [ ] Response for the initial page loads within 3 seconds on standard load
  (NFR-PERF-01); a slow-query plan is documented if any join exceeds 50ms on a
  representative data set.
- [ ] Unit tests cover: distance filter, sort orders, load_category computation
  (quiet/moderate/busy thresholds), salons without active services excluded.

**Dependencies:** 1.2
**Complexity:** L

---

### Story 3.2: Salon detail API (profile, services, offers, reviews)

**As a** customer, **I want** the server to return full salon details including
services, active offers, and paginated reviews, **so that** I can evaluate the
salon before booking.

**Acceptance criteria:**
- [ ] `GET /api/v1/salons/:id` returns: salon profile fields (`name`, `address`,
  `city`, `phone`, `operating_hours`), `average_rating`, `review_count`, list of
  active services (`name`, `duration_minutes`, `price_inr` — `slot_duration_minutes`
  is NOT returned in this response), list of active non-expired offers.
- [ ] `GET /api/v1/salons/:id/queue` returns only `{ queue_depth: number,
  load_category: string, computed_at: string (UTC ISO 8601) }`. No booking IDs,
  customer names, or scheduled times are present in this response (NFR-PRIV-01,
  NFR-PRIV-02).
- [ ] `GET /api/v1/salons/:id/reviews?page={}&pageSize=10` returns paginated
  reviews, most recent first. Each review: `{ stars, review_text, created_at }`.
  The reviewer's `customer_id` and `name` are never returned in this response
  (FR-C-RAT-05, NFR-PRIV-01); attribution is always "Verified customer" at the
  client layer.
- [ ] Expired offers (`expiry_date < current date`) are excluded from the detail
  response (FR-P-OFFER-03).
- [ ] 404 returned for unknown `salon_id`.
- [ ] Unit tests cover: offer expiry exclusion, queue response contains no PII,
  review response contains no customer name.

**Dependencies:** 1.2
**Complexity:** M

---

### Story 3.3: Location resolution and discovery screen (Flutter)

**As a** customer, **I want** to grant location permission or manually enter an
area, **so that** the app can show me salons near my chosen location.

**Acceptance criteria:**
- [ ] On first launch with no stored location, `location_prompt_card` is shown
  above an empty salon list. Tapping "Use my location" triggers the OS permission
  dialog (FR-C-LOC-01).
- [ ] If permission is granted, device coordinates are resolved, reverse-geocoded
  to a readable address, and set as the search location. The salon list loads
  immediately.
- [ ] If permission is denied, `location_prompt_card` shows "Location access
  denied. Enter a location to find nearby salons." with an "Open Settings" button
  that deep-links to the app's permission settings (iOS and Android).
- [ ] Tapping "Enter a location instead" or the `search_bar` opens the
  `LocationSearch` overlay. Searching requires a minimum of 3 characters before
  an API call is fired (debounce 300ms). Results are displayed as tappable address
  rows.
- [ ] Selecting a location from `LocationSearch` sets the search location, stores
  it (FR-C-LOC-03: single most-recently-used value in `flutter_secure_storage` or
  equivalent persistent local store), and dismisses the overlay.
- [ ] On subsequent launches, the stored location is pre-populated without showing
  `location_prompt_card` and the salon list loads immediately (FR-C-LOC-03).
- [ ] Loading state shows 3 shimmer placeholder cards. Initial results appear
  within 3 seconds (NFR-PERF-01) on standard connection.
- [ ] Network failure on list load shows a `retry_card` with "Try again" button.
- [ ] `search_bar` semantic label: "Current search location. Tap to change."

**Dependencies:** 3.1, 1.3
**Complexity:** L

---

### Story 3.4: Discovery list — sort, filter, and salon cards (Flutter)

**As a** customer, **I want** to sort and filter the salon list by distance,
speed, and price, **so that** I can quickly find a salon that fits my needs.

**Acceptance criteria:**
- [ ] Sort control offers three options: "Nearest" (distance ascending, default),
  "Fastest" (avg_duration ascending), "Lowest price" (min_price ascending). Changing
  the sort re-orders the cached result set client-side without a new API call
  (FR-C-DISC-02). Active sort option is visually highlighted.
- [ ] Each `salon_card` displays: salon name (single line, ellipsis if truncated),
  distance chip (e.g., "0.8 km"), load indicator chip ("Quiet" / "Moderate" / "Busy",
  color-coded green/amber/red), starting price ("From ₹{min_price}"), average
  duration ("Avg {N} min"), and rating row (star icon + rating + review count).
  Rating row is hidden entirely when `review_count = 0` (FR-C-DISC-03, FR-C-DISC-04).
- [ ] `FilterSheet` bottom sheet provides: max distance slider (0.5–20 km, step
  0.5 km), max price slider (₹50–₹5000, step ₹50), minimum rating selector
  (1–5 stars). "Apply filters" calls the API with filter parameters. "Reset filters"
  resets all controls to unconstrained defaults. Active filter count badge is shown
  on the filter button (hidden when 0 active filters) (FR-C-DISC-05).
- [ ] When `FilterSheet` is re-opened, controls are pre-populated with the currently
  applied filter values (not the default values).
- [ ] Empty state (no salons match): illustration + "No salons found nearby" headline
  + body + "Clear filters" CTA if filters are active (FR-C-DISC-06).
- [ ] Tapping a `salon_card` navigates to `SalonDetail` for that salon (FR-C-DET-01).
- [ ] Pull-to-refresh re-fetches the list with current location and active filters.
- [ ] `salon_card` semantic label includes all visible data fields in sequence.

**Dependencies:** 3.3
**Complexity:** M

---

### Story 3.5: Salon detail screen (Flutter)

**As a** customer, **I want** to see a salon's full details — operating hours,
services with pricing, active offers, live queue, and reviews — **so that** I
can decide whether to book without needing to call the salon.

**Acceptance criteria:**
- [ ] `SalonDetail` displays: salon name, full address, phone number as a tappable
  `tel:` link, operating hours with expand/collapse toggle, queue indicator,
  offers section (hidden entirely if no active offers), service list with one
  "Book" button per service row, ratings summary, and paginated review list
  (FR-C-DET-02 through FR-C-DET-05).
- [ ] `queue_indicator_card` shows `queue_depth` as "{N} people ahead" (or
  "0 people ahead — walk right in") and `load_category` as a categorical label.
  The card auto-refreshes every 30 seconds via a background GET to
  `/api/v1/salons/:id/queue` without triggering a full-screen reload
  (BLoC partial state update). Auto-refresh pauses when the app is in the background
  and resumes on foreground (FR-C-DET-03).
- [ ] Queue indicator load failure shows "Queue info unavailable" without exposing
  a count of 0. The card is manually retryable by tapping it.
- [ ] Service list shows `duration_minutes` (customer-facing duration); `slot_duration_minutes`
  is never displayed to the customer.
- [ ] "Book" button per service row: if authenticated, navigates to `SlotPicker`
  for that service; if unauthenticated, shows `AuthGate` modal. The selected
  service is preserved in BLoC state through the auth flow.
- [ ] Sticky bottom CTA: when no service has been tapped, tapping it scrolls
  the screen to the service list with a brief highlight animation rather than
  initiating a booking.
- [ ] Review list paginates (pageSize 10); "Show more reviews" appends the next
  page inline.
- [ ] Each review shows stars, relative date, review text (truncated to 3 lines
  with "Read more" link), and "Verified customer" attribution; no real customer
  name is ever shown (FR-C-RAT-05, NFR-PRIV-01).
- [ ] Offer cards show title, description, optional expiry date, and the persistent
  "Discount applied at salon on payment." disclaimer (FR-P-OFFER-04).
- [ ] Widget tests cover: queue indicator renders correct text from API data,
  auto-refresh fires at 30s interval, reviews use "Verified customer" label,
  unauthenticated book tap shows AuthGate.

**Dependencies:** 3.2, 3.3, 2.3
**Complexity:** L

---

## Epic 4: Slot Engine & Availability API (Backend)

This epic delivers the server-side slot computation engine. It is the
highest-criticality backend component: it determines available booking windows
and prevents double-bookings under concurrent load.

### Story 4.1: Slot computation service (SlotService)

**As a** developer, **I want** a `SlotService` that computes available time slots
for a given salon, service, and date, **so that** customers are shown only genuinely
available booking windows.

**Acceptance criteria:**
- [ ] `SlotService.getAvailableSlots({ businessId, serviceId, date })` returns an
  array of available `scheduled_start` UTC timestamps for the given date.
- [ ] Computation logic: for each minute interval of `slot_duration_minutes` within
  the salon's `operating_hours` for the requested day, a slot is available if no
  existing `Booking` with `status = confirmed` overlaps the window
  `[scheduled_start, scheduled_start + slot_duration_minutes)`.
- [ ] Slots outside `operating_hours` for the requested day are never returned.
- [ ] A day with `operating_hours[day] = null` (salon closed) returns an empty
  array.
- [ ] The service is a standalone TypeScript module in `src/services/slot.service.ts`
  with no Express imports (base-rules.md §3.1).
- [ ] Unit tests cover (base-rules.md §3.10):
  - All slots returned when no bookings exist.
  - Slots blocked when a confirmed booking occupies the window.
  - Slots at the open boundary (9:00 AM with slot duration 30 min → first slot
    is 9:00 AM, not 8:45 AM).
  - Slots at the close boundary (last slot ends exactly at close time — no slot
    that would run past close).
  - Cancelled and no-show bookings do not block slots.
  - Slots returned for `slot_duration_minutes` (not `duration_minutes`).
- [ ] `SlotService` is independently unit-testable without a running database
  (repositories are injected as interfaces).

**Dependencies:** 1.1, 1.2
**Complexity:** L

---

### Story 4.2: Slots API endpoint and Redis caching

**As a** customer, **I want** available time slots to load within 2 seconds,
**so that** I can choose a booking time without frustrating delays.

**Acceptance criteria:**
- [ ] `GET /api/v1/slots?business_id={}&service_id={}&date={}` calls `SlotService.getAvailableSlots`
  and returns available slot timestamps: `{ data: [{ scheduled_start: string (UTC ISO 8601) }] }`.
- [ ] Response returns within 2 seconds under normal load (NFR-PERF-02). If
  uncached, the slot computation plus database query completes within this budget.
- [ ] Slot results are cached in Redis with key `slots:{business_id}:{service_id}:{date}`.
  Cache TTL is configurable (default 60 seconds). On cache hit, the result is
  returned without a database query.
- [ ] Cache is invalidated for `(business_id, service_id, date)` when a booking
  is created, cancelled, or marked no-show for that combination (base-rules.md §3.6).
- [ ] The endpoint requires no authentication (customers browsing slots before
  committing to book is an unauthenticated use case — auth is only needed at
  booking creation).
- [ ] Returns `400` for missing or invalid `business_id`, `service_id`, or `date`.
  Returns `404` if the salon or service does not exist.
- [ ] Integration test covers: slot returned on first call (cache miss), same slot
  returned on second call (cache hit), slot absent after a booking is created
  for it.

**Dependencies:** 4.1
**Complexity:** M

---

## Epic 5: Slot Booking (Customer)

This epic delivers the customer's booking flow: the slot picker, booking
confirmation, and the server-side booking creation with concurrency control.

### Story 5.1: Booking creation API with concurrency control

**As a** customer, **I want** my booking to be guaranteed once the server accepts
it, **so that** I can rely on having the slot I selected.

**Acceptance criteria:**
- [ ] `POST /api/v1/bookings` (authenticated) accepts `{ business_id, service_id,
  scheduled_start (UTC ISO 8601) }`. Creates a `Booking` record with
  `status = confirmed` and returns `201` with the full booking record including
  `id`, `scheduled_start`, `scheduled_end` (= `scheduled_start + slot_duration_minutes`).
- [ ] The booking creation query runs inside a database transaction with
  `SELECT ... FOR UPDATE` on the relevant time-slot range to prevent concurrent
  double-booking (NFR-REL-01, base-rules.md §3.4, §3.5).
- [ ] If a conflicting confirmed booking is found within the transaction, the
  transaction is rolled back and the endpoint returns `409 Conflict` with error
  code `SLOT_CONFLICT` (FR-C-BOOK-07).
- [ ] After `COMMIT`: (a) Redis cache keys for `(business_id, service_id, date)`
  are invalidated; (b) an event is published to the Redis Pub/Sub channel
  `salon:{business_id}` for the WebSocket relay to update connected customers'
  queue indicators; (c) booking confirmation notifications are dispatched
  asynchronously (fire-and-forget — notification failure must not roll back the
  booking) (base-rules.md §3.6, FR-C-BOOK-05, FR-C-BOOK-06).
- [ ] The booking is durable after the `201` response: a subsequent server restart
  does not lose the confirmed booking record (NFR-REL-02).
- [ ] `scheduled_start` must fall within the salon's operating hours and on an
  available slot (validated inside the transaction, not just in application logic).
- [ ] Returns `400` if `scheduled_start` is in the past, or `service_id` is
  inactive.
- [ ] Integration tests cover: successful booking creation, concurrent POST for
  the same slot returns 409 for the second caller, booking record persists after
  service restart.

**Dependencies:** 4.2, 2.1, 2.2
**Complexity:** L

---

### Story 5.2: Slot picker screen (Flutter)

**As a** customer, **I want** to browse available time slots for a chosen service
and select one, **so that** I can confirm a specific appointment time.

**Acceptance criteria:**
- [ ] `SlotPicker` screen is reached after tapping "Book" on a service row in
  `SalonDetail` (authenticated). A non-interactive `booking_summary_card` at the
  top shows salon name, service name, duration, and price. A "Change service" link
  pops back to `SalonDetail`.
- [ ] Date selector: horizontal scrollable row of date pills, today + 13 days
  (14 total). Closed days (per `Business.operating_hours`) are greyed and not
  tappable. "Today" label replaces the day abbreviation for the current date.
- [ ] Selecting a date fires `GET /api/v1/slots?...` for that date and shows a
  shimmer loading state. Available slots appear within 2 seconds (NFR-PERF-02).
- [ ] Only available slots are shown (no greyed-out unavailable chips); each slot
  is a tappable chip showing the time in device local time (FR-C-BOOK-02,
  FR-C-BOOK-03).
- [ ] Tapping a slot chip selects it (filled primary color). Tapping a different
  chip deselects the previous one. The "Confirm booking" button is disabled until
  a chip is selected.
- [ ] "Pay at the salon after your appointment. No payment needed now." caption
  is visible above the confirm button (FR-C-BOOK-08).
- [ ] Tapping "Confirm booking" fires `POST /api/v1/bookings`. While loading, the
  button shows a spinner and is disabled.
- [ ] 409 Conflict: inline error "That slot was just booked by someone else.
  Please choose a different time." The conflicting chip is marked unavailable
  for this session. The slot list refreshes in the background (FR-C-BOOK-07).
- [ ] JWT expired mid-flow (401 on POST): `AuthGate` shown; after re-auth, POST
  is retried automatically with the preserved slot context.
- [ ] If all 14 days in the window are closed: slots area shows "This salon has
  no available slots in the next 2 weeks."
- [ ] Widget tests cover: slot chips appear for API response, 409 shows inline
  error and deselects chip, closed-day pills are not tappable.

**Dependencies:** 5.1, 3.5
**Complexity:** L

---

### Story 5.3: Booking confirmation screen (Flutter)

**As a** customer, **I want** to see a clear confirmation with my booking details
after I confirm a slot, **so that** I have a record of what I booked.

**Acceptance criteria:**
- [ ] `BookingConfirmation` screen appears only after a `201` response from
  `POST /api/v1/bookings`. Screen shows: success checkmark animation (respects
  OS "Reduce Motion" — static checkmark if enabled), salon name, service name,
  date and time in device local time, duration, price with "pay at salon" note,
  and booking reference (`Booking.id`) in monospace.
- [ ] A copy icon adjacent to the booking reference copies it to the clipboard;
  a "Copied" toast confirms.
- [ ] "A confirmation has been sent to your phone." note is displayed (FR-C-BOOK-05).
- [ ] OS back gesture is overridden to navigate to `DiscoveryList` (root), not
  back to `SlotPicker`. Tapping "Done" navigates to root. Tapping "View my
  bookings" navigates to `BookingList`. Both clear the booking navigation stack.
- [ ] If the app is killed immediately after this screen appears, the booking
  record is retrievable from `BookingList` on next launch (NFR-REL-02).
- [ ] Widget tests cover: confirmation card renders all booking fields, back gesture
  navigates to root not SlotPicker, copy button copies booking reference.

**Dependencies:** 5.2
**Complexity:** S

---

## Epic 6: Booking Management (Customer)

This epic delivers the customer's ability to view, cancel, and reschedule their
bookings, and the server-side endpoints that support these operations.

### Story 6.1: Booking management API (list, cancel, reschedule)

**As a** customer, **I want** the server to list my bookings and allow me to cancel
or reschedule any confirmed upcoming booking, **so that** I can manage my appointments
through the app.

**Acceptance criteria:**
- [ ] `GET /api/v1/bookings` (authenticated) returns all bookings for the
  authenticated customer, ordered by `scheduled_start` descending. Response
  includes `status`, `scheduled_start`, `salon name`, `service name`,
  `booking_ref (id)` for each booking (FR-C-MGT-01, FR-C-MGT-02). Enforces
  that only the requesting customer's bookings are returned (NFR-SEC-04).
- [ ] `PATCH /api/v1/bookings/:id/cancel` (authenticated, own booking only)
  transitions `status` from `confirmed` to `cancelled`. Releases the slot (cache
  invalidated, Redis event published). Dispatches cancellation notifications
  asynchronously to the customer and the salon partner (FR-C-MGT-03). Returns
  `200`. Returns `409` if booking is not in `confirmed` state.
- [ ] `PATCH /api/v1/bookings/:id/reschedule` (authenticated, own booking only)
  accepts `{ scheduled_start }`. Runs inside a transaction with `SELECT ... FOR UPDATE`
  (same concurrency control as booking creation, FR-C-MGT-04). On success, updates
  `scheduled_start` and `scheduled_end`; old slot is released (cache/event). Returns
  `200`. Returns `409` for slot conflict; `400` if the booking is not in `confirmed`
  state.
- [ ] Unit tests cover: cancel transitions status, cancel returns 409 for already-
  cancelled booking, reschedule releases old slot and blocks new slot, reschedule
  conflict returns 409.

**Dependencies:** 5.1
**Complexity:** M

---

### Story 6.2: Booking list and detail screens (Flutter)

**As a** customer, **I want** to see all my upcoming and past bookings in one
place and tap into the details of any booking, **so that** I always know what
I have scheduled.

**Acceptance criteria:**
- [ ] `BookingList` screen is the "My Bookings" tab in the bottom navigation.
  Tapping the tab when unauthenticated shows `AuthGate`.
- [ ] Two tabs: "Upcoming" (confirmed bookings with future `scheduled_start`) and
  "Past" (completed, cancelled, no-show, or confirmed past).
- [ ] Each `booking_card` displays: salon name, service name, date/time in device
  local time, status chip (Confirmed green, Cancelled red, Completed grey,
  No-show amber), and booking reference. Upcoming confirmed bookings also show
  "Reschedule" and "Cancel" buttons (FR-C-MGT-02).
- [ ] Tapping the card body (not action buttons) navigates to `BookingDetail`.
- [ ] `BookingDetail` shows all booking fields plus salon address and a tappable
  phone number. "View salon" link navigates to `SalonDetail`. A "Rate your visit"
  button is shown when `status = completed` and no rating exists for the booking.
- [ ] "A reminder will be sent 24 hours before your appointment." informational
  note is shown on confirmed upcoming `BookingDetail` (FR-C-MGT-05).
- [ ] "Completed booking already rated" state: `rate_now_button` is hidden; a
  non-interactive star summary replaces it.
- [ ] Pull-to-refresh re-fetches the booking list.
- [ ] Widget tests cover: upcoming tab shows only confirmed future bookings, past
  tab shows completed/cancelled/no-show, rate_now_button hidden after rating.

**Dependencies:** 6.1, 3.5, 2.3
**Complexity:** M

---

### Story 6.3: Cancel flow (Flutter)

**As a** customer, **I want** to cancel an upcoming booking with a confirmation
step, **so that** I don't accidentally release a slot I intended to keep.

**Acceptance criteria:**
- [ ] Tapping "Cancel" on a `booking_card` or `BookingDetail` shows the
  `CancelConfirmation` bottom sheet.
- [ ] `CancelConfirmation` shows: "Cancel booking?" title, irreversibility warning
  ("Your slot will be released and someone else may book it. This cannot be
  undone."), a read-only mini booking summary (salon, service, date/time), a
  "Cancel booking" destructive red button, and a "Keep my booking" secondary button.
- [ ] Tapping "Cancel booking" calls `PATCH /api/v1/bookings/:id/cancel`. While
  loading, both buttons are disabled. On success, the sheet dismisses, the booking
  status updates to "Cancelled" on the list or detail view, and a brief toast
  "Booking cancelled." appears (FR-C-MGT-03).
- [ ] API error: sheet re-enables buttons; shows inline "Couldn't cancel. Try again."
- [ ] 409 response (booking already cancelled): "This booking is already cancelled."
  Sheet closes, list refreshes.
- [ ] `cancel_button` semantic label: "Confirm cancellation of {service_name} at
  {salon_name} on {datetime}."
- [ ] Widget tests cover: cancel button calls correct endpoint, 409 error shows
  correct message, "Keep my booking" dismisses without API call.

**Dependencies:** 6.2
**Complexity:** S

---

### Story 6.4: Reschedule flow (Flutter)

**As a** customer, **I want** to reschedule an upcoming booking to a different
available slot at the same salon for the same service, **so that** I can adjust
my appointment without cancelling and rebooking.

**Acceptance criteria:**
- [ ] Tapping "Reschedule" navigates to `RescheduleSlotPicker`, which is the
  `SlotPicker` screen with the title "Reschedule — Choose a new time", a
  `current_appointment_text` showing the existing date/time, and no "Change
  service" link.
- [ ] The existing booking date is not excluded from the date selector (customer
  can pick a different time on the same day).
- [ ] "Confirm new time" button fires `PATCH /api/v1/bookings/:id/reschedule`
  with the new `scheduled_start`. All slot conflict behaviour is identical to
  new booking (FR-C-MGT-04): 409 shows the same inline error as in `SlotPicker`.
- [ ] On success, app navigates to `RescheduleConfirmation` showing the new
  date/time, salon, service, and unchanged booking reference.
- [ ] OS back on `RescheduleConfirmation` navigates to `BookingList`, not back
  to `RescheduleSlotPicker`.
- [ ] 409 (booking no longer reschedulable — e.g., completed or cancelled since
  intent): "This booking can no longer be rescheduled." Navigates back to
  `BookingDetail` on dismiss.
- [ ] Widget tests cover: confirm button calls reschedule endpoint, 409 shows
  inline error, confirmation navigates to BookingList on back.

**Dependencies:** 6.2, 6.1
**Complexity:** M

---

## Epic 7: Ratings & Reviews (Customer)

This epic delivers the post-visit rating and review flow: the server-side rating
API, the rating submission screen, and the push-notification trigger from the
partner's "mark complete" action.

### Story 7.1: Ratings API

**As a** customer, **I want** the server to accept my star rating and optional
review after a completed visit, **so that** my feedback is recorded and shown to
other customers.

**Acceptance criteria:**
- [ ] `POST /api/v1/ratings` (authenticated) accepts `{ booking_id, stars: 1–5,
  review_text?: string (max 500 chars) }`. Creates a `Rating` record and updates
  `Business.average_rating` (or recomputes it from all ratings). Returns `201`.
- [ ] Returns `400` if `stars < 1` or `stars > 5`, or if `review_text` exceeds
  500 characters.
- [ ] Returns `409` if a rating already exists for `booking_id` (FR-C-RAT-03).
- [ ] Returns `403` if `booking.status != 'completed'` (FR-C-RAT-04), or if the
  authenticated customer is not the booking owner.
- [ ] `GET /api/v1/ratings?business_id={}&page={}&pageSize=10` returns paginated
  ratings for the business, most recent first. Each rating contains `{ stars,
  review_text, created_at }`. The `customer_id`, `customer_name`, and `customer_phone`
  are NEVER returned in this response (FR-C-RAT-05, NFR-PRIV-01).
- [ ] `Business.average_rating` is computed to 1 decimal place and is consistent
  with the count of all submitted ratings for the business (FR-C-RAT-06).
- [ ] Unit tests cover: rating created for completed booking, 409 for duplicate
  rating, 403 for non-completed booking, review_text stripped from API response,
  average_rating recomputes correctly after new rating.

**Dependencies:** 5.1
**Complexity:** M

---

### Story 7.2: Rating submission screen (Flutter)

**As a** customer, **I want** to submit a 1–5 star rating and optional written
review after my visit, **so that** I can share my experience with other customers.

**Acceptance criteria:**
- [ ] `RatingSubmission` screen is reachable from: push notification deep-link
  (after partner marks complete), `rate_now_button` on `BookingDetail`, and the
  rating banner on `BookingList` "Past" tab.
- [ ] Screen shows a non-interactive visit summary (salon name, service, date).
- [ ] 5-star selector: tapping star N fills stars 1–N and displays a label
  ("Poor" / "Fair" / "Good" / "Great" / "Excellent"). Tapping the highest
  selected star again resets to 0 stars. "Submit review" button is disabled
  until at least 1 star is selected (FR-C-RAT-02).
- [ ] Optional review text field: max 500 characters. Character counter appears
  while typing. Caption below field: "Your comment will be visible to everyone
  as 'Verified customer'."
- [ ] Tapping "Submit review" calls `POST /api/v1/ratings`. Loading spinner inside
  button; inputs disabled during call. On success, navigate to `RatingConfirmation`.
- [ ] 409 (already rated): "You've already rated this visit." Navigate back to
  `BookingDetail`.
- [ ] 400 (booking not completed): "You can only rate a completed visit."
  Navigate back.
- [ ] Network failure: re-enable inputs; show "Couldn't submit. Check your
  connection and try again." Stars and text are preserved.
- [ ] `RatingConfirmation` screen: success animation (respects Reduce Motion),
  "Thanks for your feedback!", shows the submitted star rating and review text.
  "Done" returns to `BookingDetail` or `BookingList`.
- [ ] "Skip for now" link returns to originating screen without submitting. Rating
  prompt remains available via `BookingDetail`.
- [ ] Star selector semantic labels per star: "1 star — Poor", "2 stars — Fair",
  etc. Container announces total selected stars. Star icons are min 48pt with
  8pt gaps.
- [ ] Widget tests cover: submit disabled with 0 stars, star reset on re-tap,
  409 shows correct error message, Reduce Motion shows static checkmark.

**Dependencies:** 7.1, 6.2
**Complexity:** M

---

### Story 7.3: Rating prompt banner and push notification trigger (Flutter + Backend)

**As a** customer, **I want** to receive a rating prompt immediately after my
visit is marked complete, **so that** the app captures my feedback while my
experience is fresh.

**Acceptance criteria:**
- [ ] When the partner marks a booking as complete (`PATCH /api/v1/bookings/:id/complete`),
  the backend dispatches an asynchronous push notification (FCM or equivalent) to
  the customer's device with text: "How was your visit at {salon_name}? Share your
  feedback." Notification failure must not affect the mark-complete API response
  (FR-C-RAT-01).
- [ ] Tapping the push notification deep-links directly to `RatingSubmission` for
  that booking. If the booking is already rated (stale notification), `RatingSubmission`
  detects the existing rating via the API and shows "You've already submitted a
  review for this visit." with a "Close" button.
- [ ] A `RatingPromptBanner` appears at the top of `BookingList` "Past" tab when
  the authenticated customer has one or more completed, unrated bookings.
  Banner text: "How was your visit to {salon_name}?" (single pending) or
  "You have {N} visits to rate." (multiple). "Rate now" link navigates to
  `RatingSubmission` for the most recent pending booking. Dismissing the banner
  hides it for the session only; `rate_now_button` on `BookingDetail` remains
  accessible.
- [ ] The notification dispatch happens after the booking `COMMIT` as an async
  fire-and-forget (base-rules.md §3.6). A failure to dispatch the notification
  is logged at WARN but does not fail the `PATCH` response.

**Dependencies:** 7.2, 8.3 (partner mark-complete endpoint)
**Complexity:** M

---

## Epic 8: Salon Partner Authentication

This epic delivers the partner app's authentication flow: login, session management,
and password reset. Partner account creation is off-app (administrator-provisioned)
and is not in scope for this epic.

### Story 8.1: Partner auth API (login, password reset)

**As a** salon partner, **I want** to log in with my email and password and reset
my password via email if I forget it, **so that** I can securely access my salon's
management tools.

**Acceptance criteria:**
- [ ] `POST /api/v1/auth/partner/login` accepts `{ email, password }`. Returns
  `200` with a JWT (RS256, separate partner claims) on correct credentials. Returns
  `401` for wrong email or password (single undifferentiated message — do not
  enumerate accounts). Returns a distinct error body for a suspended account so
  the app can surface the correct message to the partner.
- [ ] The JWT payload includes `{ sub: partnerId, businessId, role: "partner" }`.
- [ ] `POST /api/v1/auth/partner/forgot-password` accepts `{ email }`. Always
  returns `200` regardless of whether the email is registered (prevents account
  enumeration). If the email exists, a password reset link is sent asynchronously.
  Rate-limited: returns `429` after repeated requests.
- [ ] Password reset link expires after a configurable period (default 60 minutes).
  The Architect specifies the reset mechanism (email link with signed token).
- [ ] All partner routes beyond login enforce `req.user.businessId === resource.businessId`
  (NFR-SEC-04, base-rules.md §3.7).
- [ ] Unit tests cover: correct login returns JWT with businessId claim, wrong
  password returns 401, forgot-password returns 200 regardless of email existence.

**Dependencies:** 1.1, 1.2
**Complexity:** M

---

### Story 8.2: Partner app — login and session management (Flutter)

**As a** salon partner, **I want** to sign in to the partner app once and stay
signed in across sessions until I explicitly log out, **so that** I can access
my dashboard quickly during a busy workday.

**Acceptance criteria:**
- [ ] `PartnerSplash` checks `flutter_secure_storage` for a valid JWT on cold start.
  Valid token → navigate to `PartnerDashboard`. Expired token → attempt refresh;
  on failure, navigate to `PartnerLogin`. No token → navigate to `PartnerLogin`.
- [ ] `PartnerLogin` screen: email field with email keyboard, password field with
  `obscureText: true` and visibility toggle, "Sign in" button disabled until
  both fields are non-empty. Calls `POST /api/v1/auth/partner/login`.
- [ ] Invalid credentials (401): "Incorrect email or password." Suspended account:
  "Your account has been suspended. Please contact support at {support_email}."
- [ ] `ForgotPassword` screen: email field, "Send reset link" button. Button
  disabled after send for 60 seconds with countdown. Always shows success message
  regardless of email registration status (prevents enumeration).
- [ ] All partner screens (post-login) check for a valid JWT on mount. Expired
  JWT mid-session: bottom sheet "Your session has expired. Please sign in again."
  with a "Sign in" button. After re-auth, the partner repeats the interrupted
  operation manually (no auto-retry of writes).
- [ ] Logout clears JWT from `flutter_secure_storage` and navigates to
  `PartnerLogin` with navigation stack cleared.
- [ ] Partner app is fully gated on authentication; no screen in the partner app
  is reachable without a valid JWT.
- [ ] "Don't have an account? Contact us at {support_email}." caption on login
  screen directs unregistered partners to off-app onboarding.
- [ ] Widget tests cover: splash navigates to dashboard on valid token, splash
  navigates to login on missing token, expired-session sheet appears on 401 from
  protected route.

**Dependencies:** 8.1, 1.4
**Complexity:** M

---

## Epic 9: Salon Profile Management (Partner)

This epic delivers the partner's ability to create and edit their salon's public
profile: name, address, phone, and day-by-day operating hours.

### Story 9.1: Business profile API (create and update)

**As a** salon partner, **I want** the server to store my salon's profile and
reflect changes to customers within 60 seconds, **so that** my profile always
shows accurate information.

**Acceptance criteria:**
- [ ] `POST /api/v1/businesses` (authenticated partner) creates a `Business` record
  with `name`, `address`, `city` (fixed to launch city, set by backend), `phone`,
  `operating_hours`. Returns `201` with the created record.
- [ ] `PATCH /api/v1/businesses/:id` (authenticated, must own the business)
  updates allowed fields. Returns `200`. Returns `403` if the partner does not
  own the business.
- [ ] `operating_hours` validation: for each day marked open, `close_time > open_time`.
  Returns `400` with a structured error if this constraint is violated (FR-P-PROF-02).
- [ ] After a successful `POST` or `PATCH`, any cached salon discovery or detail
  responses are invalidated so that customer-facing views reflect the change
  within 60 seconds (FR-P-PROF-03). The Architect specifies the cache invalidation
  strategy (e.g., short TTL + Redis key deletion).
- [ ] Unit tests cover: operating hours validation (close before open returns 400),
  partner cannot modify another partner's business (returns 403).

**Dependencies:** 8.1
**Complexity:** M

---

### Story 9.2: Salon profile screen (Flutter)

**As a** salon partner, **I want** to create and edit my salon's public profile
from the mobile app, **so that** customers see accurate information about my salon.

**Acceptance criteria:**
- [ ] `SalonProfile` screen is reachable from the "Profile" tab. On first login
  with no profile, the app routes directly to create mode; the partner cannot reach
  the dashboard until a profile is saved (per UX spec routing decision).
- [ ] Create mode: all fields empty, button "Save profile". Edit mode: fields
  pre-populated, read-only view with "Edit" button. Tapping "Edit" switches to
  editable state; an "X" cancel button appears.
- [ ] Fields: salon name (required, max 100 chars), street address (required, max
  200 chars), city (read-only, shows launch city), phone number (required, 10
  digits, `+91` prefix non-editable).
- [ ] Operating hours section: one row per day (Mon–Sun). Each row has an "Open"
  toggle; when ON, open and close time pickers are active. Closed days have disabled
  pickers. Toggling ON with no times set is an invalid state; `save_button` is
  disabled until times are set for the newly-enabled day.
- [ ] Validation runs on save (not per-keystroke). All validation errors are shown
  simultaneously (not one-at-a-time). Scroll to first error on failed save
  (FR-P-PROF-02).
- [ ] Error conditions: salon name empty, address empty, phone not 10 digits, any
  open day with close time ≤ open time.
- [ ] Unsaved changes + tapping cancel: `DiscardChanges` sheet shown if more than
  one field was changed.
- [ ] Successful save: navigate to `PartnerDashboard` (create mode) or revert to
  read-only view (edit mode). "Profile saved." non-intrusive banner shown.
- [ ] `city_field` is non-editable text (not an input field).
- [ ] Widget tests cover: save disabled when required fields empty, operating hours
  validation error shown, discard sheet appears on cancel with changes.

**Dependencies:** 9.1, 8.2
**Complexity:** M

---

## Epic 10: Service & Pricing Catalog (Partner)

This epic delivers the partner's service catalog management — adding, editing, and
soft-deleting services — and the informational offers management.

### Story 10.1: Service catalog API (CRUD)

**As a** salon partner, **I want** the server to store and manage my service
catalog with pricing and duration, **so that** customers see accurate service
information and the slot engine can compute correct availability.

**Acceptance criteria:**
- [ ] `POST /api/v1/services` (authenticated partner) accepts `{ name, duration_minutes,
  slot_duration_minutes, price_inr }`. Creates a `Service` record with `active = true`.
  Returns `201`. Returns `400` if `slot_duration_minutes < duration_minutes`
  (FR-P-SVC-01, partner-catalog.md validation rule).
- [ ] `PATCH /api/v1/services/:id` updates allowed fields. Returns `200`. Returns
  `403` if the partner does not own the service's business. Returns `400` for
  invalid field values.
- [ ] `PATCH /api/v1/services/:id` with `{ active: false }` soft-deletes the
  service (FR-P-SVC-03). Existing confirmed bookings for that service are not
  cancelled; they remain in `confirmed` state and must be fulfilable.
- [ ] `GET /api/v1/businesses/:id/services` returns all active services for the
  business (partner view may include inactive; customer view returns only active
  services — the endpoint must respect the caller's role).
- [ ] `price_inr` is stored as `NUMERIC(10,2)` (base-rules.md §1 Currency rule).
  No floating-point arithmetic occurs in price computation.
- [ ] Unit tests cover: slot_duration < duration returns 400, soft-delete does not
  cancel existing bookings, partner cannot modify another business's service.

**Dependencies:** 9.1
**Complexity:** M

---

### Story 10.2: Service catalog screen (Flutter)

**As a** salon partner, **I want** to add, edit, and remove services from my
catalog using the mobile app, **so that** customers see an accurate list of what
I offer.

**Acceptance criteria:**
- [ ] `CatalogHome` screen has "Services" and "Offers" tabs; "Services" is the
  default.
- [ ] `ServiceList`: each row shows service name, duration (min), price (₹), edit
  (pencil) and delete (trash) icon buttons (both 44pt). Tapping the row body also
  navigates to edit mode. Empty state: "No services yet. Add your first service
  to get started." with an add button. Caption at bottom when 0 services:
  "Your salon only appears to customers once you have at least one service."
  (FR-P-SVC-04).
- [ ] `ServiceForm` (create/edit): service name (required, max 100 chars),
  service duration in minutes (required, positive integer), slot duration in
  minutes (required, positive integer, auto-populates from duration on first
  fill, partner-overridable), price in INR (required, positive, max 2 decimal
  places, "₹" prefix non-editable). Edit mode shows an informational banner if
  the service has upcoming confirmed bookings: "Changes apply to new bookings only."
- [ ] Validation: slot duration must be ≥ service duration (error: "Slot duration
  must be at least as long as the service duration ({N} min)"). All required
  fields must be non-empty. Runs on save.
- [ ] Delete: `DeleteServiceConfirmation` sheet shows service name and the warning
  "Existing bookings for this service will not be affected." Tapping "Remove
  service" calls PATCH with `active = false`. Removed service disappears from
  list (soft-delete). Toast: "'{service_name}' removed from catalog."
- [ ] Unsaved changes on back: `DiscardChanges` sheet shown.
- [ ] Widget tests cover: save disabled until all fields valid, slot duration
  auto-populates from service duration, slot < duration shows validation error,
  delete confirmation sheet appears.

**Dependencies:** 10.1, 8.2
**Complexity:** M

---

### Story 10.3: Offers management screen (Flutter)

**As a** salon partner, **I want** to create, edit, and delete promotional offers
from the app, **so that** customers see accurate promotional information when
browsing my salon.

**Acceptance criteria:**
- [ ] `OfferList` tab in `CatalogHome`: each offer shows title, truncated
  description, expiry date ("Expires {date}" or "No expiry"; "Expired {date}"
  in red for expired), and active/expired badge. Edit and delete icon buttons.
  Persistent banner: "Offers are shown to customers as promotional information.
  Discounts are applied manually at the salon on payment." (FR-P-OFFER-04).
- [ ] `OfferForm` (create/edit): offer title (required, max 100 chars),
  description (required, max 500 chars, character counter). Expiry: "No expiry"
  toggle (default ON); toggling OFF activates a date picker allowing only today
  or future dates. Saving calls `POST /api/v1/offers` or `PATCH /api/v1/offers/:id`.
- [ ] Validation: title required, description required, expiry date (when set)
  must not be in the past (FR-P-OFFER-01).
- [ ] Delete: `DeleteOfferConfirmation` sheet warns the offer will no longer appear
  to customers. Confirms via `DELETE /api/v1/offers/:id` (or `active = false`).
- [ ] Expired offers do not appear on the customer-facing `SalonDetail` screen
  (enforced by API, Story 3.2); the partner still sees them in `OfferList` with
  "Expired" badge for reference.
- [ ] Widget tests cover: no-expiry toggle disables date picker, past date rejected,
  delete sheet appears and calls correct endpoint.

**Dependencies:** 10.2 (same screen, same session), 9.1
**Complexity:** S

---

### Story 10.4: Offers API (CRUD)

**As a** salon partner, **I want** the server to store my promotional offers and
exclude expired ones from customer-facing responses, **so that** customers only
see current promotions.

**Acceptance criteria:**
- [ ] `POST /api/v1/offers` (authenticated partner) accepts `{ title, description,
  expiry_date? (date string or null), active: true }`. Returns `201`. Returns
  `400` if `expiry_date` is in the past.
- [ ] `PATCH /api/v1/offers/:id` updates allowed fields. Returns `403` if the
  partner does not own the offer's business.
- [ ] `DELETE /api/v1/offers/:id` (or PATCH with `active = false`) removes the
  offer from customer-facing views. Returns `200`.
- [ ] Customer-facing responses for salon detail (`GET /api/v1/salons/:id`)
  exclude offers where `expiry_date < current date` OR `active = false`
  (FR-P-OFFER-03).
- [ ] Unit tests cover: expired offer excluded from customer response, past expiry
  date returns 400 on create, partner cannot modify another business's offer.

**Dependencies:** 9.1
**Complexity:** S

---

## Epic 11: Staff Management (Partner)

This epic delivers the partner's ability to manage their team: adding staff, assigning
services they can perform, and configuring their weekly working hours.

### Story 11.1: Staff management API (CRUD)

**As a** salon partner, **I want** the server to store my staff members with their
qualified services and working hours, **so that** scheduling and availability
computation have accurate data.

**Acceptance criteria:**
- [ ] `POST /api/v1/staff` (authenticated partner) accepts `{ name, qualified_service_ids: [],
  working_hours: map<DayOfWeek, TimeRange|null> }`. Creates a `Staff` record with
  `active = true`. Returns `201`.
- [ ] `PATCH /api/v1/staff/:id` updates name, qualified_service_ids, or working_hours.
  Returns `200`. Returns `403` if the partner does not own the staff's business.
- [ ] Validation: for each day where working hours are provided, the staff member's
  start time ≥ salon `operating_hours[day].open` AND end time ≤ salon
  `operating_hours[day].close` (FR-P-STAFF-05). Returns `400` with a structured
  error identifying the violating day(s).
- [ ] `PATCH /api/v1/staff/:id` with `{ active: false }` soft-deletes the staff
  member. Existing confirmed bookings assigned to this staff member are not
  cancelled (FR-P-STAFF-03).
- [ ] `qualified_service_ids` must all belong to the same business; foreign key
  violation returns `400`.
- [ ] Unit tests cover: working hours outside salon hours returns 400, soft-delete
  does not cancel bookings, qualified_service_ids from another business returns 400.

**Dependencies:** 9.1, 10.1
**Complexity:** M

---

### Story 11.2: Staff management screen (Flutter)

**As a** salon partner, **I want** to add, edit, and remove staff members — with
their qualified services and working hours — from the app, **so that** my team
is accurately represented for scheduling.

**Acceptance criteria:**
- [ ] `StaffList` screen: each staff card shows name, services summary (comma-
  separated, max 3 shown then "+N more"), schedule summary (compact day-range
  format or "No schedule set" in amber). Edit (pencil) and remove (trash) icons,
  44pt each. Empty state: "No staff members yet."
- [ ] Warning states on card: "No services assigned" in amber if `qualified_service_ids`
  is empty; "No schedule set" in amber if all days are off.
- [ ] `StaffForm` (create/edit): single scrollable form with three sections:
  basic info (name, required, max 100 chars), services (checkbox list of all
  active catalog services with duration and price sub-text; "Add services to
  the catalog first" note if catalog is empty), working hours (one row per day
  with working toggle and time pickers).
- [ ] Salon's operating hours shown as read-only context ("Salon: Mon–Sat
  9 AM–7 PM, Sun Closed") within the working hours section to aid input.
- [ ] Days the salon is closed are displayed as non-interactive "Salon closed"
  rows.
- [ ] Save requires only a non-empty name; services and hours are optional on
  initial save (incremental onboarding).
- [ ] Validation on save: for each day with working toggle ON, both start and end
  times must be set, end must be after start, start ≥ salon open, end ≤ salon
  close (FR-P-STAFF-04, FR-P-STAFF-05). All errors shown simultaneously.
- [ ] `RemoveStaffConfirmation` sheet: warns that existing bookings are unaffected
  (FR-P-STAFF-03). Tap "Remove staff member" calls PATCH with `active = false`.
- [ ] "Salon operating hours not yet configured" state: working hour toggles are
  disabled; note "Set salon operating hours in Profile before configuring staff
  schedules." with "Go to Profile" link.
- [ ] Widget tests cover: save enabled with name only, working hours validation
  errors all shown simultaneously, remove confirmation sheet appears.

**Dependencies:** 11.1, 10.2, 8.2
**Complexity:** L

---

## Epic 12: Schedule Configuration (Partner)

This epic delivers the partner's schedule configuration screen: a consolidated
view of slot durations per service with inline editing, and an operating hours
summary linking to the profile for editing.

### Story 12.1: Schedule configuration screen (Flutter)

**As a** salon partner, **I want** to review and adjust slot durations for each
service from a dedicated schedule view, **so that** I can fine-tune my booking
calendar's buffer times without navigating to each service individually.

**Acceptance criteria:**
- [ ] `ScheduleConfig` screen is the "Schedule" tab in the partner bottom navigation.
- [ ] Slot Durations section: one row per active service, showing service name,
  a "{duration_minutes} min" reference chip (customer-facing duration), and an
  inline-editable "{slot_duration_minutes} min" field.
- [ ] Tapping the slot duration field makes it editable in-place (numeric keyboard).
  Save (checkmark) and cancel (X) icons appear adjacent. Tapping checkmark calls
  `PATCH /api/v1/services/:id` with updated `slot_duration_minutes`.
- [ ] Live feedback: when `slot_duration_minutes > duration_minutes`, shows
  "+{buffer} min buffer" below the row. When `slot_duration_minutes < duration_minutes`,
  shows amber warning "Slot is shorter than service duration." Save icon is disabled
  until the value is ≥ `duration_minutes`.
- [ ] Validation (immediate, not deferred): must be a positive integer ≥ 1 and
  ≥ `duration_minutes`. Inline error shown below field.
- [ ] Cancel (X) reverts the field to its original value without an API call.
- [ ] Save success: field reverts to display mode with updated value; brief green
  flash or checkmark animation confirms.
- [ ] Operating Hours summary section: read-only list of salon's operating hours
  per day. "Edit in Salon Profile" link navigates to `SalonProfile`.
- [ ] Empty state when no active services: "No services in your catalog. Add
  services to configure slot durations." with "Go to Catalog" link.
- [ ] Widget tests cover: save icon disabled when slot < duration, inline edit
  reverts on cancel, buffer note appears when slot > duration.

**Dependencies:** 10.2, 9.2, 8.2
**Complexity:** M

---

## Epic 13: Booking Dashboard (Partner)

This epic delivers the partner's operational home screen: the queue summary card,
today's booking timeline across staff, the filterable upcoming bookings list, and
the mark-complete and mark-no-show actions.

### Story 13.1: Partner booking management API (list, complete, no-show)

**As a** salon partner, **I want** the server to list my salon's bookings and allow
me to mark them as complete or no-show, **so that** I can manage my day's
appointments and trigger correct downstream effects.

**Acceptance criteria:**
- [ ] `GET /api/v1/partner/bookings?date={}&staff_id={}` (authenticated partner)
  returns all bookings for the partner's business on the specified date, optionally
  filtered by staff. Each booking includes: `scheduled_start`, `scheduled_end`,
  `customer.name`, `service.name`, `staff.name` (or null), `status`,
  `booking_ref (id)` (FR-P-DASH-01, FR-P-DASH-02, NFR-PRIV-03).
- [ ] `PATCH /api/v1/bookings/:id/complete` (authenticated partner, own business
  only) transitions `status` from `confirmed` to `completed`. Returns `200`.
  Returns `409` if booking is not in `confirmed` state. After commit, dispatches
  the customer rating push notification asynchronously (FR-C-RAT-01, FR-P-DASH-03).
- [ ] `PATCH /api/v1/bookings/:id/no-show` (authenticated partner, own business
  only) transitions `status` to `no_show`. Releases the slot (cache invalidation,
  Redis event). Does NOT dispatch a rating push notification (FR-P-DASH-04).
  Returns `200`. Returns `409` if booking is not in `confirmed` state.
- [ ] `GET /api/v1/partner/queue` returns `{ active_now_count, total_today_count,
  remaining_count, load_category }` for the partner's business. No individual
  customer booking details are exposed beyond what the partner already sees in
  their own booking list (NFR-PRIV-03 permits this for the partner's own data).
- [ ] Access control enforced: partner can only see and act on bookings for their
  own `businessId` (NFR-SEC-04, base-rules.md §3.7).
- [ ] Unit tests cover: complete transitions status and triggers rating notification,
  no-show releases slot but does not trigger rating notification, partner cannot
  complete another business's booking (403).

**Dependencies:** 5.1, 8.1
**Complexity:** M

---

### Story 13.2: Partner dashboard screen (Flutter)

**As a** salon partner, **I want** to see my day's schedule at a glance — queue
summary, timeline, and booking list — **so that** I can run my front desk without
a paper register.

**Acceptance criteria:**
- [ ] `PartnerDashboard` is the default screen after login and the "Dashboard" tab
  in bottom navigation. Header shows "Dashboard" and "Today — {Day}, {Date}".
- [ ] Queue summary card at top: "In chair / up next" count, total bookings today,
  remaining bookings, load label. Auto-refreshes every 60 seconds while in
  foreground.
- [ ] Today's timeline: horizontal scrollable time axis covering salon operating
  hours. Each confirmed booking is a proportionally-sized color-coded block showing
  customer name (truncated), service name, and start time. Current time shown as
  a vertical red line. Timeline auto-positions to current time minus 30 minutes
  on load (FR-P-SCHED-03).
- [ ] Staff filter tabs above the timeline: "All staff" + one tab per staff member.
  Selecting a staff member filters timeline to that person's row only. "All staff"
  shows separate rows per staff, stacked vertically.
- [ ] Upcoming bookings list below timeline: date filter bar (today + 13 days,
  today default) and staff filter dropdown (independent of timeline filter).
  Each `partner_booking_card` shows time, customer name, service, staff (or
  "Staff TBD"), booking reference, status chip, and for confirmed bookings:
  "Mark complete" and "No-show" buttons (FR-P-DASH-01, FR-P-DASH-02).
- [ ] Timeline is shown for today only. When a future or past date is selected
  in the list date filter, the timeline shows a note "Timeline shows today's
  schedule only." Action buttons are hidden for past-date bookings regardless
  of status.
- [ ] Tapping a `partner_booking_card` body or timeline block opens
  `BookingDetailSheet` (bottom sheet with full booking fields + action buttons
  for today's confirmed bookings).
- [ ] `MarkCompleteConfirmation` sheet: warns the customer will be prompted to
  review. Tapping "Mark complete" calls `PATCH /api/v1/bookings/:id/complete`.
  On success, status chip updates to "Completed" and a toast appears: "Booking
  marked as completed. Customer will be prompted to review."
- [ ] `MarkNoShowConfirmation` sheet: warns the slot is released and no review
  is sent. Tapping "Mark no-show" calls `PATCH /api/v1/bookings/:id/no-show`.
  Status chip updates to "No-show" (amber). Toast: "Marked as no-show. Slot
  released."
- [ ] Widget tests cover: complete button calls correct endpoint and updates chip,
  no-show button calls correct endpoint and updates chip, action buttons hidden
  for past-date bookings.

**Dependencies:** 13.1, 8.2
**Complexity:** L

---

## Epic 14: Notifications (Backend + Mobile)

This epic wires up all notification dispatch paths: booking confirmation,
cancellation, 24-hour reminder, partner new-booking alert, partner cancellation
alert, and post-visit rating prompt.

### Story 14.1: Notification dispatch service (Backend)

**As a** system, **I want** a centralized notification service that dispatches push
notifications and/or SMS asynchronously after booking events, **so that** all
notification triggers are handled consistently without coupling to the booking
transaction.

**Acceptance criteria:**
- [ ] A `NotificationService` in `src/services/notification.service.ts` encapsulates
  all notification dispatch logic. It is called from relevant services (booking,
  rating) as an asynchronous fire-and-forget after transaction `COMMIT`
  (base-rules.md §3.6). A notification failure is logged at WARN and never
  propagates to the API response.
- [ ] Booking confirmation notification dispatched to customer after
  `POST /api/v1/bookings` succeeds. Content: salon name, service name, date, time,
  booking reference (FR-C-BOOK-05).
- [ ] Cancellation notification dispatched to customer AND salon partner after
  `PATCH /api/v1/bookings/:id/cancel` (FR-C-MGT-03, FR-P-DASH-06).
- [ ] New booking notification dispatched to salon partner after
  `POST /api/v1/bookings` (FR-P-DASH-05).
- [ ] Reminder notification dispatched to customer 24 hours before
  `scheduled_start`. Implemented as a scheduled job (cron or queue-based);
  fires for all bookings with `status = confirmed` and `scheduled_start` within
  24–25 hours of the job's run time (configurable window) (FR-C-MGT-05).
- [ ] Rating prompt notification dispatched to customer after
  `PATCH /api/v1/bookings/:id/complete` (FR-C-RAT-01). Content: "How was your
  visit at {salon_name}? Share your feedback."
- [ ] The notification channel (FCM push / SMS / email) is configured via
  environment variable and can be swapped without changing service logic (Architect
  to confirm at-launch channel).
- [ ] Unit tests cover: each notification trigger invokes `NotificationService`
  with correct payload, notification failure does not propagate to caller.

**Dependencies:** 5.1, 6.1, 13.1
**Complexity:** L

---

### Story 14.2: Push notification deep-link handling (Flutter — both apps)

**As a** customer or partner, **I want** tapping a push notification to take me
directly to the relevant screen in the app, **so that** I don't have to navigate
manually after receiving an alert.

**Acceptance criteria:**
- [ ] Customer app handles the following notification payloads via FCM:
  - Booking confirmation → deep-link to `BookingDetail` for the `booking_id` in
    the payload.
  - Cancellation → deep-link to `BookingList` (upcoming tab).
  - 24-hour reminder → deep-link to `BookingDetail` for the `booking_id`.
  - Rating prompt → deep-link to `RatingSubmission` for the `booking_id`.
    If the booking is already rated, shows "You've already submitted a review."
- [ ] Partner app handles:
  - New booking → deep-link to `PartnerDashboard`, auto-scrolling to and briefly
    highlighting the new booking card (FR-P-DASH-05).
  - Customer cancellation → deep-link to `PartnerDashboard`, same highlight
    behaviour for the cancelled booking (FR-P-DASH-06).
- [ ] Deep-links work in all three app states: foreground (notification handled
  in-app), background (notification tapped from OS tray), and cold-start (app
  launched via notification tap).
- [ ] Unauthenticated cold-start via notification: app shows `AuthGate`; after
  successful auth, navigates to the target screen.
- [ ] `go_router` handles all deep-link routes; no raw Navigator calls are used
  for notification navigation (base-rules.md §2.3).
- [ ] Widget tests cover: foreground notification tap navigates to correct screen,
  cold-start notification tap after auth navigates to correct screen.

**Dependencies:** 14.1, 7.2, 13.2, 6.2
**Complexity:** M

---

## Dependency chain summary

The following chains represent the critical paths through the epics:

**Customer booking path (longest chain):**
1.1 → 1.2 → 2.1 → 2.2 → 5.1 (booking creation API)
1.3 → 2.3 → 3.3 → 3.4 → 3.5 (discovery + detail UI)
3.1 → 3.2 (discovery + detail API)
4.1 → 4.2 (slot engine + API)
All of the above converge at → 5.2 (slot picker UI) → 5.3 (confirmation UI)

**Partner operational chain:**
1.1 → 1.2 → 8.1 → 9.1 → 10.1 → 11.1 → 13.1
1.4 → 8.2 → 9.2 → 10.2 → 11.2 → 12.1 → 13.2

**Notification chain:**
5.1 + 6.1 + 13.1 → 14.1 → 14.2

**Rating chain:**
5.1 → 7.1 → 7.2 → 7.3
7.3 depends on 13.1 (mark-complete endpoint triggers the notification)

**Minimum viable first-deploy sequence (customer can browse and book):**
1.1 → 1.2 → 1.3 → 2.1 → 2.2 → 3.1 → 3.2 → 4.1 → 4.2 → 5.1
simultaneously: 2.3 → 3.3 → 3.4 → 3.5 → 5.2 → 5.3

**Minimum viable partner operational sequence:**
1.1 → 8.1 → 9.1 → 10.1 → 13.1
simultaneously: 1.4 → 8.2 → 9.2 → 10.2 → 13.2
