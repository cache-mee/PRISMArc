# Project Workflow Status

> This file is the single source of truth for where the project stands across all SDLC workflows.
> Every workflow updates its relevant section on each phase completion.
> Read this first when resuming any work after a break.

---

## Planning Phase (sdlc-planning-workflow)

| Phase | Status | Artefact | Gate |
|---|---|---|---|
| 1 — Discovery & Brief | `done` | bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/brief.md | Brief Approval — approved |
| 2 — PRD | `done` | bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md (final) | (inline) — approved |
| 3 — Tech Stack | `done` | stack/stack-proposal.md; locked: stack/rules/base-rules.md, client-rules.md | Stack Approval — approved |
| 4 — UX Design | `done` | bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/{customer-booking-chat,staff-owner-manager-chat,owner-dashboard,whatsapp-deltas}.md | Design Approval — approved |
| 5 — Epics & Stories | `done` | bmad-output/planning-artifacts/epics/epics-salon-app-2026-09-17.md (8 epics, 44 stories) | — |
| 6 — Confluence Push | `done` | 8 pages in space AP: https://experionglobal.atlassian.net/wiki/spaces/AP | Push Summary — done |
| 7 — Jira Push | `done` | APPOINTMEN-1..52 (8 epics, 44 stories): https://experionglobal.atlassian.net/jira/software/projects/APPOINTMEN/boards | Push Summary — done |

**Planning status:** `complete`
**Last updated by:** sdlc-planning-workflow — see `.orchestration/runs/planning-salon-app/run-record.md`
**Resume command:** `/sdlc-dev-workflow` (planning is done; pick the next ticket from the Jira board above)

---

## Active Tickets

> One row per ticket currently in progress. Updated by sdlc-dev-workflow, sdlc-unit-test-workflow, and sdlc-qa-workflow.

| Ticket | Summary | Branch | Current Workflow | Phase | Waiting On | Status File |
|---|---|---|---|---|---|---|
| APPOINTMEN-14 | LLM provider integration via litellm (generic AI-provider handler) — Jira key reused ad hoc; actual ticket text unrelated & already Ready for UAT under a different branch | feature/APPOINTMEN-14-llm-provider-integration | sdlc-dev-workflow | Gate 3 — Plan Review | user reply: implement / revise: <notes> / stop | `.orchestration/runs/APPOINTMEN-14/status.md` |
| APPOINTMEN-16 | 1.4 FR-14: Web Chat Owner/Admin identity resolution | feature/APPOINTMEN-16-owner-admin-identity-resolution | sdlc-dev-workflow | Phase 6 — Code Review | new session: /sdlc-dev-workflow review APPOINTMEN-16 | `.orchestration/runs/APPOINTMEN-16/status.md` |
| APPOINTMEN-20 | 2.3 FR-13: Staff preference limited to bookable staff | feature/APPOINTMEN-20-23-fr-13-staff-preference-limited-to | sdlc-dev-workflow | Phase 3 — Implementation Plan | — | `.orchestration/runs/APPOINTMEN-20/status.md` |

> Note: the Planning Phase table above was synced from `.orchestration/runs/planning-salon-app/run-record.md`
> (the authoritative planning run record) on 2026-09-17. `sdlc-planning-workflow` does not update this
> table automatically — re-sync it by hand if the planning run record changes again.

---

## Completed Tickets

