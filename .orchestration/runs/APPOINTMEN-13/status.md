# APPOINTMEN-13 — status

Summary: 1.1 Shared data store entities exist
Branch:  feature/APPOINTMEN-13-shared-data-store-entities (deleted from remote post-merge; rebuilt twice on develop's tip after moving-target conflicts — see Issues & Blockers)
PR:      https://github.com/cache-mee/PRISMArc/pull/21 — MERGED into develop (88005d6)

## You Are Here
Workflow: sdlc-dev-workflow
Phase:    Complete
Waiting:  n/a
Next:     none — ticket complete

## Phase Tracker

### sdlc-dev-workflow
[✓] Phase 1 — Ticket Intake
[✓] Phase 2 — Branch Setup
[✓] Phase 3 — Implementation Plan
[✓] Gate 3 — Plan Review
[✓] Phase 4 — Code Implementation (trimmed retrofit — see Issues & Blockers)
[✓] Phase 5 — Pull Request (PR #21 merged)
[-] Phase 6 — Code Review (skipped, explicit user override)

## Artefacts
Implementation plan   development/plans/APPOINTMEN-13-implementation-plan.md   [describes original from-scratch design; actual delivered scope is the trimmed retrofit below]

## Commits (current branch tip, final trimmed retrofit on develop)
e5f8360   Fix pre-existing staff-table migration bugs on a fresh database
10d8720   APPOINTMEN-13: Add Salon entity (AC1)
2aeef36   APPOINTMEN-13: Add role-filtered staff queries (AC3)
a2b4993   APPOINTMEN-13: Link Bookings to Service via service_id FK (AC4)

## Jira Transitions
Start Dev        →   In Development   [done]
Ready for Review →   In Review        [done]
Ready for QA     →   In QA            [done]
QA Done          →   QA Done          [done]
QA Done          →   Ready for UAT    [done, explicit user override — no QA actually ran]

## Issues & Blockers (resolved, kept for audit trail)
- develop advanced significantly while this ticket was in flight; other tickets (14/15/17/18/19/22/26/33)
  independently built overlapping Staff/Customer/Service/Booking/Availability entities without waiting for
  this foundational story.
- Two full retrofit attempts were made. Attempt 1 (5 entities: Salon+Staff link, Service salon_id+duration,
  Availability, Bookings.service_id, full repo layer) was overtaken mid-flight when APPOINTMEN-33 merged its
  own independent Availability entity.
- Re-diffed current develop against all 5 acceptance criteria directly (not assumptions): AC2, AC5, and
  Availability (AC4) were already satisfied by other merged tickets. Only 3 real gaps remained: AC1 (Salon
  missing entirely), AC3 (no role-filtering existed anywhere in the codebase), and part of AC4
  (Booking.service_name was still a plain string, not a service_id FK).
- Final retrofit (attempt 2) delivers exactly those 3 gaps, nothing more — minimizing further conflict
  surface on tables other tickets depend on.
- Three unrelated pre-existing bugs found and fixed along the way (none previously exercised against a
  truly fresh database): staff_role enum double-create, a String/enum type mismatch in the seed migration,
  and a values_callable gap in the Staff model itself that silently broke any future role-based query.

## How to Resume
Ticket complete — nothing to resume. PR #21 merged into develop (88005d6); feature branch deleted from
remote post-merge; Jira at Ready for UAT.
