---
name: sdlc-unit-test-workflow
description: Writes unit tests for already-implemented code. Takes a Jira ticket key or branch name, reads the implemented code and the approved implementation plan, designs a unit test plan for user approval, then writes and runs the unit tests. Invoked by the developer after sdlc-dev-workflow completes. Covers unit tests only — integration tests are handled by sdlc-qa-workflow.
---

# SDLC Unit Test Workflow

Orchestration rules: `.claude/STANDARDS.md`. This skill owns the unit test authoring sequence. It does not implement features — it tests already-implemented code. Human gates are stops, not suggestions.

## Conventions

- `{project-root}` is the repository root.
- `{ticket}` is the Jira issue key (e.g. `PROJ-42`).
- `{run_dir}` resolves to `{project-root}/.orchestration/runs/{ticket}/`.
- `{run_record}` resolves to `{run_dir}/run-record.md`.
- Tests are written **after** implementation — this workflow reads existing code and writes tests for it.
- A **human gate** means: stop, present the artefact, wait for explicit approval before proceeding.
- **Bounded recovery:** each phase gets one retry on failure before escalating.

---

## Run Record (agent-metrics)

Schema: `.orchestration/schemas/run-record.md`. Append to the existing `{run_record}` rather
than creating a new file.

- On activation, set `State: unit-testing` in `{run_record}` (create the file per the schema
  only if it genuinely does not exist yet — e.g. this workflow was invoked standalone).
- After **every** phase below completes, and after every gate reply, append one row: `Step` =
  `[unit-test] Phase N — Name` (or `[unit-test] Gate N — Name`), `Owner` = `test`, or exactly
  `human` for a gate reply, `Outcome` = `done` / `failed` / `awaiting`, `Evidence` =
  `commit:<sha>` / `exit:<code>:<test-cmd>` / `approved`, `At` = now, ISO-8601.
- Do not advance `State` past `unit-testing` — `sdlc-qa-workflow` is what moves it to `qa`.
- Never let this slow down or gate the workflow itself. If `{run_record}` cannot be written,
  note it and continue.

---

## On Activation

1. Ask for `{ticket}` if not supplied.
2. **Read only `{run_dir}/current.md`** (do not read `status.md` or `PROJECT-STATUS.md` on activation). If not found, ask the user for the path or branch name.
3. Present:
   ```
   ── UNIT TEST WORKFLOW: {ticket} ──────────────────────────────────────────────
   Workflow : {workflow}
   Phase    : {phase}
   Waiting  : {waiting}
   Next     : {next}
   ──────────────────────────────────────────────────────────────────────────────
   Reply: resume → continue | restart → start from Phase 1 | detail → full status
   ```
   On `detail`: read `{run_dir}/status.md` and present in full, then ask resume/restart.
   Wait for the user's reply.
4. Update `{run_dir}/current.md` — set workflow to `sdlc-unit-test-workflow`, phase to `Phase 1 — Code Reconnaissance`, status to `running`.
5. Read `{run_dir}/implementation-plan.md` and `{run_dir}/ticket.md` to understand what was built.
6. Confirm the branch is checked out: `git branch --show-current`. If not on `{branch_name}`, run `git checkout {branch_name}`.
7. Begin at **Phase 1** (or the resume phase).

---

## The Pipeline

```
[TICKET KEY or BRANCH]
        │
        ▼
  Phase 1: Code Reconnaissance   (Test agent)
        │   Read implemented files · understand what each unit does
        │
        ▼
  Phase 2: Unit Test Plan        (Test agent)
        │   Design test cases per function/method/module
        │
  ── GATE 2: Test Plan Approval ─────────── user must approve before writing tests
        │
        ▼
  Phase 3: Write Unit Tests      (Test agent + bmad-build)
        │   Write tests · run them · all must pass
        │
        ▼
  Phase 4: Commit & Push         (orchestrator)
        │   Commit gate · push gate (same rules as sdlc-dev-workflow)
        │
        ▼
  [UNIT TESTS COMPLETE — hand off to sdlc-qa-workflow for integration tests]
```

---

## Phase 1: Code Reconnaissance

**Owner:** Test agent (`.claude/agents/test.md`)
**Skill:** `test-design`
**Input:** `{run_dir}/implementation-plan.md` + all files listed in the plan's "Files to Modify / Create" sections

### Instructions

1. Invoke the Test agent. Pass it:
   - `{run_dir}/implementation-plan.md` — to understand what was implemented
   - `{run_dir}/ticket.md` — for business context
   - `stack/rules/base-rules.md` — for testing framework, coverage requirements, and conventions
2. The Test agent reads every file named in the implementation plan. For each:
   - Identifies all public functions, methods, classes, or modules.
   - Notes inputs, outputs, and side effects.
   - Identifies pure functions (easiest to unit test) vs. functions with dependencies (need mocking).
   - Notes existing test files if any (to avoid duplication).
3. Produce a reconnaissance summary saved to `{run_dir}/test-recon.md`:
   - List of units to test (function/method name + file)
   - Dependencies that will need mocking per unit
   - Existing test coverage (if any)
4. Record `phase_1: complete` in `{run_dir}/status.md`.

