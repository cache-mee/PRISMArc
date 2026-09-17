---
name: sdlc-dev-workflow
description: General-purpose development-phase SDLC workflow. Takes a Jira ticket key, reads the ticket, transitions it to In Development, creates a feature branch, produces an implementation plan stored in development/plans/, presents it to the user, and on "implement" reply executes via the Developer agent, pushes and creates a PR, then hands off to the Reviewer agent in a new session. Invoke this when a developer starts work on any Jira ticket.
---

# SDLC Development Workflow

Orchestration rules: `.claude/STANDARDS.md`. This skill owns the development workflow sequence — it does not implement any phase itself. Human gates are stops, not suggestions. Evidence, not claims.

## Conventions

- `{project-root}` is the **main clone** — never a ticket's worktree, even if this workflow
  happens to be invoked from inside one. `git rev-parse --show-toplevel` is ambiguous once
  worktrees exist (it returns whichever checkout you're standing in); the main clone is always
  the first `worktree` entry in `git worktree list --porcelain`, run from anywhere. Resolve it
  once at activation and use that absolute path for every `{project-root}`-relative reference
  below, regardless of which directory subsequent Bash commands `cd`/`-C` into for
  `{worktree_path}` work.
- `{ticket}` is the Jira issue key supplied by the user (e.g. `PROJ-42`).
- `{plans_dir}` resolves to `{worktree_path}/development/plans/` once Phase 2 has created the
  worktree — Phase 1 never touches it, so there's no ordering conflict.
- `{plan_file}` resolves to `{plans_dir}/{ticket}-implementation-plan.md`.
- `{review_file}` resolves to `{plans_dir}/{ticket}-review.md`.
- `{run_dir}` resolves to `{project-root}/.orchestration/runs/{ticket}/`.
- `{run_record}` resolves to `{run_dir}/run-record.md`.
- `{worktree_path}` is set by Phase 2 (via the `worktree-add` skill) — the isolated git
  worktree where `{branch_name}` actually lives. From Phase 2 onward, every git/build/test/commit
  command for this ticket's code, and every read/write under `{plans_dir}`, runs with
  `{worktree_path}` as its working directory, never `{project-root}`. `development/plans/` is
  git-tracked (not gitignored) precisely so the plan and review files commit and travel with the
  branch into any worktree or fresh clone — a later session finds them by resolving
  `{worktree_path}` again via the `worktree-add` skill, not by a fixed project-root path.
  `{run_dir}` and `PROJECT-STATUS.md` stay anchored to `{project-root}` regardless — they are
  cross-ticket / resumability aids meant to be visible from the main checkout independent of which
  ticket's worktree is currently active.
- A **human gate** means: stop, present the artefact, wait for explicit approval. Never reinterpret a gate as optional.
- **Bounded recovery:** each phase gets one retry on failure before escalating to the user.
- **Commits are granular:** commit after each completed task, not once at the end.

---

## Communication Style (automatic)

From activation, apply the caveman compression style (`.claude/skills/caveman/SKILL.md`, level
`full`) to every piece of conversational output this workflow produces — status updates, phase
narration, plan summaries shown inline — automatically, for the whole run. No `/caveman`
command needed; do not wait for the user to ask. It never applies to persisted artefacts
(`{plan_file}`, `{review_file}`, commit messages, PR bodies, Jira comments, `{run_record}` rows)
and it auto-drops for gate prompts and irreversible-action confirmations, per that skill's own
Boundaries and Auto-Clarity rules, so it never makes a human gate ambiguous.

---

## Run Record (agent-metrics)

Schema: `.orchestration/schemas/run-record.md`.

- On first use, create `{run_record}` with `Issue: {ticket}`, `Branch: n/a` (until Phase 2),
  `State: in-development`. If a planning-cycle run-record exists for this ticket's originating
  epic (`.orchestration/runs/planning-*/run-record.md`, check its Evidence rows for
  `created:{ticket}`), set `Task:` to that path.
- After **every** phase below completes, and after every gate reply, append one row: `Step` =
  `[dev] Phase N — Name` (or `[dev] Gate N — Name`), `Owner` = `lead` (Phases 1–2) /
  `developer` (Phases 3–4) / `reviewer` (Phase 6), or exactly `human` for a gate reply,
  `Outcome` = `done` / `failed` / `awaiting`, `Evidence` = `commit:<sha>` / `exit:<code>:<cmd>`
  / `jira:transitioned` / `pr:<url>` / `approved` as applicable, `At` = now, ISO-8601 — get the
  real current time by running `date -u +%Y-%m-%dT%H:%M:%S+00:00`; never approximate or pad to
  midnight.
- `State` stays `in-development` throughout this workflow — the next workflow to touch
  `{run_record}` (`sdlc-unit-test-workflow`) is what advances it. Set `State: stopped` if the
  user replies `stop` at any gate.
- Never let this slow down or gate the workflow itself. If `{run_record}` cannot be written,
  note it and continue.

---

## Status Artefacts (workflow-status)

Schema: `.orchestration/schemas/ticket-status.md`. These are separate from `{run_record}` —
`run-record.md` is an append-only metrics ledger; `current.md`/`status.md` are the
rewritten-in-place snapshot `workflow-status` reads, and `.orchestration/PROJECT-STATUS.md` is
the project-wide index of active/completed/blocked tickets.

- On first use (Phase 1), create `{run_dir}/current.md` and `{run_dir}/status.md` per the
  schema, and add a row for `{ticket}` to the **Active Tickets** table in
  `.orchestration/PROJECT-STATUS.md` (create the file from scratch using the structure already
  documented in `.claude/skills/workflow-status/SKILL.md`'s Project Overview template if it does
  not yet exist — do not invent a different shape).
- After **every** phase and gate reply, update (never append) `current.md`'s five fields and
  `status.md`'s "You Are Here" section and the matching Phase Tracker row for
  `sdlc-dev-workflow`, and update this ticket's row in `PROJECT-STATUS.md`'s Active Tickets table
  (Current Workflow = `sdlc-dev-workflow`, Phase = the phase just reached, Waiting On = the gate
  question if one is pending, else "—").
- Phase 2 sets `status.md`'s `Branch:` field once the branch exists, and records `{worktree_path}`
  in that same Phase 2 Notes cell — a resumed session needs the path, not just the branch name.
- Phase 5 sets `status.md`'s `PR:` field once the PR is created.
- On the Phase 6 handoff (see below), set `current.md`'s `waiting` to
  "new session: /sdlc-dev-workflow review {ticket}" and leave the ticket's `PROJECT-STATUS.md`
  row in Active Tickets — the ticket is not done; it is handed off, not completed.
- Never let this slow down or gate the workflow itself. If these files cannot be written, note
  it and continue — they are resumability aids, not correctness-critical state.

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
  Phase 2: Branch Setup         (worktree-add skill, git)
        │   Pull latest · create isolated worktree + feature branch · push to remote
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
**Skill:** `worktree-add` (`.claude/skills/worktree-add/SKILL.md`)
**Tools:** git via Bash

### Branch naming

Derive the branch name from the ticket key and summary:
- **Story / Feature:** `feature/{ticket}-{slug}` — e.g. `feature/PROJ-42-user-login`
- **Bug:** `fix/{ticket}-{slug}` — e.g. `fix/PROJ-43-null-crash-on-login`
- **Chore / Task:** `chore/{ticket}-{slug}` — e.g. `chore/PROJ-44-update-dependencies`

`{slug}` = ticket summary lowercased, spaces → hyphens, special characters removed, max 40 characters.

### Instructions

1. Invoke the `worktree-add` skill with `{branch_name}` (base defaults to `{default_branch}`; pass
   `--from {default_branch}` explicitly if it was overridden during GitHub Pre-flight). It fetches
   `origin`, creates `{branch_name}` from `{default_branch}` if it doesn't exist yet, and checks it
   out into a new isolated worktree. Capture its stdout path as `{worktree_path}`.
2. If the skill reports a non-zero exit, stop and report per its Failure handling section — do not
   fall back to a plain `git checkout -b` in `{project-root}`.
3. `git -C {worktree_path} push -u origin {branch_name}` — push the branch to remote and set
   upstream (the tool creates the branch and worktree locally but never pushes).
4. Confirm the branch exists on remote: `git -C {worktree_path} branch -vv | grep {branch_name}`.
5. From here on, every git/build/test/commit command for this ticket runs with `{worktree_path}`
   as its working directory — see the `{worktree_path}` convention above.

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
5. No separate `ticket.md` is created by this phase — the plan file's own Ticket Reference
   section is the single source of truth for ticket context. (`current.md`/`status.md` are
   maintained per the **Status Artefacts** section above, not by this phase specifically.)

### Gate 3 — Plan Review

Present the plan summary to the user, then show the gate prompt:

```
── GATE 3: IMPLEMENTATION PLAN ───────────────────────────────────────────────
Plan saved at: {plan_file}

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
**Also runs:** `tools/scope-check/` — mechanical check of CLAUDE.md's Repository layout rule, before the push gate

### Instructions

1. Invoke the Developer agent. Pass it the plan file path, coding rules, ticket summary, and
   `{worktree_path}` — all file edits, commands and commits for this ticket happen there, not in
   `{project-root}` (the plan file itself is the one exception: it is read from and, if amended,
   written back to `{plan_file}` under `{project-root}`).
2. The Developer agent works through the plan **task by task** in the order defined:
   - Reads the relevant existing code before writing anything.
   - Implements exactly what the plan describes for that task — no additional changes, no unrelated refactors.
   - Runs available lint/test commands (from `CLAUDE.md` stack table or discovered from CI config) after each task.
   - After each task is complete, present the **commit message gate** (see below) before committing.
   - If a task fails after one retry, the Developer agent stops and escalates — it does not skip or silently continue.
3. After all tasks are committed, run (from `{worktree_path}`):
   ```
   tools/scope-check/scope-check --base {default_branch} --head {branch_name}
   ```
   - **Exit 0 (PASS):** continue to the push gate.
   - **Exit 1 (FAIL):** stop. Do not present the push gate, do not push, do not proceed to
     Phase 5. Report scope-check's output verbatim (it names the backend and frontend files
     separately) and tell the user this ticket must be split into two bounded changes, one per
     folder, per CLAUDE.md's Repository layout rule. This is a stop condition — the Developer
     agent does not attempt to split the change itself; that is a re-planning decision for the
     user, back at Phase 3.
4. After scope-check passes, present the **push gate** (see below) before pushing.

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

- On `use`: run `git commit` (from `{worktree_path}`) with the suggested message.
- On `edit: <message>`: run `git commit` (from `{worktree_path}`) with the user's exact message.
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

- On `push`: run `git push origin {branch_name}` from `{worktree_path}`.
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
4. Create the PR (from `{worktree_path}`, so `gh` infers the right repo/branch context):
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
  Plan:     {plan_file}

To start the code review, open a NEW Claude Code session and run:
  /sdlc-dev-workflow review {ticket}

The Reviewer agent will read the plan, inspect the PR diff, and produce
{review_file} with a PASS or FAIL verdict.
──────────────────────────────────────────────────────────────────────────────
```

### When invoked in review mode (`/sdlc-dev-workflow review {ticket}`)

1. Resolve `{worktree_path}` for `{branch_name}` via the `worktree-add` skill (idempotent — this
   is a fresh session, so nothing has created or found it yet here). Read `{plan_file}` from
   inside it. If not found, ask the user for the path.
2. Get the PR diff: `gh pr diff` (detect PR from branch) or `git diff {default_branch}...{branch_name}`.
3. Run `tools/scope-check/scope-check --base {default_branch} --head {branch_name}` independently
   — do not trust that Phase 4's check still holds; commits may have been added since. A FAIL
   here is a CRITICAL finding regardless of anything else in the diff, and forces the overall
   verdict to **FAIL** — per CLAUDE.md's Repository layout rule, there is no override.
4. Load the review template from `.claude/skills/sdlc-dev-workflow/templates/review-template.md`.
5. Invoke the Reviewer agent with plan + diff + scope-check result as input.
6. The Reviewer agent:
   - Inspects the diff against every acceptance criterion in the plan before drawing conclusions.
   - Completes every section of the review template. No section may be left blank.
   - Returns an explicit **PASS** or **FAIL** verdict in the Summary section.
7. Save the completed review to `{review_file}`.
8. Present the verdict to the user.

### On FAIL

```
── REVIEW FAILED ─────────────────────────────────────────────────────────────
Review: {review_file}

CRITICAL issues: {N}  (must fix before merge)
MAJOR issues:    {N}  (should fix before merge)

To fix and re-review:
1. Address the CRITICAL and MAJOR issues in the review file, in the ticket's worktree
   ({worktree_path} — re-run the `worktree-add` skill with {branch_name} if this is a fresh
   session and the path isn't already known).
2. Commit fixes to branch {branch_name}.
3. Push: git push origin {branch_name}
4. Re-run: /sdlc-dev-workflow review {ticket}
──────────────────────────────────────────────────────────────────────────────
```

### On PASS

**Do not target Jira's "Done" (or any status in Jira's `done` status category) at this point.**
QA has not run yet — `sdlc-unit-test-workflow` and `sdlc-qa-workflow` still stand between this
review passing and the ticket being genuinely finished. Reaching a `done`-category status is
`sdlc-qa-workflow` Phase 4's job (see that skill's Jira-transition rule), never this phase's.

