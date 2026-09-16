---
title: Client & Project-Specific Rules — salon-app
owner: CacheMe
updated: 2026-09-05
---

# Client & Project-Specific Rules

> This file is yours. Agents read it but never overwrite it.
> Add rules here that come from your client, organisation, or personal preferences.
> These rules are applied on top of stack/rules/base-rules.md — they do not replace it.

---

## Confirmed Stack Decisions (founder-fixed, not re-derivable)

- **Mobile:** Flutter (Dart) — cross-platform, iOS and Android.
- **State management:** BLoC (`flutter_bloc`). No alternative state management libraries.
- **Backend:** Node.js + TypeScript, Express framework.
- **Backend architecture pattern:** Routes → Controllers → Service. This is the enforced layer order. See `base-rules.md §3.1` for full detail.
- **Slot engine is API-driven (REST). No real-time slot subscription.** The client fetches slots on demand via `GET /slots`. There is no WebSocket or SSE channel for slot availability. Clients must not attempt to subscribe to slot state.
- **Infrastructure:** AWS. Specific resource decisions (ECS, RDS instance class, ElastiCache config) are deferred to the infrastructure addendum.

---

## Client Requirements

- All prices are displayed and stored in INR only. No currency formatting other than `₹` prefix with two decimal places.
- Queue indicators shown to customers must be anonymized aggregates only (e.g., "3 people ahead", "Busy"). No individual customer data visible to other customers at any point.
- The slot engine must live as a distinct Service module (`SlotService`) — not embedded in a Controller or a utility helper. It must be independently unit-testable.
- No in-app payment SDK may be added to either app without explicit founder approval and a new architecture review.
- Booking records, once confirmed to the customer, must be durable. A notification delivery failure must never cause a booking to be rolled back.

---

## Organisation Conventions

- All route paths use `kebab-case`.
- All date/time values are stored and transmitted in UTC ISO 8601. Local time display is handled in the Flutter presentation layer only.
- Environment-specific configuration is via environment variables. No config files with environment-switching logic committed to source.
- Feature branches named: `feature/<short-description>`. Fix branches: `fix/<short-description>`.
- Pull requests require at least one reviewer approval before merge to `main`.

---

## Preferences

- Favour boring, proven libraries over clever or experimental ones. If two options are otherwise equal, choose the one with more downloads and a longer maintenance history.
- Keep Controllers thin (~60 lines max). If a controller is growing, business logic has leaked in — move it to the Service layer.
- Keep BLoC/Cubit files focused on one screen or one logical domain. A file growing beyond ~150 lines is a signal to split.
- Avoid over-abstraction. Three similar lines of code are preferable to a premature generic utility.
- Prefer composition over inheritance in both Dart and TypeScript.

---

## Overrides to Base Rules

None at this time. Base rules are applied as written.

<!-- If a base rule needs to be overridden, document it here with a reason:
  Example:
  - "Override: eslint max-warnings 0 relaxed to 5 for the repositories layer during initial scaffolding sprint — reason: generated kysely types produce unavoidable warnings until query types are narrowed. Target: zero warnings before Sprint 2."
-->
