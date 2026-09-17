---
name: sdlc-qa-workflow
description: QA integration testing workflow. Takes a Jira ticket key or PR URL, reads the ticket and PR diff, designs an integration test plan for QA approval, writes and runs integration tests, then reports a PASS or FAIL verdict back to Jira. Invoked by QA engineers after the developer's PR is raised. Covers integration tests only — unit tests are handled by sdlc-unit-test-workflow.
---

# SDLC QA Workflow

Orchestration rules: `.claude/STANDARDS.md`. This skill is owned by QA — not the developer who implemented the feature. It reads evidence (the PR diff and the ticket) rather than trusting the developer's claims. Human gates are stops, not suggestions.

## Conventions

- `{project-root}` is the **main clone** — never a ticket's worktree, even if this workflow
  happens to be invoked from inside one. `git rev-parse --show-toplevel` is ambiguous once
  worktrees exist; the main clone is always the first `worktree` entry in
  `git worktree list --porcelain`, run from anywhere. Resolve it once at activation.
- `{ticket}` is the Jira issue key (e.g. `PROJ-42`).
- `{run_dir}` resolves to `{project-root}/.orchestration/runs/{ticket}/`.
- `{run_record}` resolves to `{run_dir}/run-record.md`.
- `{worktree_path}` is the isolated git worktree `sdlc-dev-workflow` Phase 2 created for
  `{branch_name}` — resolve it via the `worktree-add` skill (idempotent; returns the existing path
  rather than creating anything new) before Phase 1. Every test file this workflow writes, and
  every command it runs against the implemented code, runs from `{worktree_path}`; `{run_dir}`
  stays anchored to `{project-root}`.
- `{plans_dir}` resolves to `{worktree_path}/development/plans/`. `development/plans/` is
  git-tracked, so the plan file committed by `sdlc-dev-workflow` Phase 3 travels with the branch
  into this worktree.
- `{plan_file}` resolves to `{plans_dir}/{ticket}-implementation-plan.md` — written by
  `sdlc-dev-workflow` Phase 3; the ticket's single source of truth. There is no `ticket.md`.
- `{pr_url}` is the GitHub PR URL for this ticket.
- Integration tests test **boundaries** — two or more real components working together. They do not mock everything; they mock only external services (third-party APIs, email, payments).
- A **human gate** means: stop, present the artefact, wait for explicit approval. Never reinterpret a gate as optional.
- Any `started` / `updated` / `last_updated` timestamp written to `current.md` or `status.md` is
  the real current time, captured by running `date -u +%Y-%m-%dT%H:%M:%S+00:00` — never
  approximate, and never a date-only value.

---

## Communication Style (automatic)

From activation, apply the caveman compression style (`.claude/skills/caveman/SKILL.md`, level
`full`) to every piece of conversational output this workflow produces — most valuable while
reading the PR diff and running/interpreting integration tests — automatically, for the whole
run. No `/caveman` command needed; do not wait for the user to ask. It never applies to
persisted artefacts (the test plan, `{run_record}` rows, the Jira PASS/FAIL comment) and it
auto-drops for gate prompts and irreversible-action confirmations, per that skill's own
Boundaries and Auto-Clarity rules, so it never makes a human gate ambiguous.

---

## Run Record (agent-metrics)

Schema: `.orchestration/schemas/run-record.md`. Append to the existing `{run_record}` rather
than creating a new file.

- On activation, set `State: qa` in `{run_record}` (create the file per the schema only if it
  genuinely does not exist yet — e.g. QA is on a different machine and this is the first
  workflow to touch this ticket).
- After **every** phase below completes, and after every gate reply, append one row: `Step` =
  `[qa] Phase N — Name` (or `[qa] Gate N — Name`), `Owner` = `test`, or exactly `human` for a
  gate reply, `Outcome` = `done` / `failed` / `awaiting`, `Evidence` = `commit:<sha>` /
  `exit:<code>:<test-cmd>` / `approved`, `At` = now, ISO-8601 — get the real current time by
  running `date -u +%Y-%m-%dT%H:%M:%S+00:00`; never approximate or pad to midnight.
- On QA **PASS** (Phase 4), set `State: complete` — this is the row that closes the ticket's
  whole SDLC journey across all three development-side workflows.
- On QA **FAIL** (Phase 4), keep `State: qa` and set `Next:` to name the failing tests the
  developer must fix; the next `sdlc-dev-workflow` (or direct fix) pass reopens this same
  `{run_record}` rather than starting a new one.
- Never let this slow down or gate the workflow itself. If `{run_record}` cannot be written,
  note it and continue.