---

## Phase 2: Unit Test Plan

**Owner:** Test agent (`.claude/agents/test.md`)
**Skill:** `test-design`
**Input:** `{run_dir}/test-recon.md`
**Output:** `{run_dir}/unit-test-plan.md`

### Instructions

The Test agent produces a test plan with the following structure for each unit:

```markdown
### {FunctionName / MethodName}
File: {path/to/source/file}
Test file: {path/to/test/file}

| Test case | Input | Expected output | Type |
|---|---|---|---|
| Happy path | {valid input} | {expected result} | Unit |
| Edge: empty input | {} or null | {error or default} | Unit |
| Edge: boundary value | {min/max} | {expected result} | Unit |
| Error: invalid input | {bad input} | {throws / returns error} | Unit |
```

Rules for the Test agent:
- Every public function from the recon must have at least a happy path and one edge/error case.
- Do not plan tests for private/internal helpers unless they contain non-trivial logic.
- Use the testing framework specified in `stack/rules/base-rules.md`. If not yet set, note it as TBD and use the most common framework for the project's language.
- Mocking strategy: note what needs to be mocked for each unit and how.

Save the completed plan to `{run_dir}/unit-test-plan.md`.

### Gate 2 — Test Plan Approval

```
── GATE 2: UNIT TEST PLAN REVIEW ─────────────────────────────────────────────
Test plan is ready at: {run_dir}/unit-test-plan.md

Ticket:  {ticket} — {summary}
Units to test:  {N}
Test cases planned: {N}

Please review. When ready, reply with one of:
  approved            → write the tests
  revise: <notes>     → Test agent revises and re-presents (one revision allowed)
  skip: <unit name>   → exclude a specific unit from the plan, then approve
  stop                → end the workflow here
──────────────────────────────────────────────────────────────────────────────
```

Do not write a single test until the user replies `approved`.

---

## Phase 3: Write Unit Tests

**Owner:** Test agent (`.claude/agents/test.md`)
**Skill:** `bmad-build` (one invocation per test file)
**Input:** Approved `{run_dir}/unit-test-plan.md` + source files

### Instructions

1. The Test agent works through the approved plan, one source unit at a time.
2. For each unit:
   - Creates or updates the test file (follow naming convention from `stack/rules/base-rules.md`, e.g. `*.test.ts`, `*_test.go`, `Test*.java`).
   - Writes all planned test cases.
   - Sets up mocks exactly as specified in the plan — does not mock more than needed.
   - Does not modify the source file being tested.
3. After writing all tests for a unit, runs the test suite (command from `CLAUDE.md` stack table or CI config):
   - If tests pass: continue to next unit.
   - If tests fail: diagnose, fix the test (not the source), retry once. If still failing, escalate to user.
4. After all units are tested, run the full test suite one final time and report:
   - Tests run: N
   - Passed: N
   - Failed: N (list)
   - Coverage delta (if the test runner reports it)
5. Record `phase_3: complete` in `{run_dir}/status.md`.

### What the Test agent must not do

- Modify source files to make tests pass — fix the test or escalate.
- Write tests that always pass regardless of implementation (assertion-free tests, trivial equality checks).
- Skip a planned test case without flagging it to the user.
- Use real external services — mock all I/O, network, and database calls.

---

## Phase 4: Commit & Push

**Owner:** Orchestrator (this workflow)

### Commit Message Gate

After all tests are written and passing, present:

```
── COMMIT: Unit tests for {ticket} ───────────────────────────────────────────
Files staged:
  {list of test files}

Suggested commit message:
  {ticket}: add unit tests

  {N} test cases across {N} units. Coverage: {delta if known}.
  Mocks: {list of mocked dependencies}.

Reply with one of:
  use              → commit with suggested message
  edit: <message>  → commit with your message
  skip             → do not commit (you will commit manually)
──────────────────────────────────────────────────────────────────────────────
```

### Push Gate

```
── PUSH CONFIRMATION ─────────────────────────────────────────────────────────
Ready to push branch {branch_name} to origin.

Commits to be pushed:
{git log origin/{branch_name}..HEAD --oneline}

Reply with one of:
  push  → push now
  no    → skip; push manually later with: git push origin {branch_name}
──────────────────────────────────────────────────────────────────────────────
```

Never run `git commit` or `git push` without the corresponding explicit reply.

---

## Completion

After the push gate is resolved, present:

```
── UNIT TESTS COMPLETE ────────────────────────────────────────────────────────
  Ticket:        {ticket}
  Branch:        {branch_name}
  Tests written: {N} cases across {N} units
  All passing:   yes

Next step:
  Hand the PR to your QA team.
  QA runs: /sdlc-qa-workflow {ticket}
──────────────────────────────────────────────────────────────────────────────
```

Update `{run_dir}/status.md` — set `unit_tests: complete`.

---

## Stop Conditions

- User replies `stop` at any gate.
- A source file listed in the plan does not exist on disk.
- Tests cannot be made to pass after one retry (escalate, do not skip).
- Test runner command cannot be determined from project config.

On any stop: write state to `{run_dir}/status.md`, tell the user what to do to resume, then halt.
