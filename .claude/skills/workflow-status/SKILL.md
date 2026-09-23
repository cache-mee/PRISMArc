---
name: workflow-status
description: Shows where you are in any SDLC workflow. Call with no arguments for a project-wide overview, or pass a Jira ticket key (e.g. /workflow-status PROJ-42) for a per-ticket drill-down. Invoke this any time you want to know what is in progress, what is blocked, and exactly what to do next.
---

# Workflow Status

This skill is read-only. It reads status files and presents them — it does not change anything.

**Resolve the main clone first.** `.orchestration/PROJECT-STATUS.md` and `.orchestration/runs/`
live in the **main clone**, not any ticket's worktree — if this skill is invoked from inside a
worktree created by `sdlc-dev-workflow` (`.claude/skills/worktree-add/SKILL.md`), reading these
paths relative to the current directory reads that worktree's own stale checked-out copy instead
of the live one. The main clone is always the first `worktree` entry in
`git worktree list --porcelain`, run from anywhere. Resolve that path once, and read every
`.orchestration/`-relative path below from it.

---

## On Activation

Detect which mode to run based on whether a ticket key was supplied:

- **No argument** → run in **Project Overview** mode.
- **Ticket key supplied** (e.g. `PROJ-42`) → run in **Ticket Detail** mode.

---

## Project Overview Mode

Read `.orchestration/PROJECT-STATUS.md`.

Present the following, derived from the file:

```
── PROJECT STATUS ─────────────────────────────────────────────────────────────

PLANNING PHASE
  {each phase row from the Planning Phase table, formatted as:}
  Phase {N} — {Name}   [{status}]   {artefact path if present}

ACTIVE TICKETS
  {ticket}   {summary}   [{current workflow / phase}]   waiting: {waiting on}
  {ticket}   ...

BLOCKED / NEEDS WORK
  {ticket}   {reason}   action: {action required}
  (none if empty)

COMPLETED TICKETS
  {ticket}   {summary}   QA: {verdict}   PR: {pr_url}
  (none if empty)

──────────────────────────────────────────────────────────────────────────────
To drill into a ticket:  /workflow-status {TICKET}
To resume a workflow:    /{workflow-name} {TICKET}
──────────────────────────────────────────────────────────────────────────────
```

If `PROJECT-STATUS.md` does not exist, report:
```
No PROJECT-STATUS.md found at .orchestration/PROJECT-STATUS.md
No workflows have been run yet in this repository.
Start with: /sdlc-planning-workflow
```

---

## Ticket Detail Mode

1. Read `.orchestration/runs/{ticket}/status.md`.
   - If not found: report "No status file found for {ticket}. Has sdlc-dev-workflow been run for this ticket?"
2. Present the full status file contents formatted as:

```
── TICKET: {ticket} — {summary} ──────────────────────────────────────────────

YOU ARE HERE
  Workflow : {current workflow}
  Phase    : {current phase}
  Waiting  : {waiting on}
  Next     : {next action}

PHASE TRACKER

  sdlc-dev-workflow
  {phase rows as: [✓] Phase N — Name  or  [ ] Phase N — Name  or  [→] Phase N — Name (current)}

  sdlc-unit-test-workflow
  {phase rows}

  sdlc-qa-workflow
  {phase rows}

ARTEFACTS
  {artefact name}   {path}   [{status}]
  {artefact name}   ...

COMMITS
  {SHA}   {message}
  (none yet if empty)

JIRA TRANSITIONS
  {transition}   →   {status}   [{result}]

ISSUES & BLOCKERS
  {phase}   {issue}   {resolution}
  (none if empty)

HOW TO RESUME
  {exact How to Resume section from status.md}

──────────────────────────────────────────────────────────────────────────────
Branch : {branch}
PR     : {pr_url or "not yet raised"}
──────────────────────────────────────────────────────────────────────────────
```

Legend for phase rows:
- `[✓]` = complete
- `[→]` = current / in progress
- `[ ]` = pending
- `[✗]` = stopped / failed
- `[-]` = skipped

---

## Nothing to Show

If both `PROJECT-STATUS.md` and the ticket run directory are absent, output:

```
── NO WORKFLOW STATE FOUND ────────────────────────────────────────────────────
This repository has no active or completed workflow runs yet.

To get started:
  /sdlc-planning-workflow    → begin planning a new product or feature
  /sdlc-dev-workflow         → start development on a Jira ticket
──────────────────────────────────────────────────────────────────────────────
```
