---
name: sdlc-dev-workflow
description: General-purpose development-phase SDLC workflow. Takes a Jira ticket key, reads the ticket, transitions it to In Development, creates a feature branch, produces an implementation plan stored in development/plans/, presents it to the user, and on "implement" reply executes via the Developer agent, pushes and creates a PR, then hands off to the Reviewer agent in a new session. Invoke this when a developer starts work on any Jira ticket.
---

# SDLC Development Workflow

Orchestration rules: `.claude/STANDARDS.md`. This skill owns the development workflow sequence — it does not implement any phase itself. Human gates are stops, not suggestions. Evidence, not claims.

## Conventions

- `{project-root}` is the repository root.
- `{ticket}` is the Jira issue key supplied by the user (e.g. `PROJ-42`).
- `{plans_dir}` resolves to `{project-root}/development/plans/`.
- `{plan_file}` resolves to `{plans_dir}/{ticket}-implementation-plan.md`.
- `{review_file}` resolves to `{plans_dir}/{ticket}-review.md`.
- A **human gate** means: stop, present the artefact, wait for explicit approval. Never reinterpret a gate as optional.
- **Bounded recovery:** each phase gets one retry on failure before escalating to the user.
- **Commits are granular:** commit after each completed task, not once at the end.

---

## On Activation

1. Ask the user: "Which Jira ticket are you starting work on?" if a ticket key was not supplied with the invocation.
2. Check whether `{plan_file}` already exists on disk. If it does, present:
   ```
   ── RESUMING: {ticket} ────────────────────────────────────────────────────────
   An implementation plan already exists at:
     {plan_file}

   Reply with one of:
     resume    → continue from where work left off (read the plan and detect current phase)
     restart   → delete the existing plan and start over
     view      → show the plan, then ask resume / restart
   ──────────────────────────────────────────────────────────────────────────────
   ```
   Wait for the user's reply before proceeding.
3. Perform **GitHub Pre-flight** (see below). Do not proceed past pre-flight until it passes.
4. Begin at **Phase 1** (or the resume phase if resuming).

---

## The Pipeline

```
[JIRA TICKET KEY]
        │
        ▼
  Phase 1: Ticket Intake        (Rovo MCP)
        │   Read ticket · update status → In Development
        │
        ▼
  Phase 2: Branch Setup         (git)
        │   Pull latest · create feature branch · push to remote
        │
        ▼
  Phase 3: Implementation Plan  (Developer agent)
        │   Generate plan → saved to development/plans/{ticket}-implementation-plan.md
        │
  ── GATE 3: Plan Review ───────────── user clicks IMPLEMENT before any code is written
        │
        ▼
  Phase 4: Code Implementation  (Developer agent)
        │   Implement task-by-task · commit each task · push
        │
        ▼
  Phase 5: Pull Request         (git / GitHub)
        │   Push final branch · create PR · update Jira → In Review
        │
        ▼
  Phase 6: Code Review          (Reviewer agent — NEW SESSION)
        │   Reviewer reads plan + PR diff · returns PASS or FAIL
        │   Result saved to development/plans/{ticket}-review.md
        │
        ▼
  [DEVELOPMENT COMPLETE — ready for merge / QA]
```

---

## GitHub Pre-flight

Run before Phase 1. If any check fails, stop and report — do not attempt workarounds.

1. **Git remote:** run `git remote -v`. If no remote is configured, instruct the user to run `git remote add origin <url>` and re-invoke the workflow.
2. **Git identity:** run `git config user.name` and `git config user.email`. If either is empty, instruct the user to set them:
   ```
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```
3. **Default branch:** run `git remote show origin | grep "HEAD branch"` to detect `main` or `master`. Record as `{default_branch}`.
4. **Clean working tree:** run `git status --short`. If there are uncommitted changes, warn the user and ask whether to stash them before proceeding. Do not proceed without a clean tree or explicit user consent.

---

## Phase 1: Ticket Intake

**Owner:** Orchestrator (this workflow)
**MCP tools:** `mcp__claude_ai_Atlassian_Rovo__getJiraIssue`, `mcp__claude_ai_Atlassian_Rovo__getTransitionsForJiraIssue`, `mcp__claude_ai_Atlassian_Rovo__transitionJiraIssue`

### Instructions

1. Call `mcp__claude_ai_Atlassian_Rovo__getJiraIssue` with `{ticket}`. Capture:
   - `summary` — ticket title
   - `description` — full ticket body including acceptance criteria
   - `issueType` — Story / Bug / Task / Chore
   - `assignee` — if set
   - `labels`, `priority`