| Ticket | Summary | Branch | PR | QA Verdict | Completed |
|---|---|---|---|---|---|
| APPOINTMEN-9 | 0.1 Backend project scaffolding | feature/APPOINTMEN-9-01-backend-project-scaffolding | [#12](https://github.com/cache-mee/PRISMArc/pull/12) — MERGED into develop (ee1722b) | PASS (1/1 passed, 1 skipped — Docker build/network check not validated, Docker unavailable) | 2026-09-17 |
| APPOINTMEN-10 | 0.2 Frontend project scaffolding | feature/APPOINTMEN-10-02-frontend-project-scaffolding | [#13](https://github.com/cache-mee/PRISMArc/pull/13) — MERGED into develop (a356f67) | PASS (17/19, 2 not validated — Docker build unverified) | 2026-09-17 |
| APPOINTMEN-11 | 0.3 Local orchestration via Docker Compose | feature/APPOINTMEN-11-local-orchestration-docker-compose | [#15](https://github.com/cache-mee/PRISMArc/pull/15) — OPEN, targets `develop`, not yet merged | SKIPPED — unit-test and QA workflows never run (explicit user override, time constraints); code review PASSED (0 CRITICAL/MAJOR); Jira moved straight to Ready for UAT (done-category) | 2026-09-17 |
| APPOINTMEN-17 | 1.5 FR-24: Web Chat Staff identity resolution | feature/APPOINTMEN-17-staff-identity-resolution | [#17](https://github.com/cache-mee/PRISMArc/pull/17) — MERGED into develop (2f7eff6) | SKIPPED — code review, unit-test, and QA workflows all skipped (explicit user override, time constraints); no independent verification performed; Jira moved straight In Review → Ready for UAT (done-category) | 2026-09-17 |
| APPOINTMEN-22 | 2.5 FR-6: Exact-time resolution — direct confirmation | feature/APPOINTMEN-22-exact-time-direct-confirm | [#19](https://github.com/cache-mee/PRISMArc/pull/19) — MERGED into develop (49cfcae) | SKIPPED — code review, unit-test, and QA workflows all skipped (explicit user override, time constraints); no independent verification performed; Jira moved straight In Review → Ready for UAT (done-category); developed in an isolated git worktree | 2026-09-17 |
| APPOINTMEN-26 | 2.9 FR-9: Booking confirmation and creation | feature/APPOINTMEN-26-booking-confirmation-creation | [#24](https://github.com/cache-mee/PRISMArc/pull/24) — MERGED into develop (243e495) | SKIPPED — code review, unit-test, and QA workflows all skipped (explicit user override, time constraints); no independent verification performed; Jira moved straight In Review → Ready for UAT (done-category); developed in an isolated git worktree | 2026-09-17 |
| APPOINTMEN-33 | 3.4 FR-27: Confirmation required before an availability change applies | feature/APPOINTMEN-33-availability-change-confirmation | [#26](https://github.com/cache-mee/PRISMArc/pull/26) — MERGED into develop (b6ceea9) | SKIPPED — code review, unit-test, and QA workflows all skipped (explicit user override, time constraints); no independent verification performed; Jira moved straight In Review → Ready for UAT (done-category); developed in an isolated git worktree; required reconciling a real merge conflict + sync-to-async SQLAlchemy conversion before merge (re-validated after) | 2026-09-17 |
| APPOINTMEN-21 | 2.4 SM-4a: Booking-intent human-verification checkpoint | feature/APPOINTMEN-21-booking-intent-verification-checkpoint | [#32](https://github.com/cache-mee/PRISMArc/pull/32) — MERGED into develop (624ae1f) | SKIPPED — code review, unit-test, and QA workflows all skipped (explicit user override, time constraints); no independent verification performed beyond manual smoke tests and scope-check; Jira moved In Review → Ready for UAT (done-category) via the mechanical In QA/QA Done hops Jira's workflow requires — no QA actually performed; developed in an isolated git worktree | 2026-09-17 |
| APPOINTMEN-23 | 2.6 FR-7: Day-only resolution — list that day's available slots | feature/APPOINTMEN-23-day-only-available-slots | [#33](https://github.com/cache-mee/PRISMArc/pull/33) — MERGED into develop (0b9a83b) | SKIPPED — code review, unit-test, and QA workflows all skipped (explicit user override); no independent verification performed beyond manual/mocked validation during implementation and scope-check; Jira moved In Review → Ready for UAT (done-category) via the mechanical In QA/QA Done hops Jira's workflow requires — no QA actually performed; developed in an isolated git worktree; required merging develop mid-cycle and resolving two real merge conflicts (duplicate `list_bookable_staff` in `staff_repository.py`, docstring/import conflicts in `booking_agent.py`) before merge | 2026-09-17 |
| APPOINTMEN-24 | 2.7 FR-8: Exact-time-unavailable resolution — nearest alternative(s) | feature/APPOINTMEN-24-exact-time-unavailable-alternatives | [#34](https://github.com/cache-mee/PRISMArc/pull/34) — MERGED into develop (a9c82a0) | SKIPPED — code review, unit-test, and QA workflows all skipped (explicit user override); no independent verification performed beyond scope-check and lint; Jira moved In Review → Ready for UAT (done-category) via the mechanical In QA/QA Done hops Jira's workflow requires — no QA actually performed; developed in an isolated git worktree; required merging develop mid-cycle and resolving one real merge conflict (combining this ticket's FR-8 hook with newly-merged FR-7 in `booking_agent.py`) before merge | 2026-09-17 |
| APPOINTMEN-30 | 3.1 FR-25: State an availability change in natural language | feature/APPOINTMEN-30-31-fr-25-state-an-availability-change-in | [#29](https://github.com/cache-mee/PRISMArc/pull/29) — OPEN, targets `develop`, not yet merged | Code review PASSED (0 CRITICAL/MAJOR/MINOR/NITPICK) — independently verified; unit-test and QA workflows deliberately not run (standing fast-mode override, hackathon time constraints); Jira left at "In QA" (indeterminate), not advanced to a done-category status since no QA occurred; mid-flight rework was needed because concurrent tickets APPOINTMEN-19/APPOINTMEN-33 landed on develop during this run and made the original plan's LLM-config/schema tasks redundant — reworked to reuse their code instead | 2026-09-17 |
| APPOINTMEN-53 | 2.13 Web Chat conversation window (chat UI) | feature/APPOINTMEN-53-web-chat-window | [#28](https://github.com/cache-mee/PRISMArc/pull/28) — MERGED into develop (9c66f86) | SKIPPED — code review, unit-test, and QA workflows all skipped (explicit user override, time constraints); no independent verification performed; Jira moved straight In Review → Ready for UAT (done-category); developed in an isolated git worktree; first B2B_FE/ feature code (typed /chat client, ChatWindow, session persistence) — ticket created this session, no Jira ticket existed for the chat UI itself | 2026-09-17 |
| APPOINTMEN-13 | 1.1 Shared data store entities exist | feature/APPOINTMEN-13-shared-data-store-entities | [#21](https://github.com/cache-mee/PRISMArc/pull/21) — MERGED into develop (88005d6) | SKIPPED — Phase 6 code review, unit-test, and QA workflows all skipped (explicit user request); no independent verification performed. Scope trimmed twice mid-flight: develop advanced substantially while this (foundational) ticket was in progress, and other tickets (14/15/17/18/19/22/26/33) independently built most of the shared-entity work first. Final delivered scope: Salon entity (AC1), role-filtered staff queries excluding Owner/Admin (AC3), Bookings→Service FK (AC4 completion) — AC2/AC5/Availability already satisfied elsewhere. Also fixed 3 unrelated pre-existing migration/model bugs found while rebuilding a fresh-database test baseline. Jira moved In Review → In QA → QA Done → Ready for UAT → UAT Approved → Done, per explicit user request — no formal UAT/QA sign-off actually occurred | 2026-09-17 |
| APPOINTMEN-29 | 2.12 FR-12: Reschedule as cancel + rebook | feature/APPOINTMEN-29-reschedule-cancel-rebook | [#35](https://github.com/cache-mee/PRISMArc/pull/35) — MERGED into develop (5d47a90) | SKIPPED — code review, unit-test, and QA workflows all skipped (explicit user override, time constraints); no independent verification performed; Jira moved straight In Review → Ready for UAT (done-category); developed in an isolated git worktree; built the cancel-a-booking primitive from scratch (no prior ticket had it) and an atomic reschedule gate reusing the FR-9 confirmation gate; required reconciling a real merge conflict (concurrent APPOINTMEN-23/24 FR-8 work) before merge (re-validated after) | 2026-09-17 |
| APPOINTMEN-35 | 3.6 FR-29: Staff cannot view the staff list or dashboard | feature/APPOINTMEN-35-staff-no-dashboard-access | [#38](https://github.com/cache-mee/PRISMArc/pull/38) — MERGED into develop (16a01c3) | SKIPPED — code review, unit-test, and QA workflows all skipped (explicit user override, time constraints); no independent verification performed; Jira moved straight In Review → Ready for UAT (done-category); developed in an isolated git worktree; investigation found the forbidden capability was already unreachable from Staff-mode (dead code) so this ticket added a deliberate, testable guard rather than the full role-scoped tool registry mechanism (flagged as a future gap) | 2026-09-17 |

---

## Blocked / Needs Work

| Ticket | Blocked At | Reason | Action Required |
|---|---|---|---|
| — | — | — | — |

---

## How to Use This File

### When starting a new ticket:
1. Run `/sdlc-dev-workflow` → it adds a row to **Active Tickets** automatically.
2. The per-ticket status file lives at `.orchestration/runs/{TICKET}/status.md`.

### When resuming after a break:
1. Read **Active Tickets** — find your ticket row.
2. Open the linked **Status File** — read the **You Are Here** and **How to Resume** sections.
3. Run the command shown under **Resume command** in that file.

### When a ticket completes QA:
1. The `sdlc-qa-workflow` moves the row from **Active** to **Completed**.
2. Merge the PR and transition Jira to Done manually.

---

*Last updated: 2026-09-17 by sdlc-dev-workflow (APPOINTMEN-30 — PR #29 raised, code review PASSED, unit-test/QA workflows skipped per standing fast-mode override)*
