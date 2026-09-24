# Implementation Plan: Dashboard bookings list — view-aware empty state

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `SIM-1` (SIMULATED — Jira not connected; source: `.orchestration/runs/SIM-1/simulated-jira-ticket.md`) |
| Summary | Dashboard bookings list: view-aware empty state |
| Type | `Story` |
| Component / Classification | Frontend — `B2B_FE/` only |
| Priority | Low |
| Branch | `feature/SIM-1-dashboard-bookings-list-view-aware-empty` (base: `develop`) |
| Assigned to | `samson paul` |

---

## Overview

The Owner Dashboard Bookings list (`B2B_FE/src/dashboard/BookingsList.tsx`) renders the same
hard-coded `No bookings` text (line 83) whenever the grouped bookings map is empty, regardless of
whether the `today` or `week` view is selected. This change makes that empty-state message depend on
the current `view` state: `"No bookings today"` for `today` (AC1) and `"No bookings this week"` for
`week` (AC2). The non-empty branch (grouped staff cards) is not touched (AC3), and no API client,
type, or backend file changes (AC4).

---

## Business Context

From the ticket description: *"On the Owner Dashboard, the Bookings list shows the same generic text
'No bookings' whether the owner is looking at Today or This Week. The owner cannot tell from the
message which period is empty."*

Acceptance criteria:
1. With the "Today" view selected and no bookings returned, the list shows "No bookings today".
2. With the "This Week" view selected and no bookings returned, the list shows "No bookings this week".
3. When bookings exist, rendering is unchanged (grouped staff cards as today).
4. No backend/API change; change is confined to B2B_FE/.

User-facing outcome: the owner can tell at a glance which period (today vs. this week) has no
bookings.

---

## Technical Context

- Stack: React 19 + TypeScript + Vite + Tailwind (`B2B_FE/package.json`; `stack/rules/base-rules.md`
  §3.9 layout — `src/dashboard/` is the Owner Dashboard module).
- `BookingsList` already holds `view: DashboardView` in state (line 31). `DashboardView` is the union
  `"today" | "week"` exported from `B2B_FE/src/api/dashboardBookings.ts`.
- Approach: add a module-level constant typed `Record<DashboardView, string>` mapping each view to its
  empty-state message, and render `EMPTY_STATE_MESSAGE[view]` in place of the literal `No bookings`.
  Typing it as `Record<DashboardView, string>` makes the mapping exhaustive at compile time — if a new
  view is ever added to the union, `tsc -b` fails until a message is supplied. Existing element,
  classes (`mt-6 text-sm text-ink-muted`) and conditional structure are kept identical.
- No i18n layer exists in `B2B_FE/`; strings are inline literals elsewhere in the component, so an
  inline constant matches existing convention.
- Only the presentation layer of one component changes. `src/api/dashboardBookings.ts` is imported
  for its type only and is not modified.
