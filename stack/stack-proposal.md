---
title: Tech Stack Proposal — salon-app
status: approved
date: 2026-09-05
---

# Tech Stack Proposal — salon-app

Stack fixed by founder decision. Flutter (mobile) and Node.js (backend) are not open
for re-evaluation at MVP. AWS infrastructure decisions are deferred and will be recorded
in a separate infrastructure addendum once confirmed.

---

## 1. Mobile App (Customer + Salon Partner)

**Framework:** Flutter (Dart)
**State management:** BLoC (flutter_bloc package)

**Rationale:**
- Single codebase targets iOS and Android — appropriate for a small team shipping a two-sided MVP.
- Flutter's widget rendering is consistent across platforms; no platform-specific UI divergence for MVP.
- BLoC enforces a strict separation between UI, business logic, and data — testable in isolation, which matters for the slot booking flow.
- Dart is strongly typed; catches a class of runtime errors at compile time.

**Alternatives considered:**

| Alternative | Why not chosen |
|---|---|
| React Native | Requires JavaScript/TypeScript ecosystem; bridge overhead for real-time UI updates; team expertise not confirmed |
| Two native codebases (Swift + Kotlin) | Double implementation cost for every feature; not appropriate for small-team MVP |
| Expo (managed React Native) | Additional abstraction layer; ejection complexity when hitting native APIs (push notifications, geolocation) |

---

## 2. Backend

**Framework:** Node.js with Express (TypeScript)
**Architecture pattern:** Routes → Controllers → Service (layered, no microservices)