2. Display the ticket summary to the user so they can confirm it is the correct ticket before proceeding.
3. Call `mcp__claude_ai_Atlassian_Rovo__getTransitionsForJiraIssue` for `{ticket}`. Find the transition that leads to the "In Development" (or "In Progress") status — match against target status name, not transition name. For the SALON project this is the "Start Dev" transition (ID 71). If multiple candidates exist, prefer the one whose target status contains "Development" or "Progress".
4. Present the **In Development gate** and wait for the user's reply:

```
── GATE: START DEVELOPMENT ────────────────────────────────────────────────────
Ticket:  {ticket} — {summary}

Ready to move this ticket to "In Development" in Jira.

Reply with one of:
  yes   → transition to In Development and continue
  no    → skip transition (leave in current status) and continue
──────────────────────────────────────────────────────────────────────────────
```

   - On `yes`: call `mcp__claude_ai_Atlassian_Rovo__transitionJiraIssue` to move the ticket to In Development. If the transition call fails (e.g. ticket already In Development), log the failure and continue — do not stop the workflow.
   - On `no`: skip the transition and continue.

---

## Phase 2: Branch Setup

**Owner:** Orchestrator (this workflow)
**Tools:** git via Bash

### Branch naming

Derive the branch name from the ticket key and summary:
- **Story / Feature:** `feature/{ticket}-{slug}` — e.g. `feature/PROJ-42-user-login`
- **Bug:** `fix/{ticket}-{slug}` — e.g. `fix/PROJ-43-null-crash-on-login`
- **Chore / Task:** `chore/{ticket}-{slug}` — e.g. `chore/PROJ-44-update-dependencies`

`{slug}` = ticket summary lowercased, spaces → hyphens, special characters removed, max 40 characters.

### Instructions

1. `git checkout {default_branch}` — switch to the default branch.
2. `git pull origin {default_branch}` — pull latest. If this fails, stop and report.
3. `git checkout -b {branch_name}` — create the feature branch.
4. `git push -u origin {branch_name}` — push the empty branch to remote and set upstream.
5. Confirm the branch exists on remote: `git branch -vv | grep {branch_name}`.

---

## Phase 3: Implementation Plan

**Owner:** Developer agent (`.claude/agents/developer.md`)
**Template:** `.claude/skills/sdlc-dev-workflow/templates/implementation-plan-template.md`
**Output:** `{plans_dir}/{ticket}-implementation-plan.md`

### Instructions

1. Ensure `{plans_dir}` exists — create it if not (`development/plans/`).
2. Invoke the Developer agent. Pass it:
   - The ticket summary and description captured in Phase 1
   - The template path
   - `stack/rules/base-rules.md` and `stack/rules/client-rules.md`
   - The planning artefacts if available (`bmad-output/planning-artifacts/`)
3. The Developer agent fills in the template:
   - Reads the ticket description and acceptance criteria in full.
   - Includes the ticket key, summary, type, branch at the top of the plan — this is the single source of truth; no separate ticket.md is created.
   - Identifies all affected areas (files, modules, layers) — must read existing code before listing files.
   - Breaks work into tasks small enough to complete and commit independently.
   - Each task's file list must name real, existing files (verified by reading the repo) or clearly flagged new files.
   - Includes testing requirements derived from `stack/rules/base-rules.md`.
   - Explicitly lists what is out of scope for this ticket.
4. Save the completed plan to `{plans_dir}/{ticket}-implementation-plan.md`.
5. No other files are created by this phase — no ticket.md, no status.md, no current.md.

### Gate 3 — Plan Review

Present the plan summary to the user, then show the gate prompt:

