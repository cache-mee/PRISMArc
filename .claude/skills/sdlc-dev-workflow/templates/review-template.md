# Code Review: {PR Title / Ticket}

> **Instructions for the reviewer agent:**
> Complete every section. Do not skip sections even if there are no findings — write "None found."
> Cite file paths and line numbers for every issue raised.
> Always perform the git diff checks before drawing conclusions.
> Severity: **CRITICAL** (block merge) · **MAJOR** (should fix) · **MINOR** (nice to fix) · **NITPICK** (style/preference)

---

## Context

| Field | Value |
|---|---|
| Jira Ticket | `{PROJ-NNN}` |
| PR / Branch | `{branch-name}` |
| PR Type | `{Feature \| Bug Fix \| Refactor \| Chore}` |
| Target Branch | `{main \| develop \| release/x.x}` |
| Implementation Plan | `{path to approved plan file}` |
| Reviewer | Reviewer Agent (automated) |

---

## 0. Pre-Review Diff Checks

> Run these before reviewing any file. Record the output summary here.

```
git status
git diff --stat {base-branch}...{feature-branch}
```

Files changed: {N}
Insertions: {+N}  Deletions: {-N}

---

## 1. Scope Validation

Extract the file/symbol list from the approved implementation plan and compare against the actual diff.

| File / Symbol | In Plan? | In Diff? | Verdict |
|---|---|---|---|
| `{path/to/file}` | Yes / No | Yes / No | `OK \| MISSING \| UNEXPECTED` |

**In-scope files with out-of-scope edits:** {List any hunks/edits inside in-scope files that the plan did not describe — e.g. unrelated refactors, formatting rewrites, extra logic.}

**Scope Verdict:** `IN SCOPE` / `OUT OF SCOPE`
{If OUT OF SCOPE: list unexpected files or hunks. If IN SCOPE: confirm all plan items were delivered.}

---

## 2. Mergeability

| Check | Status |
|---|---|
| No unresolved merge conflicts | `YES \| NO \| NEEDS CHECK` |
| No breaking changes to public interfaces/contracts | `YES \| NO \| NEEDS CHECK` |
| No dependency version bumps without justification | `YES \| NO \| NEEDS CHECK` |
| No debug code, hardcoded secrets, or leftover TODOs in critical paths | `YES \| NO \| NEEDS CHECK` |
| Build and lint pass (no obvious compilation errors) | `YES \| NO \| NEEDS CHECK` |

**Verdict:** `SAFE TO MERGE` / `BLOCKED — {reason}`

---

## 3. Code Issues

> For each issue: `[SEVERITY] path/to/file:line — description and why it matters`

### Logic & Correctness
- {e.g. [MAJOR] `src/service/booking.ts:88` — off-by-one in date range check; last day of range is excluded}

### Error Handling & Edge Cases
- {e.g. [CRITICAL] `src/api/client.ts:42` — network timeout not caught; caller will receive an unhandled rejection}

### Code Quality & Readability
- {e.g. [MINOR] `src/utils/format.ts:15` — magic number 86400 should be a named constant `SECONDS_PER_DAY`}

### Duplication & Abstractions
- {e.g. [MINOR] — date-formatting logic duplicated in three files; extract to a shared utility}

### Adherence to Coding Rules (`stack/rules/base-rules.md`)
- {Note any deviations from the project's established patterns, naming conventions, or architecture constraints}

---

## 4. Security

| Area | Finding |
|---|---|
| Input validation | {Are all external inputs validated before use?} |
| Data exposure | {Are sensitive fields — tokens, PII, keys — logged, serialised insecurely, or passed in URLs?} |
| Authentication / Authorisation | {Are permission checks present where required?} |
| Secrets handling | {Are secrets read from environment / secret store, not hardcoded?} |
| Unsafe patterns | {Any use of eval, unsafe deserialization, unparameterised queries, or known-insecure APIs?} |

---

## 5. Performance

| Area | Finding |
|---|---|
| Blocking operations | {Any heavy I/O, DB queries, or network calls on the main/UI thread?} |
| Resource cleanup | {Are file handles, connections, and streams always closed?} |
| Unnecessary allocations | {Any allocations inside hot loops, render loops, or tight callbacks?} |
| Caching | {Are repeated expensive calls cached where appropriate?} |

---

## 6. Testing

| Check | Status | Notes |
|---|---|---|
| New code is covered by unit tests | `YES \| PARTIAL \| NO` | |
| Edge cases (null, empty, error) are tested | `YES \| PARTIAL \| NO` | |
| Integration tests present where appropriate | `YES \| N/A \| NO` | |
| Existing tests still pass (no silent breakage) | `YES \| UNKNOWN \| NO` | |
| Coverage adequate for risk level of change | `YES \| PARTIAL \| NO` | |

**Missing tests:** {List specific scenarios that are untested but should be.}

---

## 7. Documentation

| Check | Status |
|---|---|
| Public APIs / interfaces are documented | `YES \| PARTIAL \| N/A` |
| README / docs updated where behaviour changed | `YES \| NO \| N/A` |
| Inline comments present for non-obvious logic | `YES \| NO \| N/A` |

---

## 8. Recommendations

Up to 5 concrete, prioritised improvements not covered above.

- `[P1]` {Action} — {one-line rationale}
- `[P2]` {Action} — {one-line rationale}
- `[P3]` {Action} — {one-line rationale}

---

## 9. Root Cause Analysis *(Bug fixes only — skip for features/refactors)*

**Root Cause Category:**
1. Configuration/Build · 2. Improper Communication · 3. Ineffective Analysis ·
4. Knowledge Gap · 5. Standards Not Followed · 6. Oversight ·
7. Requirement/Design Ambiguity · 8. Missing Guidelines

**Selected:** `{N — Label}`
**Description:** {What went wrong and how it was introduced.}
**Fix:** {How this PR resolves it and prevents recurrence.}

---

## Summary

**Scope Verdict:** `IN SCOPE` / `OUT OF SCOPE`
**Mergeability:** `SAFE TO MERGE` / `BLOCKED`

**Issue counts:**
| Severity | Count |
|---|---|
| CRITICAL | {N} |
| MAJOR | {N} |
| MINOR | {N} |
| NITPICK | {N} |

**Overall verdict:** `PASS` / `FAIL — address CRITICAL and MAJOR issues before merge`

---

*Generated by sdlc-dev-workflow Reviewer · Ticket: `{PROJ-NNN}` · Branch: `{branch-name}`*
