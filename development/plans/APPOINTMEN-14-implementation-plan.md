# Implementation Plan: LLM Provider Integration via litellm (generic provider abstraction)

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-14` |
| Type | `Chore` |
| Branch | `feature/APPOINTMEN-14-llm-provider-integration` |
| Assigned to | sparc.team18@experionglobal.com |

---

## Overview

Introduce a small, provider-agnostic LLM abstraction — `LLMProvider` (a `Protocol`), `ToolCall`,
`LLMResponse`, and a `litellm`-backed implementation, `LiteLLMProvider` — under a new
`app/agent/providers/` package, and migrate all three existing direct LLM call sites —
`parse_booking_intent()` in `B2B_BE/app/agent/booking_intent.py`,
`is_catalog_change_request()` in `B2B_BE/app/agent/catalog_intent.py`, and
`parse_availability_change()` in `B2B_BE/app/agent/availability_intent.py` — onto it, replacing
each one's hardcoded `anthropic.Anthropic(...)` client construction and Anthropic-native tool
schema with a general `generate(*, system, messages, tools) -> LLMResponse` call that works the
same way regardless of which provider/model is configured. Provider and model are inferred from a
single config value (a provider-prefixed model string, e.g. `anthropic/claude-haiku-4-5-20251001`),
not hardcoded and not split across a separate provider setting.

**Amendment (post-Gate-3, during Task 1):** the original plan and its revision both stated
`booking_intent.py` was "the one existing direct LLM call site." That was verified wrong during
Task 1 implementation: `catalog_intent.py` and `availability_intent.py` follow the identical
`anthropic.Anthropic(api_key=settings.anthropic_api_key)` / `settings.anthropic_model` /
forced-tool-call pattern and were about to be silently broken by Task 1's config field removal (4
tests in `tests/test_catalog_intent.py` already fail on this branch as a result;
`availability_intent.py` has no test coverage so it would fail silently). Presented to the user as
a stop-and-escalate decision per this ticket's own "design decision needed mid-implementation" rule;
the user chose to widen this ticket rather than alias the old fields or defer to a follow-on ticket.
Task 4 below covers the two newly-discovered call sites, mirroring Task 3 exactly since both follow
the same pattern `booking_intent.py` did.

This is a wider shape than a single-purpose "call one forced tool" helper: `generate()` takes a
full `messages` list and an OpenAI-function-calling-shaped `tools` list, and returns zero or more
`ToolCall`s, which is what makes it a real seam for a future multi-turn agent loop rather than a
one-off shim for today's single call site. Only the seam and its one real caller are built now —
no multi-turn loop, no cross-tool dispatcher, no non-Anthropic live verification (see Out of
Scope).

---

## Business Context

**Revision note (Gate 3 plan-revision cycle):** the previous version of this plan scoped a narrow
`call_llm_with_tool()` helper shaped only for a single forced tool call. The user reviewed that
plan against a more general provider-abstraction design they had already worked out
(`LLMProvider`/`ToolCall`/`LLMResponse`/`LiteLLMProvider`, a `generate()` seam meant to outlive this
one caller) and explicitly asked to widen this ticket's scope now, rather than defer the wider
shape to a later ticket. Everything below reflects that widened design. This is the one allowed
revision before the plan returns to the user for a second approval.

This ticket's Jira key (`APPOINTMEN-14`) is administratively reused from an unrelated,
already-completed story ("1.2 FR-1: Web Chat customer identity resolution", now Ready for UAT
under a different branch). **The Jira ticket's description and acceptance criteria are not the
scope of this plan and are ignored entirely.** The actual scope comes verbatim from the user:

> "This chat needs a llm integration. Use litellm so that a generic handler is built for all AI
> providers."

The underlying motivation (inferred from `stack/rules/base-rules.md`'s own statement that "LLM
provider is not locked... pin the specific model/provider in a config value") is that the codebase
currently has exactly one LLM call, and it is hardcoded to the Anthropic SDK end-to-end (client
construction, Anthropic-native `tool_choice`/`tools` shape, Anthropic-native response parsing).
That is a correctness risk against the stack's own stated intent, and it means there is no reusable
call path for any future LLM use in the agent layer (e.g. the Booking/Manager Agent's own
reasoning loop, when that gets wired up). This ticket fixes both: it makes the provider swappable
via one config value, and it gives the codebase one reusable, general call path — not a
special-cased one — for that future reuse.

---

## Technical Context

**Verified against the current worktree (this revision re-read the following rather than trusting
the previous plan's summaries):** `app/agent/booking_intent.py` (the only LLM call site),
`app/config.py` (`Settings`, pydantic-settings), `app/agent/booking_agent.py` and
`manager_agent.py` (neither calls `parse_booking_intent` yet — both remain hook points, unchanged
by this ticket), and `app/tools/*.py` (`services.py`, `staff.py`, `customers.py` — each is a
standalone async function with its own Pydantic argument/response models; there is no existing
tool-name-to-callable dispatch registry anywhere in `app/tools/`, so "already-covered
infrastructure" does not apply here — see Out of Scope for why building one is still not this
ticket's job).

**Approach:** Add `app/agent/providers/` with two modules:

- `base.py` — the provider-agnostic types and interface:
  - `ToolCall` — one resolved tool invocation (`id`, `name`, `args: dict`).
  - `LLMResponse` — one model turn's result (`text: str | None`, `tool_calls: list[ToolCall]`,
    `raw_message: dict`). `tool_calls` may be empty (no tool invoked) or contain more than one —
    the shape does not assume "exactly one forced tool call", even though today's one caller only
    ever uses the first element.
  - `LLMProvider` — a `Protocol` with one method: `async def generate(*, system: str,
    messages: list[dict], tools: list[dict]) -> LLMResponse`. `tools` is the OpenAI
    function-calling shape (`{"type": "function", "function": {"name", "description",
    "parameters"}}`) — the same shape `litellm` normalizes every provider's tool-calling request
    to, so a future non-`litellm` provider implementation could still satisfy this same
    `Protocol` without changing any caller.
  - Final choice of plain classes (as sketched by the user) vs. `pydantic.BaseModel` for
    `ToolCall`/`LLMResponse` is an implementation-time decision, not fixed by this plan — these are
    internal data-transfer types between this module and its one caller, not an LLM-facing or
    HTTP-facing schema, so `base-rules.md`'s "schemas are Pydantic models" rule (aimed at
    tool/API/LLM schemas) does not mandate either choice here.
- `litellm_provider.py` — `LiteLLMProvider(model: str, api_key: str | None)` implementing
  `LLMProvider.generate()` by calling `litellm.acompletion(model=self.model, api_key=self.api_key,
  messages=[{"role": "system", "content": system}, *messages], tools=tools)`, then mapping
  `response.choices[0].message` into an `LLMResponse` (`tool_calls` built from
  `message.tool_calls`, parsing each `function.arguments` JSON string into a `dict`; `raw_message`
  from `message.model_dump()`). Raises a clear, specific exception (not a bare `except:`, per
  `base-rules.md`) if `litellm.acompletion` itself raises, rather than swallowing it — this module
  does not decide what "no tool call" means for a caller (see Task 3: that judgment stays in
  `parse_booking_intent`, the caller that actually requires a tool call today).

`litellm` (https://github.com/BerriAI/litellm) exposes a single `completion()`/`acompletion()`
interface across Anthropic, OpenAI, Azure, Gemini, Grok, etc. and infers the provider from a
`provider/model` prefix in the model string (its own established convention, e.g.
`anthropic/claude-haiku-4-5-20251001`, `gemini/gemini-1.5-pro`, `xai/grok-2`) — this is what
replaces a separate `llm_provider` config field: the provider is a property of the model string,
not a second setting that could drift out of sync with it.

**Why litellm does not violate the "no heavyweight agent-orchestration framework" rule
(`base-rules.md`, Architecture Constraints → Forbidden, and Dependency Policy):** that rule targets
LangChain-style **chains/graphs** — frameworks that own multi-step reasoning, memory, and
tool-execution orchestration on the framework's terms. `litellm` does none of that: it is a
same-process, single-call translation shim (request in → provider-native HTTP call → normalized
response out), functionally equivalent to swapping which SDK's `.create()`/`.messages.create()` you
call. `LiteLLMProvider.generate()` still returns control to its caller after exactly one model turn
— it does not loop, dispatch tools, or retry internally. The codebase's own caller
(`booking_intent.py` today) still owns the one tool-call round trip end to end, exactly as the
"thin, direct call to the LLM provider's native tool-calling API is required instead" rule
describes, just going through one normalized entry point instead of a provider SDK. This is a
judgment call worth the user's explicit sign-off at plan approval, not something to assume silently
— flagging it here for that reason.

**Module placement — `app/agent/providers/`, not a new top-level folder:** the previous version of
this plan placed a single `app/agent/llm.py` module directly under the existing `app/agent/`
package. This revision instead adds `app/agent/providers/` (a sub-package of `app/agent/`, still no
new top-level folder under `B2B_BE/app/` — `base-rules.md`'s Architecture Constraints only require
an Architect decision for a *new top-level folder*, and `app/agent/` is already in the enforced
tree). A sub-package is the better fit here specifically because the widened design has two
genuinely separate concerns — a provider-agnostic interface (`base.py`) and one concrete
implementation of it (`litellm_provider.py`) — where a flat `llm.py` would have mixed both into one
file; splitting them is what actually makes "swap the implementation without touching the
interface or its caller" true in practice, not just in name. The only current call site is
agent-layer code, and the named future-reuse case (a Booking/Manager Agent reasoning loop) is also
agent-layer code, so `app/agent/` remains the right parent package. If a non-agent consumer (e.g. a
`domain/` or `tools/` module) needs this later, that is the trigger to revisit placement as a real
Architect decision, not now.

**Config detail — one generic model+key pair, not per-provider fields:** `app/config.py`'s
`Settings` (pydantic-settings) gains `llm_model: str` (a provider-prefixed model string, default
`"anthropic/claude-haiku-4-5-20251001"`) and `llm_api_key: str | None = None`, replacing
`anthropic_model` and `anthropic_api_key` outright — not adding a third `llm_provider` field or a
second `openai_api_key` field alongside them, as the previous version of this plan did. One
model string plus one matching key is sufficient because the provider is read from the model
string's prefix (`litellm`'s own convention, see Technical Context above), and this codebase has
exactly one active provider/key pair configured at a time — there is no scenario yet where two
providers' keys need to be held simultaneously. `Settings` continues to read from `.env` via
pydantic-settings, not `os.environ` directly, and `LiteLLMProvider` is constructed with
`api_key=settings.llm_api_key` passed explicitly (not relying on `litellm`'s
`ANTHROPIC_API_KEY`/`OPENAI_API_KEY` environment auto-discovery, which would not see values
`Settings` parsed from `.env` unless the process happens to also export same-named env vars) — same
reasoning the previous plan version already established for this project's `Settings` pattern.

**Assumption flagged for implementation-time verification:** the tool-calling response shape
described above (`response.choices[0].message.tool_calls[i].function.name` /
`.function.arguments` as a JSON string, OpenAI-style) reflects `litellm`'s documented/established
behavior, but must be confirmed against the actual pinned `litellm` version once installed — this
plan does not install or run anything, so it is not yet verified from a live call. Task 2 records
this as an explicit check to make before writing `LiteLLMProvider`'s extraction logic.

**Testing infrastructure gap found during this revision:** `B2B_BE/tests/` currently has no
`async def test_...` function anywhere and `pyproject.toml`'s `dev` extras do not include
`pytest-asyncio` (or an `anyio` marker configuration) — there is no existing async-test convention
to "match" as the original plan assumed there might be. `LiteLLMProvider.generate()` (Task 2) is
the first genuinely async unit-testable function this ticket introduces, so Task 2 must add
`pytest-asyncio` (or equivalent) to the `dev` extra and configure it (e.g. `asyncio_mode = "auto"`
in `pyproject.toml`'s `[tool.pytest.ini_options]`), rather than assuming an overlooked existing
setup. Task 3's tests for `parse_booking_intent` then reuse that same setup.

---

## Affected Areas

| Area | Change Type | Reason |
|---|---|---|
| `B2B_BE/pyproject.toml` | Modify | Add `litellm` dependency; add `pytest-asyncio` (or equivalent) to `dev` extras; remove `anthropic` direct dependency once confirmed no longer needed |
| `B2B_BE/app/config.py` | Modify | Replace `anthropic_api_key`/`anthropic_model` with a single `llm_model`/`llm_api_key` pair |
| `B2B_BE/.env.example` | Modify | Rename `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` to `LLM_API_KEY`/`LLM_MODEL` |
| `B2B_BE/app/agent/providers/__init__.py` | New | Package marker, matching `app/agent/`'s and `app/tools/`'s existing convention |
| `B2B_BE/app/agent/providers/base.py` | New | `ToolCall`, `LLMResponse`, `LLMProvider` protocol |
| `B2B_BE/app/agent/providers/litellm_provider.py` | New | `LiteLLMProvider`, the `litellm.acompletion()`-backed implementation of `LLMProvider` |
| `B2B_BE/app/agent/booking_intent.py` | Modify | Replace direct Anthropic SDK usage with a call through `app/agent/providers/`; becomes `async def` |
| `B2B_BE/app/agent/catalog_intent.py` | Modify | Replace direct Anthropic SDK usage with a call through `app/agent/providers/`; `is_catalog_change_request` becomes `async def` |
| `B2B_BE/app/agent/availability_intent.py` | Modify | Replace direct Anthropic SDK usage with a call through `app/agent/providers/`; `parse_availability_change` becomes `async def` |

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: Add `litellm` dependency and generalize LLM config to one model+key pair

**Description:** Add `litellm` to backend dependencies. Add `pytest-asyncio` (or equivalent) to the
`dev` extra and configure it, since Task 2 introduces this codebase's first testable async
function (see Technical Context's testing-infrastructure-gap note). Replace `app/config.py`'s
`anthropic_api_key`/`anthropic_model` fields with a single `llm_model: str` /
`llm_api_key: str | None` pair. No behavior change to the running app yet — this task only adds
config surface and dependencies; `booking_intent.py` still uses the old Anthropic-specific fields
until Task 3.

**Files to modify:**
- `B2B_BE/pyproject.toml` — add `litellm` to `dependencies`; add `pytest-asyncio` (or equivalent) to
  the `dev` extra and its pytest config; remove `anthropic>=0.40` only after Task 3 confirms nothing
  imports it anymore and `litellm` doesn't require it transitively (verify at implementation time —
  `litellm` implements the Anthropic Messages API itself over HTTP and is not expected to require
  the `anthropic` SDK as a runtime dependency, but this must be confirmed against the installed
  package's actual dependency tree, not assumed).
- `B2B_BE/app/config.py` — remove `anthropic_api_key` and `anthropic_model`; add
  `llm_model: str = "anthropic/claude-haiku-4-5-20251001"` (provider-prefixed, per `litellm`'s
  routing convention) and `llm_api_key: str | None = None`.
- `B2B_BE/.env.example` — remove `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL`; add
  `LLM_MODEL=anthropic/claude-haiku-4-5-20251001` and `LLM_API_KEY=`.

**New files to create:** None.

**Dependencies:** None.

**Complexity:** `Low`

**Testing requirements:**
- Unit test that `Settings()` loads `llm_model`'s default and that `LLM_MODEL`/`LLM_API_KEY` env-var
  overrides are picked up — mirrors whatever pattern (if any) already exists for testing `Settings`;
  none exists today, so a minimal one is acceptable scope here since it directly tests this task's
  change.
- No test requires a real provider API key or a live call.

**Documentation updates:**
- `B2B_BE/.env.example` (listed above, counts as the documentation update for this task).

---

### Task 2: Build the provider abstraction (`app/agent/providers/`)

**Description:** Add `app/agent/providers/base.py` defining `ToolCall`, `LLMResponse`, and the
`LLMProvider` `Protocol` (`async def generate(*, system, messages, tools) -> LLMResponse`), and
`app/agent/providers/litellm_provider.py` defining `LiteLLMProvider`, which implements `generate()`
by calling `litellm.acompletion()` and mapping its response into `LLMResponse`/`ToolCall` — per the
full shape in Technical Context above. This is the "generic handler for all AI providers" the
ticket asks for: `generate()` takes no Anthropic-specific or OpenAI-specific parameter names, and
its `tools`/response shape is the general OpenAI-function-calling shape `litellm` already
normalizes every provider to — not a single-forced-tool-only signature. No multi-turn loop, no
tool-dispatch mechanism, and no second provider implementation are built here (see Out of Scope).

Indicative shape (final field/method naming is an implementation-time decision within this shape,
not fixed by this plan):

```python
# app/agent/providers/base.py
from typing import Protocol

class ToolCall:
    def __init__(self, id: str, name: str, args: dict): ...

class LLMResponse:
    def __init__(self, text: str | None, tool_calls: list[ToolCall], raw_message: dict): ...

class LLMProvider(Protocol):
    async def generate(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...
```

```python
# app/agent/providers/litellm_provider.py
import json
import litellm

class LiteLLMProvider:
    def __init__(self, model: str, api_key: str | None): ...

    async def generate(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        resp = await litellm.acompletion(
            model=self.model,
            api_key=self.api_key,
            messages=[{"role": "system", "content": system}, *messages],
            tools=tools,
        )
        msg = resp.choices[0].message
        tool_calls = [
            ToolCall(tc.id, tc.function.name, json.loads(tc.function.arguments))
            for tc in (msg.tool_calls or [])
        ]
        return LLMResponse(msg.content, tool_calls, msg.model_dump())
```

**Files to modify:** None (this task only adds new files).

**New files to create:**
- `B2B_BE/app/agent/providers/__init__.py`
- `B2B_BE/app/agent/providers/base.py`
- `B2B_BE/app/agent/providers/litellm_provider.py`

**Dependencies:** Task 1 (needs `litellm` installed, `pytest-asyncio` configured, and
`settings.llm_model`/`llm_api_key` to exist for the caller Task 3 will build, though this task's own
tests do not require live settings — they mock `litellm.acompletion` directly).

**Complexity:** `Medium` — the response-shape assumption flagged in Technical Context must be
confirmed against the real installed `litellm` version as the first step of implementing this
task, before writing `LiteLLMProvider.generate()`'s extraction logic against it.

**Testing requirements:**
- Unit test with `litellm.acompletion` mocked/monkeypatched as an async mock (no live
  network/provider call, per `base-rules.md`'s happy-flow-only scope) verifying: `generate()`
  builds the expected `messages`/`tools` request shape (system prepended, `messages` passed
  through, `tools` passed through unchanged), and correctly maps a representative mocked
  OpenAI-style tool-call response into an `LLMResponse` with one or more `ToolCall`s (including a
  case with zero tool calls, since the general shape allows an empty list — not just the
  single-tool-call case the one real caller happens to use today).
- No test requires a real Anthropic, OpenAI, or other provider API key.

**Documentation updates:** None beyond each module's own docstring.

---

### Task 3: Migrate `parse_booking_intent()` to the provider abstraction

**Description:** Replace the direct `anthropic.Anthropic(...)` construction and
`client.messages.create(...)` call in `parse_booking_intent()` with construction of a
`LiteLLMProvider(model=settings.llm_model, api_key=settings.llm_api_key)` and a call to its
`generate(...)`, passing the same system prompt content as `system`, a one-element `messages` list
built from the customer's `text` (`[{"role": "user", "content": text}]`), and the existing
`BookingIntent.model_json_schema()`-derived schema now wrapped in the OpenAI function-calling shape
(`tools=[{"type": "function", "function": {"name": _TOOL_NAME, "description": ..., "parameters":
BookingIntent.model_json_schema()}}]`) instead of the current Anthropic-native `tools`/
`tool_choice` shape. The provider is constructed inline inside `parse_booking_intent`, mirroring
today's inline `anthropic.Anthropic(...)` construction — no dependency-injection container or
provider factory is introduced, since there is exactly one call site and no evidence yet that one
is needed.

`parse_booking_intent` becomes `async def` (unchanged from the previous plan version — its only
caller today is test/future code; nothing in the current codebase calls it synchronously, per the
existing docstring calling it a "hook point" not yet wired into `booking_agent.py`). It reads
`response.tool_calls[0]` (raising a clear, specific error if `tool_calls` is empty — this is where
"no tool call returned" is a business-meaningful condition, since this caller genuinely requires
one; `LiteLLMProvider` itself stays agnostic about whether an empty `tool_calls` list is an error,
per Task 2) and parses its `args` into `BookingIntent`, replacing today's `tool_use.input` parsing.
Behavior (the `ServiceNotStatedError` gate, the known-service resolution, the return shape
`BookingIntent`) is otherwise unchanged — only how the LLM is called changes.

**Files to modify:**
- `B2B_BE/app/agent/booking_intent.py` — remove `import anthropic`; import and use
  `app.agent.providers.litellm_provider.LiteLLMProvider`; change `parse_booking_intent` to
  `async def`; build the `messages`/`tools` request as described above; read
  `response.tool_calls[0].args` into `BookingIntent` in place of `tool_use.input`.

**New files to create:** None.

**Dependencies:** Task 2.

**Complexity:** `Low`

**Testing requirements:**
- Existing-behavior-preserving unit tests for `parse_booking_intent`, run against
  `LiteLLMProvider.generate` (or the constructed provider instance) mocked — not a live provider
  call: known-service match resolves `service_name` to the catalog's exact string
  (case-insensitive input); unmatched service raises `ServiceNotStatedError`; omitted
  `requested_time`/`staff_preference` stay `None`.
- A unit test for the "no tool call returned" path at this layer (empty `tool_calls`), since this
  is where that condition is actually handled per the design above.
- Since `parse_booking_intent` is now `async def`, its test(s) use the `pytest-asyncio` setup added
  in Task 1 — there is no pre-existing async-test convention elsewhere in `tests/` to match instead
  (verified during this revision; see Technical Context).
- No test in this task exercises a live Anthropic or other provider call (see Out of Scope).

**Documentation updates:**
- Update `parse_booking_intent`'s docstring to no longer describe an Anthropic-specific call if any
  such detail is currently implied beyond what was read (current docstring is already
  provider-agnostic in its description of behavior, so this may be a no-op — confirm at
  implementation time).

---

### Task 4: Migrate `catalog_intent.py` and `availability_intent.py` to the provider abstraction

**Description:** Added post-Gate-3, during Task 1 (see Overview's Amendment note). Both files
follow the exact same pattern `booking_intent.py` used before Task 3: `anthropic.Anthropic(api_key=
settings.anthropic_api_key)`, `client.messages.create(model=settings.anthropic_model, ...,
tools=[schema], tool_choice={"type": "tool", "name": ...})`, then
`next(block for block in response.content if block.type == "tool_use")`. Migrate each onto
`LiteLLMProvider`/`generate()` exactly as Task 3 did for `booking_intent.py`:

- `catalog_intent.py::is_catalog_change_request(text)` — construct `LiteLLMProvider(model=
  settings.llm_model, api_key=settings.llm_api_key)`; call `generate(system=..., messages=
  [{"role": "user", "content": text}], tools=[{"type": "function", "function": {"name":
  _TOOL_NAME, "description": ..., "parameters": _CatalogChangeClassification.model_json_schema()}}])`;
  read `response.tool_calls[0].args` into `_CatalogChangeClassification` in place of
  `tool_use.input`. Becomes `async def`. Raise a clear, specific error if `tool_calls` is empty
  (mirrors Task 3's "no tool call returned" handling — this caller also genuinely requires one).
- `availability_intent.py::parse_availability_change(text, *, staff_name, now=None)` — same
  migration shape, using `_ExtractedAvailabilityWindow` as the tool schema. Becomes `async def`.
  Same empty-`tool_calls` handling as above.
- Update each function's callers, if any exist in this codebase, to `await` the now-async call
  (verify at implementation time — per the plan's Technical Context, neither function is wired
  into `booking_agent.py`/`manager_agent.py` yet, so this is expected to be a no-op, but must be
  confirmed rather than assumed, exactly as Task 3 already required for `parse_booking_intent`).

**Files to modify:**
- `B2B_BE/app/agent/catalog_intent.py` — remove `import anthropic`; import and use
  `LiteLLMProvider`; change `is_catalog_change_request` to `async def`; build the request as
  described above; read `response.tool_calls[0].args` into `_CatalogChangeClassification`.
- `B2B_BE/app/agent/availability_intent.py` — remove `import anthropic`; import and use
  `LiteLLMProvider`; change `parse_availability_change` to `async def`; build the request as
  described above; read `response.tool_calls[0].args` into `_ExtractedAvailabilityWindow`.

**New files to create:** None.

**Dependencies:** Task 2 (provider abstraction must exist). Independent of Task 3 otherwise — can
run in parallel with it since the two touch disjoint files — but committed after Task 3 in this
plan's task order for clarity.

**Complexity:** `Low` — identical shape to Task 3, applied twice.

**Testing requirements:**
- Existing-behavior-preserving unit tests for `is_catalog_change_request` (currently covered by
  `tests/test_catalog_intent.py`, which is what Task 1 broke) against a mocked
  `LiteLLMProvider.generate` — not a live provider call.
- A new unit test (or tests) for `parse_availability_change` against a mocked
  `LiteLLMProvider.generate`, since this plan's Technical Context confirmed no test currently
  covers it — closing the silent-failure gap the Amendment note above identified, not just
  preserving existing coverage.
- A unit test for the "no tool call returned" path for each function, mirroring Task 3.
- No test in this task exercises a live Anthropic or other provider call.

**Documentation updates:**
- Update each function's docstring to no longer describe an Anthropic-specific call if any such
  detail is currently implied beyond what was read (same confirm-at-implementation-time caveat as
  Task 3).

---

## External Dependencies

- **`litellm` package** (PyPI) — new dependency, not yet installed anywhere in this repo. Available
  now (public package); no approval gate beyond `base-rules.md`'s "mature, widely-used" guardrail,
  which `litellm` (a widely-adopted, actively maintained unification library) satisfies.
- **`pytest-asyncio` package** (PyPI, or equivalent `anyio` pytest plugin) — new dev dependency,
  needed because this ticket introduces the first genuinely async unit-testable functions in
  `B2B_BE` (verified: no existing async test or config today).
- **Anthropic API key** (`settings.llm_api_key`, used with `settings.llm_model` set to an
  `anthropic/...` model) — required to validate the migrated Anthropic path actually still works
  end-to-end; available today per the existing `.env` setup (not newly introduced by this ticket).
- **OpenAI / Gemini / Grok API keys** — NOT available in this environment. Any end-to-end
  verification against those providers is therefore out of scope (see below); the abstraction is
  designed to be provider-agnostic by construction, but only the Anthropic path is actually
  exercised in this pass.

---

## Testing Strategy

| Test Type | Scope | Tooling |
|---|---|---|
| Unit | `app/agent/providers/litellm_provider.py`'s request-building/response-mapping logic, against a mocked `litellm.acompletion`; `app/config.py`'s new settings fields | `pytest` + `pytest-asyncio` (per `base-rules.md` — "Backend: `pytest`, run from `B2B_BE/`") |
| Integration | `parse_booking_intent()`'s end-to-end behavior (service resolution, `ServiceNotStatedError` gate, empty-`tool_calls` error path), `is_catalog_change_request()`'s classification behavior, and `parse_availability_change()`'s window-extraction behavior — all against the mocked provider, not a live LLM call, consistent with `base-rules.md`'s happy-flow-only scope | `pytest` + `pytest-asyncio` |
| End-to-End | Not planned. A real Anthropic call could optionally be exercised manually (not as an automated test) using the existing Anthropic key to confirm the migrated path still produces a valid `BookingIntent` — left to Developer discretion at implementation time, not a required deliverable of this plan | Manual / `pytest` if added |

Minimum coverage expectation: per `base-rules.md`'s Testing Requirements, this project is explicitly
happy-flow-only for the current build — no exhaustive edge-case/defensive coverage is required.
Test authoring itself happens in a later workflow phase; the requirements above state *what* should
eventually be tested, not a demand to write it now.

---

## Security Considerations

- No change to authentication/authorization posture — this ticket only changes how an LLM call is
  made, not who can trigger it.
- Secrets handling is unchanged in kind (provider API key read from `app/config.py` / `.env`, never
  hardcoded) — `llm_api_key` replaces `anthropic_api_key` in the exact same pattern.
  `.env.example` is updated with placeholder (blank) values only, consistent with
  `base-rules.md`'s Security Baselines.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `litellm`'s actual tool-calling response shape for Anthropic models differs in some detail from the OpenAI-style shape assumed in Task 2 (e.g. `tool_calls` absent/differently nested for a given `litellm` version) | Med | Med | Task 2 explicitly requires confirming the real shape against the installed `litellm` version before writing `LiteLLMProvider.generate()`'s extraction logic, and Task 3 includes an explicit empty-`tool_calls` error path rather than assuming success silently |
| `litellm` pulls in a heavier transitive dependency set than expected (it optionally depends on/imports several provider SDKs) | Low | Low | Check the actual installed dependency tree during Task 1 before deciding whether to also remove `anthropic>=0.40`; flag to the user if the footprint is a real concern rather than silently accepting it |
| `LLM_MODEL` now requires a provider-prefixed model string (e.g. `anthropic/claude-haiku-4-5-20251001`) per `litellm`'s routing convention — a bare, unprefixed model name may still resolve for some well-known models but is not guaranteed across `litellm` versions | Low | Low | `config.py`'s default and `.env.example`'s example value both use the prefixed form, so the correct convention is discoverable immediately rather than left to guesswork |
| Renaming `anthropic_api_key`/`ANTHROPIC_MODEL` → `llm_api_key`/`LLM_MODEL` (and requiring the provider prefix) is a breaking config-name/value change for anyone with a real `.env` already set | Low | Low | This is a pre-production hackathon-scale build (`base-rules.md` context) with no deployed `.env` beyond local dev; `.env.example` is updated in the same task so the rename is discoverable immediately |
| No `pytest-asyncio` (or equivalent) currently configured, and no existing async-test convention to follow | Low | Low | Task 1 adds and configures it explicitly as part of this ticket's own scope, rather than assuming it already exists (verified absent during this revision) |
| No OpenAI/Gemini/Grok key available means the "generic for all providers" claim is only actually verified for Anthropic in this pass | Med | Low | Explicitly named in Out of Scope below; `LLMProvider`'s request/response shape is provider-agnostic by construction (no Anthropic-specific parameter names), so the residual risk is in `litellm`'s own non-Anthropic support, not this codebase's code — noted, not silently hidden |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 | `Low` |
| Task 2 | `Medium` |
| Task 3 | `Low` |
| Task 4 | `Low` |
| **Overall** | `Medium` |

---

## Out of Scope

- **Wiring a running multi-turn tool-call loop** (the `while True: ... dispatch tool ... append
  tool result ... loop` pattern) into `booking_agent.py` or `manager_agent.py`. Both remain hook
  points after this ticket, exactly as they are today — this ticket only builds the reusable
  `LLMProvider`/`LiteLLMProvider`/`ToolCall`/`LLMResponse` seam and migrates the one existing caller
  onto it; it does not change *when* an LLM gets called, only *how*.
- **A generic cross-tool dispatch registry** (mapping tool names to callable tool functions across
  `app/tools/*.py`). Verified during this revision: `app/tools/services.py`, `staff.py`, and
  `customers.py` are each standalone async functions with no existing dispatcher of this kind —
  this is not already-covered infrastructure being skipped, it genuinely does not exist yet. Building
  one is still out of scope for this ticket (only the LLM-provider seam is in scope); it is a
  natural next ticket once `booking_agent.py`'s reasoning loop is actually implemented and needs to
  route multiple `ToolCall`s to real tool functions.
- **A new LLM call site beyond the three that already exist.** The Booking/Manager Agent's own
  reasoning loop (beyond intent/classification parsing) is not implemented or wired to the new
  abstraction — only the three existing calls (`booking_intent.py`, `catalog_intent.py`,
  `availability_intent.py`, per Task 4's amendment) are migrated. `LLMProvider`/`LiteLLMProvider`
  are designed for straightforward reuse, not built out for a call site that doesn't exist yet.
- **A second `LLMProvider` implementation.** Only `LiteLLMProvider` is built. The `Protocol` is
  designed so a future non-`litellm` implementation is possible without changing callers, but no
  second implementation is written now.
- **OpenAI/Gemini/Grok end-to-end live verification.** No API key for any of these is available in
  this environment. `LiteLLMProvider`'s request/response handling is provider-agnostic by
  construction, but no task in this plan requires actually exercising a non-Anthropic call; if the
  user has a key, that verification can be done manually outside this plan's required deliverables.
- **Streaming responses.** `litellm` supports streaming; nothing in this codebase currently needs
  it, so `generate()` does not add it speculatively.
- **Removing the ability to run against Anthropic.** Anthropic remains fully supported (as the
  default `llm_model` value) — this ticket adds provider flexibility, it does not migrate the
  running default away from Anthropic.
- **Test authoring itself.** Per the workflow phase this plan belongs to, only *testing
  requirements* are recorded per task above; writing the actual test code happens in a later
  phase/gate.
- **Any change to `booking_agent.py` or `manager_agent.py` beyond what is already true today** (they
  remain independent of `booking_intent.py`, per `booking_agent.py`'s own docstring — verified
  unchanged in this revision).

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-14` · Branch: `feature/APPOINTMEN-14-llm-provider-integration`*
