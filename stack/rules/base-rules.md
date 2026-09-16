---
title: Base Coding Rules — salon-app
status: approved
stack-ref: stack/stack-proposal.md
date: 2026-09-05
---

# Base Coding Rules — salon-app

These rules are derived from the approved stack (Flutter + BLoC / Node.js
Routes → Controllers → Service). Every agent that writes or reviews code in this
repository must treat these as invariants. Client rules in `client-rules.md` layer
on top and win on conflict.

---

## 1. Global Rules (all code)

| Rule | Detail |
|---|---|
| Language | Flutter: Dart. Backend: TypeScript (strict mode, `"strict": true` in tsconfig). |
| Secrets | No secrets, API keys, or credentials in source files. Use environment variables. Use AWS Secrets Manager in production. |
| TLS | All client-server communication over TLS 1.2 minimum; TLS 1.3 preferred. |
| Date/time | All timestamps stored and transmitted in UTC ISO 8601. Display conversion to local time happens in the Flutter presentation layer only. |
| Currency | All monetary values stored as `NUMERIC(10,2)` in PostgreSQL and transmitted as a numeric JSON value in INR. No floating-point money arithmetic. |
| Logging | Log at INFO for normal operations, WARN for recoverable issues, ERROR for failures. Never log PII (customer name, phone, email) at any level in production. |
| No unused code | Dead code, commented-out blocks, and TODO stubs must not be committed unless the TODO is linked to a tracked issue. |

---

## 2. Flutter / Dart Rules

### 2.1 BLoC State Management

