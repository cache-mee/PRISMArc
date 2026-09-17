---
ticket: "{PROJ-NNN}"
summary: "{ticket summary}"
branch: "{branch-name}"
pr_url: "{url or pending}"
started: "{ISO-8601 timestamp, e.g. 2026-09-17T14:32:05+00:00}"
last_updated: "{ISO-8601 timestamp}"
overall_status: "{planning | implementing | code-review | unit-testing | qa | complete | stopped}"
---

# Ticket Workflow Status: {PROJ-NNN}

## You Are Here

```
Current workflow : {sdlc-dev-workflow | sdlc-unit-test-workflow | sdlc-qa-workflow | complete}
Current phase    : Phase {N} — {Phase Name}
Waiting on       : {gate name, or "nothing — running" or "user: <what is needed>"}
Next action      : {exactly what needs to happen to move forward}
```

---

## Phase Tracker

### sdlc-dev-workflow (Developer)

| Phase | Status | Completed | Notes |
|---|---|---|---|
| 1 — Ticket Intake | `{pending\|complete\|skipped}` | | |
| 2 — Branch Setup | `{pending\|complete\|skipped}` | | Branch: `{branch-name}` |
| 3 — Implementation Plan | `{pending\|plan_ready\|approved\|skipped}` | | |
| 4 — Code Implementation | `{pending\|in_progress\|complete\|stopped}` | | |
| 5 — Pull Request | `{pending\|complete\|skipped}` | | PR: `{pr_url}` |
| 6 — Code Review | `{pending\|pass\|fail\|skipped}` | | |

### sdlc-unit-test-workflow (Developer — after code review passes)

| Phase | Status | Completed | Notes |
|---|---|---|---|
| 1 — Code Reconnaissance | `{pending\|complete}` | | |
| 2 — Unit Test Plan | `{pending\|plan_ready\|approved}` | | |
| 3 — Write Unit Tests | `{pending\|in_progress\|complete\|stopped}` | | Tests: {N} written, {N} passing |
| 4 — Commit & Push | `{pending\|complete\|skipped_by_user}` | | |

### sdlc-qa-workflow (QA Engineer)

| Phase | Status | Completed | Notes |
|---|---|---|---|
| 1 — Feature Understanding | `{pending\|complete}` | | |
| 2 — Integration Test Plan | `{pending\|plan_ready\|approved}` | | |
| 3 — Write & Run Tests | `{pending\|in_progress\|complete\|stopped}` | | Tests: {N} pass / {N} fail |
| 4 — QA Verdict | `{pending\|pass\|fail}` | | |

---

## Artefacts

| Artefact | Path | Status |
|---|---|---|
| Ticket data | `{run_dir}/ticket.md` | `{present\|missing}` |
| Implementation plan | `{run_dir}/implementation-plan.md` | `{draft\|approved\|missing}` |
| PR description | `{run_dir}/pr-body.md` | `{present\|missing}` |
| Code review | `{run_dir}/review.md` | `{pass\|fail\|pending\|missing}` |
| Test recon | `{run_dir}/test-recon.md` | `{present\|missing}` |
| Unit test plan | `{run_dir}/unit-test-plan.md` | `{draft\|approved\|missing}` |
| QA feature summary | `{run_dir}/qa-feature-summary.md` | `{present\|missing}` |
| Integration test plan | `{run_dir}/integration-test-plan.md` | `{draft\|approved\|missing}` |
| QA results | `{run_dir}/qa-results.md` | `{pass\|fail\|pending\|missing}` |

---

## Commits

| Task | Commit SHA | Message |
|---|---|---|

---

## Jira Transitions Log

| Transition | To Status | Result | Timestamp |
|---|---|---|---|
| Ticket intake | In Progress | | |
| PR raised | In Review | | |
| QA pass | Ready for Merge / Done | | |
| QA fail | Needs Work | | |

---

## Issues & Blockers

> Record anything that caused a stop, a retry, or a deviation from the plan.

| Phase | Issue | Resolution | Status |
|---|---|---|---|

---

## How to Resume

> This section is rewritten by the workflow each time it stops or is interrupted.

**Last state:** {What was happening when the workflow stopped or was last active}

**To resume:**
1. {Exact command or action to continue}
2. {What to check or confirm before proceeding}
3. {Which gate is pending, if any}
