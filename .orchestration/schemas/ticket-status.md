# Ticket Status Schema

The durable, **human-readable** per-ticket status file consumed by `workflow-status`'s Ticket
Detail Mode. Written and updated by `sdlc-dev-workflow`, `sdlc-unit-test-workflow`, and
`sdlc-qa-workflow` — the three workflows that share `{run_dir}` for one ticket.

This is narrower in purpose than `run-record.md`: `run-record.md` is an append-only metrics
ledger (one row per phase, never rewritten); `status.md` is a **rewritten-in-place** snapshot of
where things stand right now, plus a companion `current.md` that names only the active
workflow/phase/waiting-on for the fast resume-prompt each workflow shows on activation.

## Where it lives

| File | Path | Written by |
|---|---|---|
| `current.md` | `.orchestration/runs/{ticket}/current.md` | all three workflows, on every phase/gate transition |
| `status.md` | `.orchestration/runs/{ticket}/status.md` | all three workflows, on every phase/gate transition |

## `current.md` — required shape

Small and cheap to read on every activation. Fields are updated in place, never appended.

```markdown
workflow: {sdlc-dev-workflow | sdlc-unit-test-workflow | sdlc-qa-workflow}
phase: {exact phase or gate name, e.g. "Phase 3 — Implementation Plan" or "Gate 3 — Plan Review"}
status: {running | waiting | complete | stopped}
waiting: {what a human reply is needed for, or "n/a"}
next: {concrete next action, one line}
```

## `status.md` — required shape

```markdown
# {ticket} — status

Summary: {ticket summary}
Branch:  {branch name, or "n/a" before Phase 2 of sdlc-dev-workflow}
PR:      {pr_url, or "not yet raised"}

## You Are Here
Workflow: {current workflow}
Phase:    {current phase}
Waiting:  {waiting on}
Next:     {next action}

## Phase Tracker

### sdlc-dev-workflow
[{✓|→|✗|-| }] Phase 1 — Ticket Intake
[{✓|→|✗|-| }] Phase 2 — Branch Setup
[{✓|→|✗|-| }] Phase 3 — Implementation Plan
[{✓|→|✗|-| }] Gate 3 — Plan Review
[{✓|→|✗|-| }] Phase 4 — Code Implementation
[{✓|→|✗|-| }] Phase 5 — Pull Request
[{✓|→|✗|-| }] Phase 6 — Code Review

### sdlc-unit-test-workflow
[{✓|→|✗|-| }] Phase 1 — Code Reconnaissance
[{✓|→|✗|-| }] Phase 2 — Unit Test Plan
[{✓|→|✗|-| }] Gate 2 — Test Plan Approval
[{✓|→|✗|-| }] Phase 3 — Write Unit Tests
[{✓|→|✗|-| }] Phase 4 — Commit & Push

### sdlc-qa-workflow
[{✓|→|✗|-| }] Phase 1 — Feature Understanding
[{✓|→|✗|-| }] Phase 2 — Integration Test Plan
[{✓|→|✗|-| }] Gate 2 — Test Plan Approval
[{✓|→|✗|-| }] Phase 3 — Write & Run Integration Tests
[{✓|→|✗|-| }] Phase 4 — QA Verdict

## Artefacts
{name}   {path}   [{status}]

## Commits
{sha}   {message}
(none yet if empty)

## Jira Transitions
{transition name}   →   {target status}   [{result}]

## Issues & Blockers
{phase}   {issue}   {resolution}
(none if empty)

## How to Resume
{one or two lines: exact command to run next, and what it will do}
```

Legend (matches `workflow-status`'s Ticket Detail Mode exactly): `✓` complete · `→` current ·
` ` (blank) pending · `✗` stopped/failed · `-` skipped.

## Field rules

- **Rewrite in place.** Unlike `run-record.md`, `status.md` and `current.md` are not append-only
  — each update replaces the relevant section/field with current reality. History lives in
  `run-record.md`, not here.
- **Phase Tracker** always shows all three workflows' full phase lists, regardless of which one
  is currently active — a workflow not yet reached shows every phase blank (` `), a workflow
  already finished shows every phase `✓` (or `✗`/`-` where that's what happened).
- **Commits** and **Jira Transitions** are short, human-scannable summaries — derive them from
  `run-record.md`'s `Evidence` column (`commit:<sha>`, `jira:transitioned`) rather than
  maintaining a second independent log; `run-record.md` remains the source of truth for exact
  ordering and timestamps.
- **How to Resume** must always be concrete enough to act on without reading anything else —
  the exact slash command, not "continue from where you left off".
- If `status.md`/`current.md` cannot be written for any reason, note it and continue — these
  files improve resumability and `workflow-status`'s output; they must never block a workflow's
  own phase from completing.

## Relationship to other durable state

`run-record.md` is the append-only metrics ledger; `status.md`/`current.md` are the
rewritten-in-place human snapshot `workflow-status` reads; `development/plans/{ticket}-*.md` are
the actual work products (plan, review). None of these three replace either of the others — see
`.orchestration/schemas/run-record.md` for how they relate to `handoff.md` and `status.json` as
well.
