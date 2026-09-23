---
project: salon-app
started: 2026-09-17
status: complete
last_completed_phase: 7
---

## Notes

Full pivot: the marketplace-scope brief/PRD/UX/epics (created 2026-09-04/05) were deleted by
the user prior to this run. This is a clean-slate planning cycle for the hackathon scope
(Agentic Appointment Management Engine — Salon Edition), not a revision of the old plan.

Deviation from this skill's literal phase-owner labels: Phase 1 (Discovery & Brief) was routed
to the **product-manager** agent, not business-analyst, because this repo's actual agent
contracts (`.claude/agents/product-manager.md` vs `.claude/agents/business-analyst.md`) assign
`bmad-product-brief` (Create) to the Product Manager. The business-analyst agent correctly
refused the task on scope-boundary grounds when first attempted.

Phase 3 (Tech Stack): the Architect evaluated the user's stated Flutter + FastAPI + Postgres
leaning (`addendum.md` §2.2–2.4) against the approved PRD rather than adopting it as given.
Recommendation: React+TypeScript (not Flutter) for the web frontend, FastAPI (Python)
confirmed for the backend, Postgres confirmed for the database, no native mobile app (explicit
N/A, not an omission), direct in-process tool registration (not the sketched MCP layer),
backend-persisted conversation state (not client-resent history). Full rationale and
alternatives in `stack/stack-proposal.md`. Approved at Gate 3.

Phase 4 (UX Design): produced as four surface-scoped artefacts rather than the generic
bmad-ux skill's interactive DESIGN.md/EXPERIENCE.md spine pair, per the orchestrating agent's
explicit output-shape instruction for this headless run — a per-surface spec (conversational
turn structure for the two chat agents, a traditional screen-layout spec for the dashboard, plus
a WhatsApp channel-delta note) matches this product's conversational-first shape (PRD §0) more
directly than a generic visual-identity/IA spine pair would. Five UX-driven open questions were
forwarded rather than resolved unilaterally (SM-4a/b/c operator-hook mechanism, Dashboard access
gating, WhatsApp Sandbox interactive-button feasibility, and two non-blocking design-consistency
notes) — see `.orchestration/runs/planning-salon-app/handoff.md` for the full list and owners.

## Post-approval revisions

- **2026-09-18** — Phase 3 (Tech Stack) revised, not reopened: `stack/stack-proposal.md` §5 finalizes
  demo hosting as EC2 `t2.micro`+Docker (backend), S3+CloudFront (frontend), RDS Postgres (database),
  superseding the original "local + tunnel / PaaS" recommendation. `stack/rules/base-rules.md` updated
  to match (Infra row, Forbidden bullet, Secrets bullet), sign-off recorded in its frontmatter. Gate 3
  itself was not reopened — the stack (React/FastAPI/Postgres/Twilio) is unchanged, only the hosting
  mechanism. Open item carried forward: CloudFront/EC2 cross-origin `fetch()` calls + no CORS on the
  backend, not yet resolved. Tracked in Jira: APPOINTMEN-61 (original APPOINTMEN-60 deleted by user, recreated as
  APPOINTMEN-61). Branch: `chore/APPOINTMEN-60-finalize-hosting` (name unchanged; PR #66).

## Phase Status

| Phase | Status | Artefact Path | Gate | Gate Status |
|---|---|---|---|---|
| 1 — Brief | done | bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/brief.md | Brief Approval | approved |
| 2 — PRD | done | bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md | (inline) | done |
| 3 — Stack | done (revised 2026-09-18) | stack/stack-proposal.md | Stack Approval | approved |
| 4 — UX Design | done | bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/ | Design Approval | pending |
| 5 — Epics & Stories | done | bmad-output/planning-artifacts/epics/epics-salon-app-2026-09-17.md | (none) | — |
| 6 — Confluence Push | done | | Push Summary | done — 8 pages created in space AP |
| 7 — Jira Push | done | | Push Summary | done — APPOINTMEN-1..52 created |

## Confluence Push Results

| Document | Confluence URL | Status |
|---|---|---|
| Product Brief | https://experionglobal.atlassian.net/wiki/spaces/AP/pages/5883297900 | created |
| PRD | https://experionglobal.atlassian.net/wiki/spaces/AP/pages/5883920426 | created |
| Tech Stack | https://experionglobal.atlassian.net/wiki/spaces/AP/pages/5882904635 | created |
| UX: Customer Booking Chat | https://experionglobal.atlassian.net/wiki/spaces/AP/pages/5883363371 | created |
| UX: Staff Owner Manager Chat | https://experionglobal.atlassian.net/wiki/spaces/AP/pages/5883494428 | created |
| UX: Owner Dashboard | https://experionglobal.atlassian.net/wiki/spaces/AP/pages/5884215306 | created |
| UX: WhatsApp Deltas | https://experionglobal.atlassian.net/wiki/spaces/AP/pages/5884608542 | created |
| Epics & Stories | https://experionglobal.atlassian.net/wiki/spaces/AP/pages/5884936215 | created |

## Jira Push Results

| Epic | Jira Key | Stories Pushed | Failures |
|---|---|---|---|
| Epic 0: Project Scaffolding & Environment Setup | APPOINTMEN-1 | 4 (APPOINTMEN-9..12) | 0 |
| Epic 1: Shared Foundation — Domain Model & Identity Resolution | APPOINTMEN-2 | 5 (APPOINTMEN-13..17) | 0 |
| Epic 2: Customer Booking Lifecycle | APPOINTMEN-3 | 12 (APPOINTMEN-18..29) | 0 |
| Epic 3: Staff Availability Management | APPOINTMEN-4 | 7 (APPOINTMEN-30..36) | 0 |
| Epic 4: Owner/Admin Catalog Management | APPOINTMEN-5 | 7 (APPOINTMEN-37..43) | 0 |
| Epic 5: Owner Dashboard | APPOINTMEN-6 | 2 (APPOINTMEN-44..45) | 0 |
| Epic 6: Shared State & Live Reflection | APPOINTMEN-7 | 2 (APPOINTMEN-46..47) | 0 |
| Epic 7: WhatsApp Channel Integration | APPOINTMEN-8 | 5 (APPOINTMEN-48..52) | 0 |
