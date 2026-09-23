# Implementation Plan — APPOINTMEN-30

## Ticket Reference

- **Jira key:** APPOINTMEN-30
- **Requirement:** FR-25 — "State an availability change in natural language." As Meena or Arjun
  (a Staff member), I can tell the Manager Agent to block or unblock my own availability in plain
  language, so I don't have to use a form.
- **Branch:** `feature/APPOINTMEN-30-31-fr-25-state-an-availability-change-in`

## Acceptance Criteria

- The agent correctly extracts, from the Staff member's free-text message:
  - which staff member the change applies to (always the speaker themselves — never parsed from
    the text),
  - which time window,
  - whether the request is a block or an unblock,
  for the demo's rehearsed happy-path phrasings (`bmad-output/planning-artifacts/ux/ux-salon-app-2026-09-17/staff-owner-manager-chat.md`
  §3: "block out Friday morning", "block out all of Friday", "unblock Saturday").

## Deviations from the original plan

The original (stale) plan for this ticket assumed no prior art existed and proposed two tasks that
are now redundant given work merged into `develop` since:

1. **APPOINTMEN-19 (FR-5)** already added `settings.anthropic_api_key` / `settings.anthropic_model`
   to `B2B_BE/app/config.py` and `B2B_BE/.env.example`, and already added `anthropic` as a
   `pyproject.toml` dependency. The original plan's "add LLM config" task is redundant — this plan
   reuses that config exactly as it exists, with no changes to `config.py`, `.env.example`, or
   `pyproject.toml`.
2. **APPOINTMEN-19 (FR-5)** also established the working extraction pattern this ticket should
   follow: `B2B_BE/app/agent/booking_intent.py` — a plain (non-async) function using the sync
   `anthropic.Anthropic` client, a forced tool-choice call whose `input_schema` is a Pydantic
   model's `model_json_schema()`, and `model_validate` on the tool-use input. This plan mirrors
   that pattern directly rather than inventing a new one.
3. **APPOINTMEN-33 (FR-27)** already added `B2B_BE/app/domain/availability.py`, which defines
   `ProposedAvailabilityChange` (`staff_name`, `start_time`, `end_time`, `blocked`,
   `confirmed: bool = False`) as the shape a proposed block/unblock change takes before an explicit
   confirmation step (Story 3.3, not this ticket) allows it to be written. The original plan's
   "define a new intent schema" task (e.g. a standalone `AvailabilityChangeIntent` /
   `AvailabilityWindow` / `AvailabilityAction` model) would duplicate this shape. This plan produces
   `ProposedAvailabilityChange` directly as FR-25's output type — no parallel schema.

Because of (1)–(3), this ticket only needs two small, additive changes: a new extraction module
that produces a `ProposedAvailabilityChange`, and a hook-point function on the Manager Agent that
wires it to the already-resolved speaker. `app/domain/availability.py`,
`app/models/availability.py`, `app/config.py`, `.env.example`, and `pyproject.toml` are untouched.

A second correction from the original plan: the LLM extraction call must never be asked for staff
identity. `ProposedAvailabilityChange.staff_name` always comes from the resolved `SpeakerContext`
(`app/agent/manager_agent.py`), never from parsed text — this is what keeps FR-30's "a staff member
cannot alter another staff member's schedule" boundary intact even if a message were phrased as
"block out Priya's Friday". The LLM-facing tool schema therefore only ever asks for
`start_time`, `end_time`, and `blocked`; `staff_name` is layered on afterward in plain Python.

## Affected Areas

| File | Change | Reason |
|---|---|---|
| `B2B_BE/app/agent/availability_intent.py` | **New** | Sync LLM extraction of `(start_time, end_time, blocked)` from a Staff member's free-text message, mirroring `booking_intent.py`'s pattern. Never asks the LLM for staff identity. |
| `B2B_BE/app/agent/manager_agent.py` | **Modify** | Add a hook-point function that combines the extraction result with the already-resolved `SpeakerContext.name` to build a fully-formed `ProposedAvailabilityChange(confirmed=False)`. |

No other file is touched. In particular, not touched: `app/domain/availability.py`,
`app/models/availability.py`, `app/config.py`, `.env.example`, `pyproject.toml`.

## Out of Scope

- **Conflict checking (FR-26).** `check_conflicts` / `app/domain/conflicts.py` is not called here.
  This ticket only produces the proposed change; conflict detection is a separate FR against a
  separate story.
- **Actual database write / confirmation flow (FR-27).** `confirm_and_apply_availability_change`
  already exists (APPOINTMEN-33) and is untouched. This ticket never sets `confirmed=True` and
  never calls that function — Story 3.3 (restate-and-confirm) is the boundary that will eventually
  produce a confirmed change and call it.
- **Restating the change back to the Staff member for confirmation (Story 3.3).** Not built here.
- **Frontend.** This is a backend-only ticket; no `B2B_FE/` changes.
- **Unrehearsed-phrasing robustness.** Per the AC and the PRD's happy-flow-only scope
  (`stack/rules/base-rules.md` — Testing Requirements), only the three rehearsed phrasings need to
  work correctly. No fuzzing, no ambiguous-phrasing handling, no clarifying-question loop.