**Slot engine REST endpoints:**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/slots` | Returns available slots for a given `business_id`, `service_id`, and `date`. Computed on-demand from operating hours minus existing bookings. |
| `POST` | `/api/v1/bookings` | Creates a booking for a specific slot. |
| `DELETE` | `/api/v1/bookings/:id` | Cancels a booking. |
| `PATCH` | `/api/v1/bookings/:id/cancel` | Cancels a booking (preferred named action form). |

The slot computation logic lives entirely in `SlotService`, called by the booking controller. It is not a separate process and not pushed via WebSocket. Slot availability is request/response only.

**Rationale:**
- Node.js + Express is a proven, boring choice that any mid-level JavaScript/TypeScript developer can read and extend.
- TypeScript gives compile-time type safety across API contracts and data models.
- The Routes → Controllers → Service pattern enforces a clean separation of routing, HTTP handling, and business logic. The slot engine lives as a distinct Service module — satisfying the PRD constraint without requiring a separate process.
- The same pattern makes it straightforward to extract the slot engine into a separate service post-MVP if load warrants it.
- No framework magic; easy to debug, easy to test, easy to hand off.

**Alternatives considered:**

| Alternative | Why not chosen |
|---|---|
| NestJS | More structure than needed for MVP; decorator-heavy; increases onboarding time |
| Fastify | Good choice but marginal performance gain not a deciding factor at MVP scale |
| Python / Django or FastAPI | Team stack is Node; switching adds context cost |
| Go | Strong performance but typed differently from frontend Dart; team familiarity not confirmed |

---

## 3. Database

**Primary store:** PostgreSQL

**Rationale:**
- Relational model matches the data: Bookings reference Customers, Staff, Services, and Businesses with explicit foreign keys and constraints.
- `FOR UPDATE` row-level locking is the concurrency mechanism for no-double-booking (see Section 4 / Section 10).
- Strong ACID guarantees satisfy NFR-REL-02 (confirmed booking records are durable under single component failure).
- `geography` / `point` column type (via PostGIS extension) supports geolocation queries for salon discovery without an external spatial service.
- INR decimal precision is handled with `NUMERIC(10,2)` — no floating-point money bugs.
- Mature ecosystem; straightforward backup, restore, and point-in-time recovery on AWS RDS.

**Caching layer:** Redis

**Rationale:**
- Slot computation results for high-traffic salons can be cached in Redis with a short TTL (see Section 10 and Section 11).
- Pub/Sub channel on Redis supports real-time queue count broadcast (see Section 4). It is not used for slot availability sync — slots are fetched via REST.
- Session/token storage for auth tokens if needed.

**Alternatives considered:**

| Alternative | Why not chosen |
|---|---|
| MongoDB | Document model creates impedance mismatch with relational booking constraints; harder to enforce referential integrity |
| MySQL | Viable alternative; PostGIS support weaker; PostgreSQL preferred for spatial queries |
| Firestore / DynamoDB | Managed convenience, but complex query patterns for slot computation; concurrency control is more complex |
| SQLite | Not production-grade for multi-instance deployment |

---

## 4. Real-Time Layer

**Technology:** Redis Pub/Sub + WebSocket (via `ws` or `socket.io` on Node.js backend)

**Scope: queue position display only — not slot availability.**

Slot availability (which slots are open for booking) is **not** pushed via WebSocket. Clients fetch `GET /slots` on demand when they need availability. This is a request/response interaction with no subscription.

What the real-time layer IS used for:

- **Live queue position display** ("3 people ahead", "Busy now") — this changes frequently as customers check in and are served, and must reflect the current state without requiring a manual refresh. This remains WebSocket/Pub/Sub.

**How live queue sync works:**

1. When a booking is confirmed, cancelled, or a queue status change occurs, the backend publishes an event to a Redis channel keyed by `business_id`.
2. The Node.js API server maintains WebSocket connections to connected mobile clients. The mobile client subscribes to the relevant `business_id` channel when viewing a salon detail screen.
3. The server relays the anonymized aggregate update (queue depth, load category) to all subscribed clients for that salon.
4. The Flutter client updates its BLoC state on receipt, triggering a UI rebuild without a full page reload.

**Privacy:** The relay carries only anonymized aggregate counts — no individual booking data is ever broadcast to customers (NFR-PRIV-01, NFR-PRIV-02).

**Salon partner app:** Receives full booking events (new booking, cancellation) as push notifications (Section 6) and via WebSocket refresh of the dashboard BLoC.

**Redis Pub/Sub scope:** Redis Pub/Sub is justified for queue count broadcast. It is not used for slot availability sync — slot data is served by the REST API with a short-TTL cache (see Section 11). If the queue display feature is descoped, Redis Pub/Sub can be removed entirely; the caching use case alone would be served by Redis key-value only.

**Alternatives considered:**

| Alternative | Why not chosen |
|---|---|
| Polling (HTTP) for queue position | Wastes bandwidth and battery; queue updates would lag unacceptably |
| Server-Sent Events (SSE) | One-directional; acceptable for queue display but WebSocket gives bidirectional channel that can also handle booking confirmation acknowledgement |
| Polling (HTTP) for slot availability | Actually the correct approach — `GET /slots` on demand is exactly this. Slots are not pushed. |
| Firebase Realtime Database / Firestore | Adds a second database vendor dependency; Firebase SDK conflicts with clean BLoC data layer |
| AWS AppSync (GraphQL subscriptions) | Infrastructure not locked to AWS for real-time specifically; adds GraphQL complexity |

---

## 5. Authentication

**Customer app:** Phone number OTP (SMS) as primary method; email + password as secondary option.
**Salon Partner app:** Email + password.

**Technology:** Supabase Auth or a self-managed JWT flow backed by PostgreSQL.

- OTP flow: Generate a 6-digit code, store a hashed copy in PostgreSQL with a 10-minute TTL, deliver via SMS (Twilio or AWS SNS). On verification, issue a signed JWT (RS256). Code is invalidated on first use (NFR-SEC-03).
- Email/password flow: Password stored with bcrypt (cost factor 12) — never plaintext (NFR-SEC-02). On login, issue a signed JWT.
- JWT access token: short-lived (15 minutes). Refresh token: stored in PostgreSQL, rotated on use, revocable.
- Minimum TLS 1.2 on all endpoints; TLS 1.3 preferred (NFR-SEC-01).
- Salon partner access control enforced at the Service layer: every query scopes to the `business_id` extracted from the JWT claims (NFR-SEC-04).

**Alternatives considered:**

| Alternative | Why not chosen |
|---|---|
| Firebase Auth | Ties authentication to Google infrastructure; harder to migrate; SDK adds weight |
| Auth0 / Clerk | Managed convenience but adds per-MAU cost and a third-party data processor for PII (phone numbers) — requires review under Indian data protection obligations |
| Passwordless magic link only | SMS OTP is more familiar to the target Indian market than email magic links |

---

## 6. Notifications

**Push notifications:** Firebase Cloud Messaging (FCM) — covers both iOS (via APNs gateway) and Android natively.

**SMS:** AWS SNS or Twilio for OTP delivery and booking confirmation SMS to customers who may have notifications disabled.

**What triggers notifications:**

| Event | Recipient | Channel |
|---|---|---|
| Booking confirmed | Customer | Push + SMS |
| Booking reminder (configurable, default 24 h) | Customer | Push |
| Booking cancelled by customer | Salon partner | Push |
| New booking arrived | Salon partner | Push |
| Booking rescheduled | Customer + Salon partner | Push |

**Technology rationale:**
- FCM is the standard cross-platform push gateway; the Flutter `firebase_messaging` plugin is mature and well-maintained.
- SMS fallback for customers covers devices without push enabled and OTP delivery — a single SMS provider handles both.
- Notification dispatch is a fire-and-forget async job queued after the booking transaction commits — it does not sit on the critical booking path (NFR-PERF-03).

**Alternatives considered:**

| Alternative | Why not chosen |
|---|---|
| OneSignal | Aggregates FCM/APNs but adds a middleman with data access to device tokens and notification content |
| APNs direct (iOS only) | Platform-specific; Flutter app must be cross-platform |
| In-app polling for notifications | Battery-inefficient; not suitable for time-sensitive booking alerts |

---

## 7. Maps & Geolocation

**Technology:** Google Maps SDK for Flutter (`google_maps_flutter`) + Google Maps Platform APIs (Geocoding, Places).

**Device location:** Flutter `geolocator` package for device GPS (FR-C-LOC-01).

**Salon discovery spatial query:** PostGIS `ST_DWithin` query on the `businesses` table using a `geography` column for the salon's coordinates. No external map service is needed for the core discovery query — the database handles radius filtering. Distance sorting uses `ST_Distance`.

**Map display:** Google Maps SDK renders the map view in the customer app for location selection (FR-C-LOC-02). Salon pins may be displayed as a future enhancement; MVP discovery is list-first.

**Rationale:**
- Google Maps is the de-facto standard in India; users expect it.
- PostGIS spatial queries keep the discovery hot path inside the database, avoiding an extra service hop.
- `geolocator` is the standard Flutter geolocation plugin with permission handling built in.

**Alternatives considered:**

| Alternative | Why not chosen |
|---|---|
| Mapbox | Higher cost at scale; less familiar to Indian users |
| OpenStreetMap / Leaflet | No Flutter SDK parity; geocoding accuracy in India is weaker |
| External geospatial service (Elasticsearch geo) | Overkill for single-city MVP; PostGIS is sufficient |

---

## 8. Infrastructure & CI/CD

**Hosting:** AWS (specific services TBD — to be recorded in infrastructure addendum once confirmed by founder).

**Containerisation:** Docker for the Node.js API server. Each environment (dev, staging, production) runs the same image. No container orchestration at MVP — single-instance deploy is acceptable for launch; horizontal scaling added when load data warrants it.

**CI/CD:** GitHub Actions.
- On pull request: lint, unit tests, integration tests, build Docker image.
- On merge to `main`: deploy to staging automatically.
- On tagged release: deploy to production (manual approval gate).

**Minimum viable infrastructure (MVP):**
- Node.js API: containerised on AWS (ECS Fargate or EC2 — TBD).
- PostgreSQL: AWS RDS PostgreSQL (managed backups, point-in-time recovery — satisfies NFR-REL-02).
- Redis: AWS ElastiCache for Redis.
- Static assets / mobile app distribution: App Store + Google Play.

**Rationale:**
- Docker + GitHub Actions is the boring, well-understood CI/CD path for a Node.js monolith.
- AWS RDS gives managed backups without operational burden — critical for booking durability.
- Single-instance deploy avoids distributed state complexity at MVP; the slot engine's concurrency control (PostgreSQL row locking) works correctly on a single instance.

**Infrastructure addendum:** AWS-specific resource decisions (VPC layout, IAM, RDS instance class, ElastiCache node type, domain/SSL management) are deferred and must be recorded separately before the first production deploy.

---

## 9. Key Libraries & Services

| Layer | Library / Service | Purpose |
|---|---|---|
| Flutter | `flutter_bloc` | State management (BLoC pattern) |
| Flutter | `dio` | HTTP client for API calls |
| Flutter | `web_socket_channel` | WebSocket connection for real-time updates |
| Flutter | `firebase_messaging` | FCM push notifications |
| Flutter | `geolocator` | Device GPS / location permission |
| Flutter | `google_maps_flutter` | Map display and location picker |
| Flutter | `go_router` | Declarative navigation |
| Flutter | `freezed` + `json_serializable` | Immutable data models and JSON serialisation |
| Flutter | `get_it` | Service locator / dependency injection |
| Flutter | `flutter_secure_storage` | Secure JWT token storage on device |
| Node.js | `express` | HTTP framework |
| Node.js | `typescript` | Static typing |
| Node.js | `pg` / `kysely` | PostgreSQL client / query builder (type-safe, no full ORM magic) |
| Node.js | `ioredis` | Redis client (Pub/Sub + caching) |
| Node.js | `ws` or `socket.io` | WebSocket server |
| Node.js | `jsonwebtoken` | JWT sign / verify |
| Node.js | `bcrypt` | Password hashing |
| Node.js | `zod` | Request validation and schema parsing at the Controller layer |
| Node.js | `vitest` | Unit and integration testing |
| Node.js | `supertest` | HTTP integration test client |
| External | Firebase Cloud Messaging | Push notification gateway (iOS + Android) |
| External | Twilio or AWS SNS | SMS delivery (OTP + booking confirmations) |
| External | Google Maps Platform | Geocoding, Places autocomplete |
| Infrastructure | AWS RDS PostgreSQL | Primary database with managed backups |
| Infrastructure | AWS ElastiCache Redis | Caching + Pub/Sub |
| Infrastructure | GitHub Actions | CI/CD pipeline |

---

## 10. Architecture Constraints

### What this stack rules out for the future

- **GraphQL at MVP:** REST is chosen; switching to GraphQL requires schema design and client codegen changes across both apps. Not ruled out post-MVP but it is a deliberate change, not a natural extension.
- **Serverless functions for the slot engine:** The slot engine is a Service module within the monolith. Extracting it to a Lambda/serverless function is possible post-MVP but the cold-start latency (NFR-PERF-02: 2 s for slot results) must be validated before moving.
- **Multiple database vendors:** PostgreSQL is the single source of truth. Introducing a second database technology requires Architect sign-off and a new ADR.
- **In-app payments:** Explicitly out of scope. No payment SDK may be added to either app without a separate architecture review and PCI scope assessment.

### Required patterns

- **Routes → Controllers → Service** in all Node.js code. No business logic in route handlers. No database queries in Controllers. The slot engine is a Service (or sub-module of a Service), not a utility function scattered across Controllers.
- **BLoC for all state in Flutter.** No `setState` outside of trivial widget-local ephemeral state (e.g., a text field focus). All data fetched from the API flows through a Cubit or Bloc.
- **Zod validation at the Controller boundary.** All incoming request bodies and query parameters are parsed through a Zod schema before reaching the Service layer. Invalid requests are rejected at the Controller with a 400 before any business logic runs.
- **No raw SQL outside the repository/data layer.** Queries are encapsulated in repository functions (the data-access portion of the Service layer). Controllers and Blocs never construct SQL.
- **Slot availability is computed and returned synchronously via REST API. No WebSocket or SSE for slot data.** The client calls `GET /slots` when it needs availability. There is no slot subscription and no slot push.
- **Booking endpoints (`POST /bookings`, `PATCH /bookings/:id/cancel`) must be idempotent and use row-level locking to prevent double-booking.** The booking creation transaction must use `SELECT ... FOR UPDATE` on the relevant time window (FR-C-BOOK-07, NFR-REL-01). Optimistic locking alone is not sufficient given the concurrent booking requirement.
- **Async notification dispatch.** Notification sends (FCM, SMS) must happen outside the booking database transaction. Enqueue or fire-and-forget after `COMMIT` to prevent a notification failure from rolling back a confirmed booking.

### Forbidden patterns

- Business logic in Express route handlers.
- Direct database access from Flutter BLoC or Cubit classes (all data via repository/API).
- Plaintext secrets in source code or committed `.env` files — use environment variables and AWS Secrets Manager for production.
- `any` type in TypeScript application code (lint rule enforced).
- Mutable global state on the Node.js server process.

---

## 11. Open Questions for the Architect (deferred from PRD)

**Staff assignment to bookings (PRD §10)**
Decision: For MVP, bookings are assigned to a staff member at the time of booking only if the customer can select a staff preference. If staff selection is not exposed in the MVP UI, the system assigns the first available qualified staff member at slot confirmation time using the slot engine. The `staff_id` on the Booking record is populated at booking creation — not deferred to service time. This means the slot engine must compute availability per-staff (not per-salon aggregate) to prevent double-booking a specific staff member.

- Implication: the slot query is `SELECT slots WHERE staff_id = ? AND no existing confirmed booking overlaps the window` — per-staff, not per-salon.
- Open for UX designer: does the customer-facing booking screen show staff selection, or is staff assigned silently?

**Concurrency control for no-double-booking (PRD §10, NFR-REL-01)**
Mechanism: Serializable transaction with `SELECT ... FOR UPDATE` on the `bookings` table rows for the target `(staff_id, scheduled_start, scheduled_end)` range. Only one transaction can hold the lock; the second sees a conflict and returns an error to the client (FR-C-BOOK-07). This is correct on a single database instance (MVP) and on RDS with a single writer.

- Post-MVP risk: If a read replica or multi-writer setup is introduced, this mechanism must be revisited.

**Slot computation caching strategy (PRD §10)**
Strategy: `GET /slots` is the only way clients receive slot availability — there is no push path. The endpoint computes slots on demand. Results are cached in Redis with a 30-second TTL keyed by `(business_id, service_id, date)` using a cache-aside pattern: on a cache miss, `SlotService` computes from the database and writes to cache; on a hit, the cached result is returned directly. On any booking creation, cancellation, or staff-hours change for that business, the relevant Redis cache keys are invalidated immediately (write-through invalidation triggered by the booking or scheduling service after `COMMIT`). This is a cache invalidation problem on a REST endpoint — not a push invalidation problem. Cache staleness is bounded to 30 seconds at most (TTL expiry), but proactive invalidation keeps it much lower in practice. This satisfies NFR-PERF-02 (2 s slot response) for the common read case.