---

## Status Artefacts (workflow-status)

Schema: `.orchestration/schemas/ticket-status.md`.

- After **every** phase and gate reply, update `current.md`'s five fields and `status.md`'s "You
  Are Here" section and the matching Phase Tracker row for `sdlc-qa-workflow`.
- Update this ticket's row in `.orchestration/PROJECT-STATUS.md`. While QA is in progress, keep
  it in the **Active Tickets** table (Current Workflow = `sdlc-qa-workflow`, Phase = the phase
  just reached, Waiting On = the gate question if pending, else "—"). If no row exists yet
  (invoked standalone), create one.
- **On PASS** (Phase 4): move the ticket's row from **Active Tickets** to **Completed Tickets**
  (Ticket, Summary, Branch, PR, QA Verdict = `PASS`, Completed = today's date). Remove any row
  for it from **Blocked / Needs Work** if one exists from a prior FAIL.
- **On FAIL** (Phase 4): keep the row in **Active Tickets** (Waiting On = "developer fix"), and
  add/update a row in **Blocked / Needs Work** (Blocked At = `sdlc-qa-workflow Phase 4`, Reason =
  a one-line summary of the failing ACs, Action Required = "fix failing tests, push, re-run
  `/sdlc-qa-workflow {ticket}`").
- Never let this slow down or gate the workflow itself. If these files cannot be written, note
  it and continue.

---

## On Activation

1. Ask for `{ticket}` and `{pr_url}` if not supplied.
2. **Read only `{run_dir}/current.md`** (do not read `status.md` or `PROJECT-STATUS.md` on activation). If not found (QA is on a different machine), skip and proceed directly to Phase 1.
3. If `current.md` is found, present:
   ```
   ── QA WORKFLOW: {ticket} ─────────────────────────────────────────────────────
   Workflow : {workflow}
   Phase    : {phase}
   Waiting  : {waiting}
   Next     : {next}
   ──────────────────────────────────────────────────────────────────────────────
   Reply: resume → continue | restart → start QA from Phase 1 | detail → full status
   ```
   On `detail`: read `{run_dir}/status.md` and present in full, then ask resume/restart.
   Wait for QA's reply.
4. Update `{run_dir}/current.md` — set workflow to `sdlc-qa-workflow`, phase to `Phase 1 — Feature Understanding`, status to `running`.
5. Confirm GitHub CLI access and derive `{branch_name}`: `gh pr view {pr_url} --json headRefName,baseRefName` — if this fails, ask the user for `{branch_name}` directly. `{default_branch}` is the PR's base ref from that same call, or `git remote show origin | grep "HEAD branch"` if the PR lookup failed.
6. Resolve `{worktree_path}` for `{branch_name}` via the `worktree-add` skill
   (`.claude/skills/worktree-add/SKILL.md`) — it returns the existing worktree `sdlc-dev-workflow`
   Phase 2 already created rather than making a new one. Every file this workflow reads or writes
   for this ticket (the plan file, the integration tests themselves) lives under `{worktree_path}`
   from here on, never `{project-root}`.
7. Begin at **Phase 1** (or the resume phase).

---

## The Pipeline

```
[TICKET KEY + PR URL]
        │
        ▼
  Phase 1: Feature Understanding    (Test agent)
        │   Read ticket + PR diff · understand what was built
        │
        ▼
  Phase 2: Integration Test Plan    (Test agent)
        │   Identify component boundaries · design test cases
        │
  ── GATE 2: Test Plan Approval ──────────── QA must approve before writing tests
        │
        ▼
  Phase 3: Write Integration Tests  (Test agent + bmad-build)
        │   Write tests · run them · report results
        │
        ▼
  Phase 4: QA Verdict               (orchestrator + Rovo MCP)
        │   PASS → comment on PR + transition Jira
        │   FAIL → list failures + comment on PR
        │
        ▼
  [QA COMPLETE]
```

---

## Phase 1: Feature Understanding

**Owner:** Test agent (`.claude/agents/test.md`)
**MCP tools:** `mcp__claude_ai_Atlassian_Rovo__getJiraIssue`

### Instructions

1. Call `mcp__claude_ai_Atlassian_Rovo__getJiraIssue` for `{ticket}`. Read:
   - Summary and description
   - Acceptance criteria (these become the integration test targets)
   - Linked epics or parent stories for context
2. Fetch the PR diff:
   - Run `gh pr diff {pr_url}` or `git diff {default_branch}...{branch_name}`
   - Identify which files changed and what the change does at a high level
3. Read `{plan_file}` (`{plans_dir}/{ticket}-implementation-plan.md`) if it exists — the approved plan describes intended component interactions. There is no separate `ticket.md`; the plan file's Ticket Reference section covers that.
4. Read `stack/rules/base-rules.md` for testing framework, conventions, and what counts as a component boundary in this project.
5. Produce a brief feature summary saved to `{run_dir}/qa-feature-summary.md`:
   - What the feature does (from the ticket)
   - Which components interact (from the diff)
   - What the acceptance criteria are (these map 1:1 to integration test scenarios)
6. Record `phase_1: complete` in `{run_dir}/status.md`.

---

## Phase 2: Integration Test Plan

**Owner:** Test agent (`.claude/agents/test.md`)
**Skill:** `test-design`
**Input:** `{run_dir}/qa-feature-summary.md` + PR diff
**Output:** `{run_dir}/integration-test-plan.md`

### What integration tests cover

Integration tests verify that **two or more real components work correctly together**. They are not unit tests and they are not E2E UI tests.

| ✅ Integration test targets | ❌ Not integration tests |
|---|---|
| Service layer calling a real database | Mocking the database and asserting on mock calls |
| API endpoint returning correct response for a given request | Unit test of a single function |
| Repository correctly persisting and retrieving data | Full browser/UI simulation |
| Auth middleware correctly rejecting unauthorised requests | Testing a third-party service |

### Test plan structure

For each acceptance criterion from the ticket:

```markdown
### AC{N}: {Acceptance criterion text}

**Components under test:** {Component A} ↔ {Component B}
**Test environment:** {real DB / real file system / mock external API — specify what is real vs mocked}

| Test case | Setup | Action | Expected result | Type |
|---|---|---|---|---|
| Happy path | {preconditions} | {what the test does} | {what should happen} | Integration |
| Failure: {condition} | {preconditions} | {action} | {expected failure behaviour} | Integration |
| Edge: {condition} | {preconditions} | {action} | {expected result} | Integration |
```

Rules for the Test agent:
- Every acceptance criterion must map to at least one integration test.
- Mock only: external third-party APIs, email/SMS services, payment gateways, time (use a fixed clock).
- Do not mock: your own database, your own file system, your own internal services.
- Specify the test data setup (seed data, fixtures) needed for each test.
- If the project has no integration test infrastructure yet, flag this clearly and propose the minimal setup needed.

### Gate 2 — Integration Test Plan Approval

```
── GATE 2: INTEGRATION TEST PLAN REVIEW ──────────────────────────────────────
Test plan is ready at: {run_dir}/integration-test-plan.md

Ticket:            {ticket} — {summary}
Acceptance criteria covered: {N}
Integration test cases planned: {N}

Please review. When ready, reply with one of:
  approved          → write the tests
  revise: <notes>   → Test agent revises and re-presents (one revision allowed)
  stop              → end QA here; mark ticket as Needs Work
──────────────────────────────────────────────────────────────────────────────
```

Do not write a single test until the QA replies `approved`.

---

## Phase 3: Write & Run Integration Tests

**Owner:** Test agent (`.claude/agents/test.md`)
**Skill:** `bmad-build` (one invocation per test file)
**Input:** Approved `{run_dir}/integration-test-plan.md`

All test files are created/updated and all test/build commands below run inside
`{worktree_path}` (resolved On Activation) — never in `{project-root}`.

### Instructions

1. For each acceptance criterion in the approved plan:
   - Create or update the integration test file (follow naming conventions from `stack/rules/base-rules.md`, e.g. `*.integration.test.ts`, `*_integration_test.go`).
   - Write all planned test cases.
   - Set up test data / fixtures as specified in the plan.
   - Mock only what the plan marks as external.
2. Run the integration test suite (command from `CLAUDE.md` or CI config, or discover from project):
   - If the integration test command is unknown, check: `package.json` scripts, `Makefile`, `pytest.ini`, CI workflow files.
   - Run tests and capture full output.
3. Record results in `{run_dir}/qa-results.md`:

```markdown
## QA Test Results — {ticket}

Run at: {datetime}
Branch: {branch_name}

| Test case | AC | Status | Failure message |
|---|---|---|---|
| {test name} | AC1 | PASS | — |
| {test name} | AC2 | FAIL | {error message} |

Summary:
  Total:  N
  Passed: N
  Failed: N
```

4. Record `phase_3: complete` in `{run_dir}/status.md`.

### What the Test agent must not do

- Modify source files to make tests pass.
- Skip planned test cases without flagging.
- Mark a test as passing when the assertion was never reached.
- Use real external payment/email/SMS services in tests.

---

## Phase 4: QA Verdict

**Owner:** Orchestrator (this workflow)
**MCP tools:** `mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue`, `mcp__claude_ai_Atlassian_Rovo__transitionJiraIssue`, `mcp__claude_ai_Atlassian_Rovo__getTransitionsForJiraIssue`

### On PASS (all tests pass)

1. Present verdict:

```
── QA VERDICT: PASS ───────────────────────────────────────────────────────────
All integration tests passed.

  Ticket:  {ticket}
  PR:      {pr_url}
  Tests:   {N} passed / {N} total
  Results: {run_dir}/qa-results.md

Actions:
  → Jira comment added
  → Ticket transitioned to the real terminal (done-category) Jira status
──────────────────────────────────────────────────────────────────────────────
```

2. Call `mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue`:
   > "QA PASS — {N}/{N} integration tests passed. PR: {pr_url}. Results: {run_dir}/qa-results.md"

3. Transition Jira to the real terminal status — **match by status category, not by name**:
   - Call `mcp__claude_ai_Atlassian_Rovo__getTransitionsForJiraIssue`. Status *names* vary per
     project ("Done", "Ready for UAT", "Ready for Merge", "Released" all exist across different
     Jira setups) but every one of them reports `to.statusCategory.key`, and only `"done"` means
     Jira actually counts the issue as finished — `"new"` and `"indeterminate"` do not, even when
     the status is *named* something that sounds terminal (e.g. a status literally called
     "QA Done" can still carry `statusCategory.key: "indeterminate"`).
   - Prefer any available transition whose target `statusCategory.key == "done"`. Call
     `mcp__claude_ai_Atlassian_Rovo__transitionJiraIssue` for it.
   - If no available transition leads directly to a `done`-category status, take the best
     available transition toward it (an intermediate in-progress status), then call
     `getTransitionsForJiraIssue` again from the new status and repeat — up to 3 hops total.
     Stop and report to the user if 3 hops are exhausted without reaching `done`-category, rather
     than settling for an intermediate status and calling it final.
   - Record every hop as its own `run-record.md` evidence entry (`jira:transitioned:<status
     name>`), not just the last one.
4. Update `{run_dir}/status.md` — set `qa: passed`, per **Status Artefacts** above.

### On FAIL (one or more tests fail)

1. Present verdict:

```
── QA VERDICT: FAIL ───────────────────────────────────────────────────────────
{N} integration test(s) failed.

  Ticket:  {ticket}
  PR:      {pr_url}
  Tests:   {N} passed / {N} failed / {N} total

Failed tests:
  - {test name} (AC{N}): {failure message}
  - {test name} (AC{N}): {failure message}

Full results: {run_dir}/qa-results.md

Actions:
  → Jira comment added with failure details
  → Ticket transitioned to: Needs Work
──────────────────────────────────────────────────────────────────────────────
```

2. Call `mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue` with the failure details listed above.
3. Find and call `mcp__claude_ai_Atlassian_Rovo__transitionJiraIssue` to move the ticket to "Needs Work" or equivalent — an in-progress-category status, never a `done`-category one.
4. Update `{run_dir}/status.md` — set `qa: failed`, per **Status Artefacts** above.

The developer must fix the failures and re-raise the PR. QA re-runs `/sdlc-qa-workflow {ticket}` to re-validate.

---

## Run Directory Files (QA additions)

| File | Created by | Purpose |
|---|---|---|
| `qa-feature-summary.md` | Phase 1 | Feature understanding from ticket + diff |
| `integration-test-plan.md` | Phase 2 | Approved integration test cases |
| `qa-results.md` | Phase 3 | Test run output and pass/fail per case |

---

## Stop Conditions

Bounded recovery in this workflow follows the same `status.json` + `tools/breaker-check`
convention defined in `sdlc-dev-workflow`'s "Bounded Recovery" section: on any retry, run
`tools/breaker-check/breaker-check record-attempt --run-dir {run_dir} --activity <key> --reason
"<why>" --failure-signal "<signature>" --evidence "<path>"` (never hand-edit `status.json`), then
run `tools/breaker-check/breaker-check --run-dir {run_dir} --ticket {ticket}` before proceeding; a
non-zero exit stops the retry.

- QA replies `stop` at any gate.
- PR diff cannot be fetched (ticket and PR URL not accessible).
- Integration test infrastructure does not exist and QA does not want to set it up.
- Tests cannot run after one retry (escalate, do not fake a result).

On any stop: write state to `{run_dir}/status.md`, tell the QA what to do to resume, then halt.