- **Wiring this hook point into a live conversation loop / API endpoint.** As with
  `parse_booking_intent` and `resolve_speaker`, this remains a hook point a future conversational
  Manager Agent loop calls once a message and phone number are available — no new API route is
  added in this ticket.

## Task Breakdown

### Task 1 — `B2B_BE/app/agent/availability_intent.py` (new)

- Define a private, extraction-only Pydantic model (not exported as part of the domain layer) with
  exactly `start_time: datetime`, `end_time: datetime`, `blocked: bool` — no `staff_name` field, so
  the LLM is structurally incapable of supplying staff identity.
- `_TOOL_NAME` constant and `_build_tool_schema()` helper, mirroring `booking_intent.py`.
- A sync function, e.g. `parse_availability_change(text: str, *, staff_name: str, now: datetime | None = None) -> ProposedAvailabilityChange`:
  - Resolves `reference_time = now or datetime.now(UTC)`.
  - Calls `anthropic.Anthropic(api_key=settings.anthropic_api_key).messages.create(...)` with a
    system prompt giving the reference date/time and instructing the model to resolve relative
    day/window phrases ("Friday morning", "all of Friday", "Saturday") into concrete start/end
    timestamps, and to set `blocked=True` for a block request, `blocked=False` for an unblock
    request. Forces `tool_choice={"type": "tool", "name": _TOOL_NAME}`.
  - Validates the tool-use input against the private extraction model.
  - Builds and returns `ProposedAvailabilityChange(staff_name=staff_name, start_time=..., end_time=..., blocked=..., confirmed=False)`
    — `staff_name` is a plain function argument supplied by the caller (the Manager Agent hook in
    Task 2), never read from the LLM output.
- Docstring stating the FR-25 traceability and the "never asks the LLM for identity" boundary
  explicitly, matching `booking_intent.py`'s documentation style.
- No unit tests committed (per the workflow split — Test Agent owns that); a scratch,
  uncommitted smoke script exercises the three rehearsed phrasings from
  `staff-owner-manager-chat.md` §3 against a mocked Anthropic client to sanity-check parsing
  before commit.

**Validation:** `.venv/bin/python -m pytest -q`, `.venv/bin/ruff check app/agent/availability_intent.py`,
`.venv/bin/black --check app/agent/availability_intent.py`,
`.venv/bin/mypy --ignore-missing-imports app/agent/availability_intent.py`, run from `B2B_BE/`.

### Task 2 — `B2B_BE/app/agent/manager_agent.py` (modify)

- Add `build_proposed_availability_change(speaker: SpeakerContext, message: str, *, now: datetime | None = None) -> ProposedAvailabilityChange`:
  - Calls `parse_availability_change(message, staff_name=speaker.name, now=now)` from Task 1.
  - Returns the resulting `ProposedAvailabilityChange` unchanged (it is already `confirmed=False`
    and attributed to `speaker.name`).
  - Docstring stating this is the hook point a future conversational Manager Agent loop calls once
    a `SpeakerContext` has been resolved (mirrors `resolve_speaker`'s own docstring style) and once
    the message has been identified as an availability-change request.
- No change to `SpeakerContext`, `resolve_speaker`, or `describe_speaker`.

**Validation:** same four commands scoped to `app/agent/manager_agent.py`, run from `B2B_BE/`, plus
a full `pytest -q` run to confirm nothing else regressed.

Each task is committed independently and can be reviewed/reverted on its own.

## Testing Strategy

- No automated unit/integration tests are written as part of this ticket (owned by a separate
  Test-Agent workflow step, consistent with `.claude/agents` role split and the "fast mode" note in
  `MEMORY.md`).
- Pre-commit validation for each task: `pytest -q` (full suite, to catch any regression),
  `ruff check`, `black --check`, `mypy --ignore-missing-imports` on the changed file(s), all from
  `B2B_BE/`, with exit codes recorded as evidence.
- A manual, uncommitted smoke script (mocking the Anthropic client's `messages.create` the way the
  original APPOINTMEN-19 spike did) exercises the three rehearsed phrasings from
  `staff-owner-manager-chat.md` §3.1/§3.2/§3.3 to sanity-check that block/unblock and the time
  window resolve as expected before committing.

## Risks / Open Questions

- **LLM correctness on "morning" and "all of Friday" is a genuine judgment call for the model**,
  not something this code can force deterministically — the system prompt states the convention
  (e.g., "morning" = 9 AM–1 PM per the UX spec's own worked example) but ultimately relies on the
  model resolving it correctly for the demo's rehearsed phrasings, same class of risk already
  accepted for `parse_booking_intent`.
- **No conflict check runs before this point** (by design — out of scope, FR-26 is separate), so a
  `ProposedAvailabilityChange` returned here may later be rejected by a conflict check the calling
  flow performs; this ticket's job ends at producing the correctly-parsed proposal.
- **This hook point is not yet wired into a live endpoint or conversation loop** — same
  not-yet-wired state `resolve_speaker` and `parse_booking_intent` are already in; wiring is a
  separate, later integration step, not part of this ticket's AC.