```
── GATE 3: IMPLEMENTATION PLAN ───────────────────────────────────────────────
Plan saved at: development/plans/{ticket}-implementation-plan.md

Ticket:  {ticket} — {summary}
Branch:  {branch_name}
Tasks:   {N} tasks identified

{brief task list — one line per task with complexity}

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Reply  implement  to begin coding                                         │
│   Reply  revise: <notes>  to update the plan first (one revision allowed)  │
│   Reply  stop  to end the workflow here                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Do not write a single line of application code until the user replies `implement`.
On `revise`, the Developer agent applies the notes and re-presents; one revision cycle before escalating to the user.
On `stop`, delete `{plan_file}` if the user requests cleanup, then halt.

---

## Phase 4: Code Implementation

**Owner:** Developer agent (`.claude/agents/developer.md`)
**Skills:** `bmad-build` (primary — use for each task); escalate to `bmad-build-auto` only for fully autonomous sub-tasks explicitly noted as such in the plan
**Input:** Approved `{plan_file}` + `stack/rules/base-rules.md` + `stack/rules/client-rules.md`

### Instructions

1. Invoke the Developer agent. Pass it the plan file path, coding rules, and ticket summary.
2. The Developer agent works through the plan **task by task** in the order defined:
   - Reads the relevant existing code before writing anything.
   - Implements exactly what the plan describes for that task — no additional changes, no unrelated refactors.
   - Runs available lint/test commands (from `CLAUDE.md` stack table or discovered from CI config) after each task.
   - After each task is complete, present the **commit message gate** (see below) before committing.
   - If a task fails after one retry, the Developer agent stops and escalates — it does not skip or silently continue.
3. After all tasks are committed, present the **push gate** (see below) before pushing.

### Commit Message Gate (after every task)

After completing a task and staging its files, present the following to the user:

```
── COMMIT: {task title} ──────────────────────────────────────────────────────
Files staged:
  {list of staged files}

Suggested commit message:
  {ticket}: {task title}

  {one paragraph: what changed and why, derived from the task description}

Reply with one of:
  use       → commit with the suggested message above
  edit: <your message>  → commit with your message instead
  skip      → do not commit this task yet (continue to next task)
──────────────────────────────────────────────────────────────────────────────
```

- On `use`: run `git commit` with the suggested message.
- On `edit: <message>`: run `git commit` with the user's exact message.
- On `skip`: continue without committing; remind the user to commit before pushing.
- Do not commit anything without one of the above responses.

### Push Gate (after all tasks are committed)

Before running any `git push`, present:

```
── PUSH CONFIRMATION ─────────────────────────────────────────────────────────
Ready to push branch {branch_name} to origin.

Commits to be pushed:
{output of: git log origin/{branch_name}..HEAD --oneline}
  (or "branch not yet on remote — all commits above will be pushed" if new)

Reply with one of:
  push      → push now
  no        → skip push; you can push manually later with: git push origin {branch_name}
──────────────────────────────────────────────────────────────────────────────
```

- On `push`: run `git push origin {branch_name}`.
- On `no`: continue to Phase 5.
- Never run `git push` without this explicit confirmation.

### What the Developer agent must not do

- Modify files not listed in the approved plan without flagging it first.
- Write unit or integration tests during this phase — tests are authored separately in `sdlc-unit-test-workflow`.
- Squash or amend commits from previous tasks.
- Proceed past a failing lint/test run without reporting it.

---

## Phase 5: Pull Request

**Owner:** Orchestrator (this workflow)
**Tools:** `gh` CLI (GitHub CLI)
**MCP tools:** `mcp__claude_ai_Atlassian_Rovo__transitionJiraIssue`, `mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue`

### Instructions

1. Verify GitHub CLI is available: `gh --version`. If not, skip PR creation and instruct the user to create the PR manually, then continue to Phase 6.
2. If the push gate in Phase 4 was answered `no`, present the push gate again now before creating the PR. Do not create a PR against an un-pushed branch.
3. Generate a PR description inline (no separate pr-body.md file):
   - **Summary:** bullet points of what was implemented (derived from the plan tasks)
   - **Jira Ticket:** link to `{ticket}` on Atlassian
   - **Plan:** path to `{plan_file}`
   - **Test plan:** checklist derived from the plan's testing requirements
4. Create the PR:
   ```
   gh pr create \
     --title "{ticket}: {summary}" \
     --base {default_branch} \
     --head {branch_name} \
     --body "<generated description>"
   ```
5. Capture the PR URL from `gh` output.
6. Call `mcp__claude_ai_Atlassian_Rovo__transitionJiraIssue` to move `{ticket}` to "In Review". On failure, log and continue.
7. Call `mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue` with: `"PR raised: {pr_url} — awaiting review."`.

---

## Phase 6: Code Review (New Session)

**Owner:** Reviewer agent (`.claude/agents/reviewer.md`) — invoked in a **new Claude Code session**
**Template:** `.claude/skills/sdlc-dev-workflow/templates/review-template.md`
**Input:** `{plan_file}` + PR diff
**Output:** `{review_file}` (`development/plans/{ticket}-review.md`)

### Handoff

After Phase 5, present the following to the user:

```
── PHASE 6: CODE REVIEW HANDOFF ──────────────────────────────────────────────
Implementation is complete and the PR is raised.

  Ticket:   {ticket} — {summary}
  Branch:   {branch_name}
  PR:       {pr_url}
  Plan:     development/plans/{ticket}-implementation-plan.md

