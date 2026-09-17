# Project Workflow Status

> This file is the single source of truth for where the project stands across all SDLC workflows.
> Every workflow updates its relevant section on each phase completion.
> Read this first when resuming any work after a break.

---

## Planning Phase (sdlc-planning-workflow)

| Phase | Status | Artefact | Gate |
|---|---|---|---|
| 1 — Discovery & Brief | `pending` | | Brief Approval |
| 2 — PRD | `pending` | | (inline) |
| 3 — Tech Stack | `pending` | | Stack Approval |
| 4 — UX Design | `pending` | | Design Approval |
| 5 — Epics & Stories | `pending` | | — |
| 6 — Confluence Push | `pending` | | Push Summary |
| 7 — Jira Push | `pending` | | Push Summary |

**Planning status:** `not started`
**Last updated by:** —
**Resume command:** `/sdlc-planning-workflow`

---

## Active Tickets

> One row per ticket currently in progress. Updated by sdlc-dev-workflow, sdlc-unit-test-workflow, and sdlc-qa-workflow.

| Ticket | Summary | Branch | Current Workflow | Phase | Waiting On | Status File |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

> Note: a planning run also exists at `.orchestration/runs/planning-salon-app/`, tracked in its
> own `workflow-status.md` rather than this file's Planning Phase table above — that table is not
> currently kept in sync by `sdlc-planning-workflow` and is a known separate gap, out of scope
> for this fix.

---

## Completed Tickets

| Ticket | Summary | Branch | PR | QA Verdict | Completed |
|---|---|---|---|---|---|
| APPOINTMEN-10 | 0.2 Frontend project scaffolding | feature/APPOINTMEN-10-02-frontend-project-scaffolding | [#13](https://github.com/cache-mee/PRISMArc/pull/13) — MERGED into develop (a356f67) | PASS (17/19, 2 not validated — Docker build unverified) | 2026-09-17 |

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

*Last updated: 2026-09-17 by sdlc-qa-workflow*