- `stack/rules/client-rules.md` has no recorded client requirements/overrides affecting this change.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_FE/src/dashboard/BookingsList.tsx` (verified exists) | `Modify` | Replace hard-coded empty-state text with a view-keyed message (AC1, AC2). |
| `B2B_FE/src/api/dashboardBookings.ts` (verified exists) | None (read / type import only) | Source of `DashboardView`; already imported by `BookingsList.tsx`. |

---

## Tasks

### Task 1: Render a view-aware empty-state message in BookingsList

**Description:** In `BookingsList.tsx`, add a top-level constant
`const EMPTY_STATE_MESSAGE: Record<DashboardView, string> = { today: "No bookings today", week: "No bookings this week" };`
and change the empty branch (currently line 83, `<p className="mt-6 text-sm text-ink-muted">No bookings</p>`)
to render `{EMPTY_STATE_MESSAGE[view]}`. Do not alter the non-empty branch, the toggle buttons, the
fetch effect, or the grouping helper.

**Files to modify:**
- `B2B_FE/src/dashboard/BookingsList.tsx`

**New files to create:** None.

**Dependencies:** `None`

**Complexity:** `Low`

**Testing requirements:**
(Unit tests are authored later in `sdlc-unit-test-workflow`, not in Phase 4. Listed here so that
workflow has concrete targets; framework is Vitest + React Testing Library per base-rules.md
*Testing Requirements*, already configured in `B2B_FE/vite.config.ts` with jsdom and
`tests/setup.ts`.)
- Today view, fetch resolves `[]` → text "No bookings today" is shown (AC1).
- Click "This Week", fetch resolves `[]` → text "No bookings this week" is shown (AC2).
- Fetch resolves one or more bookings → staff-name cards render and neither empty message is present (AC3).
- Suggested file: `B2B_FE/tests/BookingsList.test.tsx` (new, created by the unit-test workflow; mock
  `fetchDashboardBookings` or global `fetch`).
- Phase 4 validation for this task: `npm run lint`, `npm run build`, `npm run format:check`, and
  `npm test` (existing suite must stay green) from `B2B_FE/`, plus `tools/scope-check/` against the diff.

**Documentation updates:** None required. (See Findings: the UX doc's "No bookings" wording for
per-cell empty state is not contradicted, since this ticket governs the whole-list empty state.)

---

## External Dependencies

None. The existing `GET /dashboard/bookings?view=today|week` endpoint and its response shape are used
unchanged. No env vars, feature flags, or other teams' work are required.

---

## Testing Strategy

| Test Type | Scope | Tooling |
|---|---|---|
| Unit / component | `BookingsList` empty state per view (AC1, AC2) and non-empty rendering unchanged (AC3) — authored in `sdlc-unit-test-workflow` | Vitest + React Testing Library (jsdom) — `npm test` → `vitest run` |
| Static | Type exhaustiveness of the message map, lint, formatting | `npm run build` (`tsc -b && vite build`), `npm run lint` (`eslint .`), `npm run format:check` (`prettier --check .`) |
| Integration | Owner Dashboard against the real API shows the correct message per view — covered in `sdlc-qa-workflow` | Manual / QA plan |

Minimum coverage expectation: base-rules.md mandates no numeric coverage threshold and scopes the
build as happy-flow-only; the three scenarios above (one per AC1–AC3) are the expected minimum.

Validation commands (source: `B2B_FE/package.json` `scripts`), run from `B2B_FE/`:
- `npm run lint`
- `npm run build`
- `npm test`
- `npm run format:check`

---

## Security Considerations

None. Static, non-user-derived strings rendered via JSX (auto-escaped). No auth, input, or data
handling changes.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Accidental change to the non-empty rendering branch (AC3) | `Low` | `Med` | Edit is confined to the single `<p>` text node; diff review checks no other lines in the JSX change. |
| Existing tests asserting the literal "No bookings" break | `Low` | `Low` | Verified: `grep` over `B2B_FE/src` and `B2B_FE/tests` finds "No bookings" only at `BookingsList.tsx:83`; no test references it. |
| Brief stale message while switching views (view state updates before the new fetch resolves, so previous view's data shows with the new view's label) | `Low` | `Low` | Pre-existing behaviour, not introduced here; recorded as a finding, out of scope. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 | `Low` |
| **Overall** | `Low` |

---

## Out of Scope

- **Error-state handling for a failed fetch.** Observed, unfixed finding: `fetchDashboardBookings`
  rejections are only `console.error`-ed (`BookingsList.tsx` lines 38–40). On an initial-load failure
  `bookings` stays `[]`, so the UI falls through to the empty state and will now say "No bookings
  today" even though the request failed. On a failure after switching views, the previous view's
  bookings remain displayed. Neither is addressed here.
- **Stale / out-of-order responses on rapid view toggling.** The effect has no abort/ignore guard, so
  a slower earlier response can overwrite a later one. Observed, not fixed.
- **Loading state.** No loading indicator exists; the empty message may flash before data arrives.
  Not addressed.
- The UX doc's Week-view table layout and per-day/per-staff cell empty states
  (`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/owner-dashboard.md` lines 54–59) and
  the same-day booking count (line 48) — current implementation uses grouped cards; not changed.
- Any change to `B2B_FE/src/api/dashboardBookings.ts`, any backend (`B2B_BE/`) code, or the API
  contract (AC4).
- Writing unit tests (deferred to `sdlc-unit-test-workflow`).
- i18n / string externalisation.

---

*Generated by sdlc-dev-workflow · Ticket: `SIM-1` · Branch: `feature/SIM-1-dashboard-bookings-list-view-aware-empty`*