To start the code review, open a NEW Claude Code session and run:
  /sdlc-dev-workflow review {ticket}

The Reviewer agent will read the plan, inspect the PR diff, and produce
development/plans/{ticket}-review.md with a PASS or FAIL verdict.
──────────────────────────────────────────────────────────────────────────────
```

### When invoked in review mode (`/sdlc-dev-workflow review {ticket}`)

1. Read `{plan_file}`. If not found, ask the user for the path.
2. Get the PR diff: `gh pr diff` (detect PR from branch) or `git diff {default_branch}...{branch_name}`.
3. Load the review template from `.claude/skills/sdlc-dev-workflow/templates/review-template.md`.
4. Invoke the Reviewer agent with plan + diff as input.
5. The Reviewer agent:
   - Inspects the diff against every acceptance criterion in the plan before drawing conclusions.
   - Completes every section of the review template. No section may be left blank.
   - Returns an explicit **PASS** or **FAIL** verdict in the Summary section.
6. Save the completed review to `{review_file}`.
7. Present the verdict to the user.

### On FAIL

```
── REVIEW FAILED ─────────────────────────────────────────────────────────────
Review: development/plans/{ticket}-review.md

CRITICAL issues: {N}  (must fix before merge)
MAJOR issues:    {N}  (should fix before merge)

To fix and re-review:
1. Address the CRITICAL and MAJOR issues in the review file.
2. Commit fixes to branch {branch_name}.
3. Push: git push origin {branch_name}
4. Re-run: /sdlc-dev-workflow review {ticket}
──────────────────────────────────────────────────────────────────────────────
```

### On PASS

1. Call `mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue` with: `"Automated review passed. PR {pr_url} is ready for merge."`.
2. Present the **Done gate** and wait for the user's reply:

```
── REVIEW PASSED ─────────────────────────────────────────────────────────────
Review: development/plans/{ticket}-review.md

The PR is ready to merge.
  PR:     {pr_url}
  Ticket: {ticket}

Move {ticket} to "Done" in Jira now?

Reply with one of:
  yes   → transition ticket to Done in Jira
  no    → skip (you can transition manually in Jira after merging)
──────────────────────────────────────────────────────────────────────────────
```

   - On `yes`: call `mcp__claude_ai_Atlassian_Rovo__getTransitionsForJiraIssue` for `{ticket}` to find the transition to "Done", then call `mcp__claude_ai_Atlassian_Rovo__transitionJiraIssue`. If the transition fails (e.g. project requires PR to be merged first), log the failure and advise the user to transition manually.
   - On `no`: continue.

---

## Plans Directory Structure

`{plans_dir}` = `development/plans/`

```
development/
└── plans/
    ├── {ticket}-implementation-plan.md   # Plan + ticket context (single source of truth)
    └── {ticket}-review.md                # Review output (created only during Phase 6)
```

**One plan file per ticket. No ticket.md, no status.md, no current.md.**
The plan file contains the ticket reference, branch, acceptance criteria, and all tasks.
It is the only artefact persisted to disk between phases.

---

## Skill Selection Guide for the Developer Agent

| Task size / type | Skill to use |
|---|---|
| Single bounded change (one task from the plan) | `bmad-build` |
| Multi-step unattended sub-task explicitly flagged in the plan | `bmad-build-auto` |
| Design decision needed mid-implementation | Stop, escalate to user, do not proceed |
| Out-of-scope finding during implementation | Note in the plan file under a "Deviations" section, do not fix, continue |

The Developer agent MUST NOT invoke `bmad-quick-dev` (deprecated), `bmad-dev-story` (deprecated), or any planning-phase skills during implementation.

---

## Stop Conditions (Any Phase)

- The user replies `stop` at any gate.
- GitHub pre-flight fails and the user does not resolve the issue.
- A required source file or artefact does not exist on disk.
- The Developer agent exhausts its retry limit without producing output.
- A lint or test run fails after one retry.
- A human decision is required that no agent can make.

On any stop: tell the user exactly where things stand and what command to run to resume. The plan file at `{plan_file}` preserves all context needed to continue in a future session.

---

## Resuming a Stopped Run

On activation, the workflow checks whether `{plan_file}` exists. If it does, it reads the file, presents a resume/restart/view prompt, and continues from the appropriate phase. No separate status file is needed — the plan file is the single resume anchor.