1. Call `mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue` with: `"Automated review passed. PR {pr_url} is ready for merge."`.
2. Present the **next-stage gate** and wait for the user's reply:

```
── REVIEW PASSED ─────────────────────────────────────────────────────────────
Review: {review_file}

The PR is ready to merge, but QA has not run yet.
  PR:     {pr_url}
  Ticket: {ticket}

Move {ticket} forward in Jira now (to whatever this project's next in-progress
status is after review — e.g. "Ready for QA" — never to Done/Ready for UAT/any
done-category status)?

Reply with one of:
  yes   → transition ticket to the next in-progress status in Jira
  no    → skip (leave the ticket's Jira status as-is)
──────────────────────────────────────────────────────────────────────────────
```

   - On `yes`: call `mcp__claude_ai_Atlassian_Rovo__getTransitionsForJiraIssue` for `{ticket}`.
     Select the available transition whose target status has the **highest indeterminate**
     progress that is still short of the `done` category (`statusCategory.key` of `new` or
     `indeterminate`, never `done`) — e.g. "Ready for QA" / "In QA". If no such transition is
     available, do not force one; report the available options to the user and let them choose,
     or skip.
   - On `no`: continue.
   - Next steps for the user: run `sdlc-unit-test-workflow` (unit tests) then `sdlc-qa-workflow`
     (integration tests + the actual done-category Jira transition) for `{ticket}`.