- **All application state goes through BLoC or Cubit.** No `setState` for data that originates from the API or that is shared between widgets. `setState` is permitted only for widget-local ephemeral state (e.g., a text field's `FocusNode`).
- **One BLoC/Cubit per feature screen or logical domain.** Do not create a single global BLoC for the whole app.
- **Events are the only way to trigger state changes in a Bloc.** A Bloc must not expose public methods other than `add(event)`. Use Cubit when the state machine is simple and events add no value.
- **States are immutable.** Use `freezed` for all BLoC state and event classes. No mutable fields on state objects.
- **BLoC classes must not import any Flutter widget.** BLoC lives in the domain/business layer — it must be testable without Flutter.
- **No direct API calls from a BLoC.** BLoC calls a Repository abstraction. The Repository calls the API client (e.g., `dio`). BLoC does not know about HTTP.

### 2.2 Layered Architecture (Flutter)

```
Presentation layer   — Widgets, Pages, Dialogs
      |
BLoC / Cubit layer   — State machines, events, states (no Flutter import)
      |
Repository layer     — Abstracts data source; calls API client or local cache
      |
API client layer     — dio HTTP client, WebSocket channel
```

- No widget may directly call a repository or API client — all calls go through BLoC.
- No repository may contain UI logic.

### 2.3 Navigation

- Use `go_router` for all navigation. No `Navigator.push` with anonymous routes.
- Route paths are defined in a single `AppRouter` class. No hard-coded route strings outside that class.

### 2.4 Models and Serialisation

- All data transfer objects (API request/response shapes) use `freezed` + `json_serializable`.
- No `dynamic` or raw `Map<String, dynamic>` in BLoC or widget code. Deserialise at the repository boundary.

### 2.5 Dependency Injection

- Use `get_it` as the service locator. Register all singletons and factories in a dedicated `injection_container.dart` (or equivalent) file.
- No `InheritedWidget`-based DI for services that are not UI-related.

### 2.6 Secure Storage

- JWT access tokens and refresh tokens are stored with `flutter_secure_storage`. Never in `SharedPreferences` or local files.

### 2.7 Error Handling

- Repository methods return a `Result<T, Failure>` type (or equivalent sealed class) — they do not throw. BLoC catches errors from the repository via the result type and emits a typed error state.
- The UI layer reads error states and displays user-facing messages. Raw exception messages must not be shown to users.

### 2.8 Dart Style

- Follow `dart format` (enforced by CI). No manual formatting overrides.
- No `dynamic` type annotations in business logic. Prefer explicit types.
- No `print()` in committed code — use a logger.
- File naming: `snake_case.dart`. Class naming: `PascalCase`. Constants: `camelCase` (Dart convention).

---

## 3. Node.js / TypeScript Rules

### 3.1 Layered Architecture (Backend)

```
Routes       — Express router definitions only. No logic. Maps HTTP verbs + paths to Controller methods.
     |
Controllers  — Parse and validate the request (Zod). Call one or more Service methods. Format the HTTP response.
     |
Services     — All business logic lives here. Orchestrate data access and enforce domain rules.
     |
Repositories — All database queries live here. Services call repositories; controllers do not.
     |
PostgreSQL / Redis
```

Rules derived from this pattern:

- **Routes contain zero business logic.** A route file imports a controller and wires a path to a method — nothing else.
- **Controllers contain zero business logic and zero SQL.** Controllers validate input with Zod, call service methods, and return HTTP responses. If a controller file grows beyond ~60 lines it is a signal that logic has leaked in.
- **Services contain all domain rules.** Services call repositories for data. Services do not import `express`, `Request`, or `Response`.
- **Repositories contain all SQL / database interaction.** No raw SQL outside a repository file. Services never call `db.query(...)` directly.
- **The slot engine is a Service module** (`SlotService` or `SchedulingService`). It is not a utility function spread across controllers. It must be independently unit-testable.

### 3.2 TypeScript

- `"strict": true` in `tsconfig.json`. No exceptions.
- No `any` type in application code. Use `unknown` and narrow explicitly. ESLint rule `@typescript-eslint/no-explicit-any: error` is enforced.
- All exported functions have explicit return type annotations.
- Prefer `interface` for object shapes that are extended; `type` for unions and intersections.

### 3.3 Request Validation

- Every endpoint that accepts a request body or query parameters must parse through a `zod` schema at the top of the Controller method.
- If validation fails, the Controller returns `400 Bad Request` with a structured error body before any Service call.
- Validated and typed values are passed to Service methods — Services do not validate input again.

### 3.4 Database Access

- Use `kysely` as the query builder. No raw template-literal SQL in application code.
- All queries are in repository files located at `src/repositories/`.
- Database transactions use `db.transaction()`. The booking creation flow (slot check + insert) must run inside a single transaction with `SELECT ... FOR UPDATE` on the conflicting row range.
- Connection pooling is managed by `pg` pool — do not open a new connection per request.

### 3.5 Concurrency and Booking Integrity

- Booking creation: acquire a row-level lock with `SELECT ... FOR UPDATE SKIP LOCKED` (or equivalent serialisable isolation) before inserting a booking. If a conflicting booking is found inside the transaction, roll back and return a `409 Conflict` response. The Controller maps this to the user-facing "slot no longer available" message.
- Never rely on application-level checks alone (read then write) for double-booking prevention.

### 3.6 Real-Time Events

- **Slot availability must be fetched via `GET /slots` — never pushed.** Clients must not maintain subscriptions for slot state. The slot engine is REST-only; there is no WebSocket or SSE channel for slot data.
- After a booking transaction `COMMIT`s, two things happen (both outside the transaction):
  1. Publish an event to the Redis Pub/Sub channel `salon:{business_id}` — the WebSocket relay fans out anonymized queue aggregate updates (queue depth, load category) to connected customers.
  2. Invalidate the Redis slot cache keys for `(business_id, service_id, date)` affected by the booking, so the next `GET /slots` call sees fresh data.
- Notification dispatch (FCM, SMS) happens after `COMMIT`, outside the transaction, as an async fire-and-forget. A failure to send a notification must not roll back or fail the booking response.
- **Booking mutations (`POST /bookings`, `PATCH .../cancel`) must use `SELECT ... FOR UPDATE` within a transaction** to prevent double-booking. Never rely on application-level read-then-write checks alone.

### 3.7 Authentication and Authorisation

- All protected routes use a JWT middleware that verifies the token (RS256) and attaches the decoded claims to `req.user`.
- Salon partner routes additionally enforce that `req.user.businessId === resource.businessId`. This check happens in the Service layer — not just in middleware.
- OTP codes: stored as a bcrypt hash in the database with a 10-minute expiry. Invalidated on first successful use.

### 3.8 Error Handling

- Use a central Express error-handling middleware (`src/middleware/errorHandler.ts`). All unhandled errors flow through it.
- Service methods throw typed `AppError` subclasses (`NotFoundError`, `ConflictError`, `ValidationError`, etc.). The error handler maps these to the appropriate HTTP status codes.
- Never expose internal error messages, stack traces, or database errors to the client in production.

### 3.9 File and Folder Structure

```
src/
  routes/          — Express routers
  controllers/     — Request/response handling + Zod validation
  services/        — Business logic (including SlotService)
  repositories/    — All database queries
  middleware/      — Auth, error handling, logging
  lib/             — Shared utilities (db client, redis client, logger)
  types/           — Shared TypeScript types and interfaces
```

- Feature grouping within each layer is by domain (e.g., `services/booking.service.ts`, `services/slot.service.ts`).
- No barrel `index.ts` files that re-export everything — import explicitly.

### 3.10 Testing

- Unit tests cover all Service and Repository methods. Test file co-located: `booking.service.test.ts` beside `booking.service.ts`.
- Integration tests (using `supertest`) cover the full Routes → Controllers → Services → Database path for critical flows: booking creation, slot query, auth.
- `vitest` is the test runner. `npm test` runs all unit and integration tests.
- The slot engine (`SlotService`) must have unit tests covering: available slots returned correctly, slots blocked when overlapping bookings exist, edge cases at operating hour boundaries.

### 3.11 TypeScript / Node.js Style

- `camelCase` for variables and functions. `PascalCase` for classes and interfaces. `SCREAMING_SNAKE_CASE` for true constants.
- No `console.log` in committed code — use the project logger (`src/lib/logger.ts`).
- `async/await` over raw `Promise.then` chains.
- No `require()` — ES module imports only (`import`/`export`).

---

## 4. API Contract Rules

- All API responses use a consistent envelope:
  ```json
  { "data": <payload>, "error": null }
  { "data": null, "error": { "code": "SLOT_CONFLICT", "message": "..." } }
  ```
- HTTP status codes must be semantically correct: `200` success, `201` created, `400` validation error, `401` unauthenticated, `403` forbidden, `404` not found, `409` conflict (double-booking), `500` unexpected server error.
- All route paths are `kebab-case` (e.g., `/api/v1/salon-partners`, `/api/v1/bookings/:id/cancel`).
- API versioning: prefix all routes with `/api/v1/`. Breaking changes require a new version prefix.
- Pagination: list endpoints return `{ data: [], meta: { total, page, pageSize } }`. No unbounded list responses.

---

## 5. CI Enforcement

The following checks run on every pull request and must pass before merge:

| Check | Tool |
|---|---|
| Flutter format | `dart format --output=none --set-exit-if-changed .` |
| Flutter analyse | `flutter analyze` |
| Flutter tests | `flutter test` |
| TypeScript compile | `tsc --noEmit` |
| ESLint | `eslint src/ --max-warnings 0` |
| Backend tests | `npm test` |
| Docker build | `docker build .` (verify image builds) |

No warnings promoted to errors may be suppressed inline without a comment explaining the exception.
