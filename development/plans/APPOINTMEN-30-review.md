# Code Review: APPOINTMEN-30 — State an availability change in natural language (FR-25)

> Reviewer Agent, independent of the implementer. All commands below were re-run
> personally in this session; none of the developer's reported results were
> accepted without independent re-execution.

---

## Context

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-30` |
| PR / Branch | `feature/APPOINTMEN-30-31-fr-25-state-an-availability-change-in` |
| PR Type | Feature |
| Target Branch | `develop` (origin/develop, per task instructions — not `main`) |
| Implementation Plan | `development/plans/APPOINTMEN-30-implementation-plan.md` |
| Reviewer | Reviewer Agent (automated) |

---

## 0. Pre-Review Diff Checks

Commands actually run, from the worktree root:

```
git fetch origin develop
git diff --stat origin/develop...feature/APPOINTMEN-30-31-fr-25-state-an-availability-change-in
```

Output:

```
 B2B_BE/app/agent/availability_intent.py            | 105 ++++++++++++++
 B2B_BE/app/agent/manager_agent.py                  |  26 ++++
 development/plans/APPOINTMEN-30-implementation-plan.md | 156 +++++++++++++++++++++
 3 files changed, 287 insertions(+)
```

Files changed: 3
Insertions: +287  Deletions: 0

`git status --porcelain=v1` in the worktree returned no output — clean tree, no
stray uncommitted scratch files left behind (consistent with the plan's claim
that the manual smoke script was uncommitted and not part of the change).

---

## 1. Scope Validation

| File / Symbol | In Plan? | In Diff? | Verdict |
|---|---|---|---|
| `B2B_BE/app/agent/availability_intent.py` (new) | Yes | Yes | OK |
| `B2B_BE/app/agent/manager_agent.py` — `build_proposed_availability_change` (modify) | Yes | Yes | OK |
| `development/plans/APPOINTMEN-30-implementation-plan.md` | Implicit (plan artifact itself) | Yes | OK |
| `app/domain/availability.py`, `app/models/availability.py`, `app/config.py`, `.env.example`, `pyproject.toml` (explicitly declared untouched) | N/A (declared out of scope) | Not in diff | OK — confirmed untouched |

**In-scope files with out-of-scope edits:** None found. Both changed files contain
exactly the additions the plan describes and nothing else.

**Scope Verdict:** `IN SCOPE` — all plan items delivered, no unplanned files or hunks.

**Repository layout check (CLAUDE.md):** All touched application files are under
`B2B_BE/`. This is a backend-only ticket (FR-25, agent extraction logic, no UI).
No `B2B_FE/` files touched. No new top-level application folder created.

**Scope-check tool (mechanical enforcement, re-run independently):**

```
$ tools/scope-check/scope-check --base origin/develop --head feature/APPOINTMEN-30-31-fr-25-state-an-availability-change-in
[custom tool] scope-check
PASS scope-check (3 file(s) touched, backend)
Exit code: 0
```

No override — this matches CLAUDE.md's repository-layout rule; a FAIL here would
have forced FAIL overall regardless of anything else, and it did not occur.

---

## 2. Mergeability

| Check | Status |
|---|---|
| No unresolved merge conflicts | YES (`git diff origin/develop...HEAD` applies cleanly, diff is purely additive) |
| No breaking changes to public interfaces/contracts | YES — `ProposedAvailabilityChange` is consumed with its existing field names/types unchanged; `SpeakerContext`/`resolve_speaker`/`describe_speaker` untouched |
| No dependency version bumps without justification | YES — `pyproject.toml` untouched, confirmed by diff stat |
| No debug code, hardcoded secrets, or leftover TODOs in critical paths | YES — reviewed both files in full, none found |
| Build and lint pass (no obvious compilation errors) | YES for ruff/black; mypy has one error — see §6/§3 below, confirmed pre-existing, not introduced by this change |

**Verdict:** `SAFE TO MERGE`

---

## 3. Code Issues

### Logic & Correctness
- None found. `parse_availability_change` mirrors `parse_booking_intent`'s
  reference-time resolution, sync Anthropic client construction, forced
  `tool_choice`, and `model_validate`-then-reshape pattern faithfully
  (`B2B_BE/app/agent/availability_intent.py:76-105` vs.
  `B2B_BE/app/agent/booking_intent.py:80-108`).
- `build_proposed_availability_change` (`B2B_BE/app/agent/manager_agent.py:47-65`)
  correctly threads `speaker.name` in as `staff_name` and passes `message`/`now`
  straight through; return value is unmodified from `parse_availability_change`,
  matching the plan's stated intent (no double-wrapping, no extra `confirmed`
  toggling).

### Error Handling & Edge Cases
- None found as CRITICAL/MAJOR. `tool_use = next(block for block in response.content if block.type == "tool_use")` at
  `availability_intent.py:96` will raise an unhandled `StopIteration` if the
  forced-tool-choice call somehow returns no tool-use block. This is not a new
  risk introduced by this ticket — it is the identical pattern already present,
  unguarded, in `booking_intent.py:99`, so it is a pre-existing class of risk
  this change deliberately mirrors rather than a new defect. Recorded as a risk
  below, not a blocking finding, per the review's scope boundary (pre-existing
  issues outside the change are not blocking unless materially worsened, and
  this change does not worsen it — it replicates the exact same shape).

### Code Quality & Readability
- None found. Naming, docstring style, and structure closely track
  `booking_intent.py`.

### Duplication & Abstractions
- None found. The plan's stated goal — reuse `ProposedAvailabilityChange`
  rather than defining a parallel schema — is honored: `availability_intent.py`
  imports `ProposedAvailabilityChange` from `app.domain.availability` (line 7)
  and constructs it with its real field names (`staff_name`, `start_time`,
  `end_time`, `blocked`, `confirmed`), verified against the actual class
  definition in `B2B_BE/app/domain/availability.py:20-32`. No shadow/duplicate
  type was introduced.

### Adherence to Coding Rules (`stack/rules/base-rules.md`)
- None found beyond what's noted elsewhere. Pattern consistency with
  `booking_intent.py` (sync client, `_TOOL_NAME` constant, `_build_tool_schema()`
  helper, forced `tool_choice`, docstring style referencing the FR number) is
  intact — see side-by-side comparison in "Style/pattern consistency" below.

---

## 4. Security

| Area | Finding |
|---|---|
| Input validation | The free-text message is passed to the LLM as message content; the response is validated through Pydantic (`_ExtractedAvailabilityWindow.model_validate`) before use. Consistent with the existing `booking_intent.py` pattern. |
| Data exposure | None found. No secrets, tokens, or PII are logged or embedded in URLs. |
| Authentication / Authorisation — **the specifically-flagged FR-30 boundary check** | **Verified true in code, not just claimed.** `_ExtractedAvailabilityWindow` (`availability_intent.py:12-43`) declares exactly `start_time`, `end_time`, `blocked` — no `staff_name` or any identity-shaped field. The tool's `input_schema` is `_ExtractedAvailabilityWindow.model_json_schema()` (line 50), so the LLM-facing tool schema is structurally incapable of returning a staff identity. The system prompt (lines 82-89) instructs the model only on date/window resolution and block/unblock semantics — it never asks for or mentions a staff name. `staff_name` is supplied exclusively as a plain Python keyword argument (`staff_name: str` at line 57) sourced from `build_proposed_availability_change`'s `speaker: SpeakerContext` parameter (`manager_agent.py:47-65`), which in turn comes from the already-resolved `SpeakerContext` (`resolve_speaker`, unmodified). There is no code path by which text in `message`/`text` can influence `ProposedAvailabilityChange.staff_name`. This confirms the plan's claimed design constraint is real, not aspirational. |
| Secrets handling | YES — reuses `settings.anthropic_api_key` (`app/config.py:11`, pre-existing from APPOINTMEN-19) via `settings.anthropic_api_key` at `availability_intent.py:77`. No new secret, no hardcoded key, no new config field added. `settings.anthropic_model` (`app/config.py:12`) is likewise reused unchanged at line 79. |
| Unsafe patterns | None found. No `eval`, no unsafe deserialization, no string-built queries (no DB access at all in this module — by design, per the plan's stated out-of-scope). |

---

## 5. Performance

| Area | Finding |
|---|---|
| Blocking operations | `parse_availability_change` makes a synchronous, blocking Anthropic API call (`client.messages.create(...)`), same as `parse_booking_intent`. This is an existing accepted pattern in this codebase for hook-point functions not yet wired into an async request path — not a new risk this ticket introduces. |
| Resource cleanup | N/A — no file handles/streams/connections opened. |
| Unnecessary allocations | None found. |
| Caching | N/A — matches existing `booking_intent.py` behavior (no caching there either); not a regression. |

---

## 6. Testing

| Check | Status | Notes |
|---|---|---|
| New code is covered by unit tests | `NO` | No unit tests were added for `availability_intent.py` or `build_proposed_availability_change`. Per the implementation plan's "Testing Strategy" section and the standing hackathon-time-constraint fast-mode override recorded in project memory, this is an explicit, declared deferral to a separate Test-Agent workflow step — not an oversight. Not treated as a CRITICAL/blocking finding for that reason, per the task's explicit instruction, but recorded factually here as `NO`. |
| Edge cases (null, empty, error) are tested | `NO` | Same reason as above — no tests exist to test them. The unguarded `next(...)` on a possibly-empty tool-use generator (see §3) is untested but mirrors an already-accepted, untested risk in `booking_intent.py`. |
| Integration tests present where appropriate | `N/A` | None exist for this hook point, consistent with `parse_booking_intent`/`resolve_speaker`'s own current untested, not-yet-wired state. |
| Existing tests still pass (no silent breakage) | `YES` | Personally re-ran `pytest -q` from `B2B_BE/` — see §Validation Commands below; exit code 0, 1 passed, 1 skipped, no failures. |
| Coverage adequate for risk level of change | `PARTIAL` | Deferred by design (see above); acceptable under the stated hackathon fast-mode override but a genuine gap that should be closed before this hook point is wired into a live conversation loop. |

**Missing tests (recorded, not blocking):**
- Happy-path extraction for the three rehearsed phrasings ("block out Friday morning", "block out all of Friday", "unblock Saturday") against a mocked Anthropic client — the plan describes this as a manual, uncommitted smoke script, not a committed automated test.
- `build_proposed_availability_change` wiring test asserting `staff_name` always equals `speaker.name` regardless of message content (the FR-30 boundary) — this is the single highest-value test to add given it's the security-relevant invariant.
- Behavior when the tool-use response contains no tool_use block (`StopIteration` path).

---

## 7. Documentation

| Check | Status |
|---|---|
| Public APIs / interfaces are documented | YES — both `parse_availability_change` and `build_proposed_availability_change` have full docstrings stating FR traceability, the identity-boundary rationale, and hook-point status, matching `booking_intent.py`/`resolve_speaker`'s documentation style. |
| README / docs updated where behaviour changed | N/A — no user-facing behavior change yet (not wired into any endpoint). |
| Inline comments present for non-obvious logic | YES — `_ExtractedAvailabilityWindow`'s docstring explicitly explains why no `staff_name` field exists. |

---

## 8. Recommendations

- `[P1]` Add a unit test asserting `build_proposed_availability_change`'s `staff_name` always equals `speaker.name` even when `message` names a different staff member (e.g. "block out Priya's Friday") — this is the FR-30 boundary and is currently only enforced by the type shape, not verified by any test.
- `[P2]` Add a mocked-client unit test covering the three rehearsed phrasings from `staff-owner-manager-chat.md` §3, converting the plan's uncommitted manual smoke script into a committed automated test (owned by the Test-Agent step per the plan, but flagged here so it isn't lost).
- `[P3]` Consider guarding the `next(block for block in response.content if block.type == "tool_use")` call in both `availability_intent.py` and (pre-existing) `booking_intent.py` with an explicit error instead of relying on `StopIteration` — cosmetic/robustness improvement, not scoped to this ticket since it mirrors existing code.

---

## 9. Root Cause Analysis

N/A — this is a feature addition, not a bug fix. Skipped per template instructions.

---

## Summary

**Scope Verdict:** `IN SCOPE`
**Mergeability:** `SAFE TO MERGE`

**Issue counts:**
| Severity | Count |
|---|---|
| CRITICAL | 0 |
| MAJOR | 0 |
| MINOR | 0 |
| NITPICK | 0 |

(The unguarded `next(...)` call and the missing-tests gap are recorded as a
**risk** and a **factual testing gap** respectively, not as MAJOR/MINOR
defects — both are pre-existing patterns this change faithfully mirrors rather
than newly introduces, and the missing-tests gap is an explicitly authorized
deferral per the task's own instructions.)

**Overall verdict:** `PASS`

---

## Validation Commands — Personally Re-Run (Evidence, Not Claims)

All commands below were executed by the Reviewer in this session, from
`/Users/riyashassank/Documents/worktrees-Hackathon-2026/APPOINTMEN-30-31-fr-25-state-an-availability-change-in`.

| Command | Exit Code | Result |
|---|---|---|
| `tools/scope-check/scope-check --base origin/develop --head feature/APPOINTMEN-30-31-fr-25-state-an-availability-change-in` | **0** | `PASS scope-check (3 file(s) touched, backend)` |
| `cd B2B_BE && .venv/bin/python -m pytest -q` | **0** | `1 passed, 1 skipped, 1 warning` — no regressions |
| `cd B2B_BE && .venv/bin/ruff check app/agent/availability_intent.py app/agent/manager_agent.py` | **0** | `All checks passed!` |
| `cd B2B_BE && .venv/bin/black --check app/agent/availability_intent.py app/agent/manager_agent.py` | **0** | `All done! 2 files would be left unchanged.` |
| `cd B2B_BE && .venv/bin/mypy --ignore-missing-imports app/agent/availability_intent.py app/agent/manager_agent.py` | **1** | One `call-overload` error at `availability_intent.py:78` on `client.messages.create(...)` |

**Discrepancy check on the developer's mypy claim:** The developer reported that
the mypy overload error is pre-existing, inherited from mirroring
`booking_intent.py`'s exact pattern, and reproduces identically against the
untouched `booking_intent.py`. This was independently re-verified rather than
accepted:

```
$ .venv/bin/mypy --ignore-missing-imports app/agent/booking_intent.py
app/agent/booking_intent.py:82: error: No overload variant of "create" of "Messages" matches argument types ... [call-overload]
Found 1 error in 1 file (checked 1 source file)
Exit code: 1
```

This is the identical error shape (same overload-mismatch message, same
`Messages.create` call site pattern) on `booking_intent.py`, which `git diff
origin/develop -- app/agent/booking_intent.py` confirms is byte-for-byte
unchanged by this branch. **The claim holds: this is a pre-existing issue in
the Anthropic SDK's type stubs interacting with this call pattern, not
something newly introduced by this ticket.** It is not attributed as a defect
of this change. It is, however, worth noting as a standing repository-wide
mypy gap outside this ticket's scope — recorded here for visibility, not as a
blocking finding.

---

## What Was NOT Reviewed

- `B2B_BE/app/domain/availability.py`, `app/models/availability.py`,
  `app/config.py`, `.env.example`, `pyproject.toml` — read only to confirm they
  are correctly unmodified and to verify integration correctness; not
  re-reviewed as if newly authored (they landed via other, already-merged
  tickets: APPOINTMEN-19, APPOINTMEN-33).
- `B2B_BE/app/agent/booking_intent.py` — read as the reference pattern and used
  to independently reproduce the mypy discrepancy check; not re-reviewed as
  part of this change's own defect surface, since it is untouched by this diff.
- Any `B2B_FE/` files — out of scope by classification; not browsed, per
  CLAUDE.md's repository-layout rule.
- The actual behavior of the LLM against live Anthropic API calls for the three
  rehearsed phrasings — no live or mocked smoke test was re-run by the
  Reviewer (the plan describes this as an uncommitted, developer-side sanity
  check, and no committed test exists to re-run deterministically). This is
  recorded as a testing gap in §6, not silently assumed to work.
- Wider repository mypy health beyond the two changed files (i.e., whether
  other files in the repository have unrelated mypy errors) — out of scope per
  the review's boundary of reviewing the change, not the whole repository.

---

*Generated by sdlc-dev-workflow Reviewer · Ticket: `APPOINTMEN-30` · Branch: `feature/APPOINTMEN-30-31-fr-25-state-an-availability-change-in`*