---

## Plans Directory Structure

`{plans_dir}` = `{worktree_path}/development/plans/` — inside the ticket's worktree, not the main
checkout.

```
development/
└── plans/
    ├── {ticket}-implementation-plan.md   # Plan + ticket context (single source of truth)
    └── {ticket}-review.md                # Review output (created only during Phase 6)
```

**One plan file per ticket. No separate `ticket.md`.**
The plan file contains the ticket reference, branch, acceptance criteria, and all tasks — it is
the single source of truth for ticket context. `development/plans/` is git-tracked, so these files
commit and travel with `{branch_name}`. Other workflows (`sdlc-unit-test-workflow`,
`sdlc-qa-workflow`) MUST get there by resolving `{worktree_path}` for `{branch_name}` via the
`worktree-add` skill first, then reading `{plans_dir}` inside it — never by guessing a
`{project-root}`-relative path, and never from a `{run_dir}`-relative guess.
`current.md`/`status.md` under `{project-root}/.orchestration/runs/{ticket}/` are also maintained
(see **Status Artefacts** above) — they stay in the main checkout, are resumability aids read by
`workflow-status`, and are not a second copy of the plan's content.

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
- `tools/scope-check/` reports a violation (the change touches both `B2B_BE/` and
  `B2B_FE/`) — resolved only by re-planning the ticket as two bounded changes, never by
  overriding the check.
- A human decision is required that no agent can make.

On any stop: tell the user exactly where things stand and what command to run to resume. The plan file at `{plan_file}` preserves all context needed to continue in a future session; `current.md`/`status.md` (Status Artefacts, above) also reflect the stop for `workflow-status` to surface.

---

## Resuming a Stopped Run

On activation, the workflow checks whether `{plan_file}` exists. If it does, it reads the file, presents a resume/restart/view prompt, and continues from the appropriate phase. The plan file is the authoritative resume anchor for this workflow's own logic; `current.md`/`status.md` are updated alongside it so `workflow-status` stays accurate but are never the source of truth for what phase to resume into.
