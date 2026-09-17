---
title: Base Coding Rules — Agentic Appointment Management Engine (Salon Edition)
status: approved
approved_date: 2026-09-17
owner: Architect
source: stack/stack-proposal.md (status: approved, 2026-09-17 — Gate 3)
---

# Base Coding Rules

> Generated from the approved tech stack (`stack/stack-proposal.md`, approved at Gate 3 on 2026-09-17).
> Do not edit without Architect sign-off recorded in this file's frontmatter.
> To add project- or client-specific rules, use `stack/rules/client-rules.md`. Where a client rule
> conflicts with a rule here, the client rule wins and the override must be documented there — this file
> is not edited to accommodate it.

## Stack

| Layer | Technology | Version / Constraint |
|---|---|---|
| Frontend | React + TypeScript (Vite) | React 18+, TypeScript 5+, Vite 5+. One codebase serving both the Web Chat widget and the Owner Dashboard (`B2B_FE/`). |
| Backend | FastAPI (Python) | Python 3.12+, FastAPI 0.11x+. One deployable service hosting both the Booking Agent and the Manager Agent (`B2B_BE/`). |
| Database | PostgreSQL | 16+. Single primary store for domain data and conversation/session state. |
| Mobile | N/A | No native or cross-platform mobile app in scope for this MVP (stack-proposal.md §4). Do not build one speculatively. |
| Infra | Docker Compose | One `Dockerfile` per top-level folder (`B2B_BE/`, `B2B_FE/`) plus a root `docker-compose.yml` orchestrating backend + frontend + Postgres. Demo hosting: local + tunnel (ngrok/Cloudflare Tunnel) as default, or a single-service PaaS (Railway/Render/Fly.io) as fallback. No managed-Kubernetes/ECS-class infra. |
| WhatsApp channel | Twilio WhatsApp Sandbox + Twilio Python SDK | Sandbox, not a production WhatsApp Business Account, for this build. |
| LLM provider | Not locked here | Any provider with a mature native tool/function-calling API (Anthropic Claude or OpenAI current-generation). Pin the specific model/provider in a config value once API keys are confirmed — this is an implementation detail, not an architecture lock. |

## Language & Style

**Backend (`B2B_BE/`, Python):**
- Python 3.12+ everywhere. Type hints are required on every function signature (parameters and return
  type) — this is not optional style, it is what makes Pydantic-derived tool/API schemas
  (stack-proposal.md §2) work correctly.
- All request/response/tool-argument schemas are Pydantic models (`pydantic` v2). A tool's LLM
  function-calling schema, its HTTP request/response schema (where also exposed via API), and its
  internal argument type all derive from the same Pydantic model — do not hand-write a second schema for
  the same shape.
- Formatter: `black`, default settings. Linter: `ruff` (covers import sorting and common correctness
  checks — no separate `isort`/`flake8`). Both run with default/near-default config; do not hand-tune
  extensive per-project rule sets for a 24-hour build.
- Async/await for all I/O-bound code in the request and tool-call path (DB queries, LLM calls, Twilio
  calls) — FastAPI's async support exists specifically to match the LLM-call → tool-execution →
  DB-query → LLM-call chain (stack-proposal.md §2); do not write blocking synchronous I/O inside an
  `async def` request handler.
- No bare `except:` — catch specific exceptions. Given the happy-flow-only scope (Testing Requirements
  below), this is about not silently swallowing genuine bugs, not about building defensive error
  taxonomies.

**Frontend (`B2B_FE/`, TypeScript):**
- TypeScript strict mode (`"strict": true` in `tsconfig.json`) — no `any` used to bypass typing; use
  `unknown` plus a narrowing check where a type is genuinely not known ahead of time.
- Function components with hooks only. No class components.
- Formatter: `prettier`, default settings. Linter: `eslint` with the standard
  `@typescript-eslint/recommended` + `eslint-plugin-react-hooks` rule sets. Do not hand-roll a custom
  rule set for this build.
- API calls to the backend go through the typed client in `B2B_FE/src/api/` (see Architecture
  Constraints) — no ad-hoc `fetch`/`axios` calls scattered through component code.

## Architecture Constraints

**Enforced repository layout** (from stack-proposal.md §9 — reproduced here as the binding structure,
not merely illustrative):

```text
B2B_BE/
  pyproject.toml
  Dockerfile
  alembic/                     # DB migrations
  app/
    main.py                    # FastAPI app entrypoint
    config.py
    api/
      chat.py                  # Web Chat REST/WebSocket endpoints
      appointments.py
      availability.py
      dashboard.py             # read-only dashboard data endpoints
      webhooks/
        whatsapp.py            # Twilio inbound webhook + TwiML reply
    agent/
      booking_agent.py
      manager_agent.py
      prompts/
      state/                   # conversation-state read/write
    tools/                     # in-process tool registrations
      services.py
      staff.py
      availability.py
      appointments.py
    domain/
      appointments.py
      availability.py
      conflicts.py             # explicit conflict-check mechanism (FR-26)
    models/                    # SQLAlchemy models
    repositories/              # DB access layer
  tests/

B2B_FE/
  package.json
  Dockerfile
  src/
    chat/                      # Web Chat widget (Booking Agent + Manager Agent conversation UI)
    dashboard/                 # Owner Dashboard (read-only staff list + bookings)
    shared/                    # component library + hooks shared by chat and dashboard
    api/                       # typed client for the B2B_BE API
  tests/

docker-compose.yml             # orchestration only — not application code
```

New top-level folders under `B2B_BE/app/` or `B2B_FE/src/` beyond this tree require an Architect
decision recorded as a decision entry or ADR, not an ad-hoc addition mid-implementation.

**Required patterns:**
- **In-process tool registration, not a network-facing tool-exposure layer.** Every tool the Booking
  Agent or Manager Agent can call is a Python function in `B2B_BE/app/tools/`, registered directly with
  the LLM provider's native tool/function-calling parameter, with its schema derived from a Pydantic
  model. A tool calls into `app/domain/` and `app/repositories/` — it never lets the LLM touch the
  database directly.
- **Role-scoped tool registry per agent/role, as the access-control mechanism.** Each agent/role gets
  its own registry of available tools, assembled per session from the caller's identified role:
  - Booking Agent (Customer-facing) — its own registry.
  - Manager Agent, Staff mode — a registry scoped to staff-permitted tools only.
  - Manager Agent, Owner/Admin mode — a registry scoped to owner/admin-permitted tools only.
  A tool that a role should not be able to invoke MUST simply not be registered into that role's
  registry for that session — this is the enforcement point for FR-21–FR-23 and FR-28–FR-30, and it is
  required, not optional scaffolding.
- **Two clearly separated agent modules, one deployable process.** `booking_agent.py` and
  `manager_agent.py` are separate modules with separate system prompts and separate tool registries,
  both running inside the single `B2B_BE` FastAPI service — not one combined mega-prompt, and not two
  independently deployed services.
- **Channel logic stays a thin adapter; core agent/intent-parsing logic never forks per channel.** Web
  Chat and WhatsApp are both thin adapters (`app/api/chat.py` and `app/api/webhooks/whatsapp.py`
  respectively) that translate a channel-specific message format into the same call into
  `app/agent/booking_agent.py` / `manager_agent.py`, and translate the same agent response back into the
  channel's reply format. There is exactly one intent-parsing / tool-calling loop per agent, shared by
  both channels — never a WhatsApp-specific or Web-Chat-specific branch of the actual agent reasoning or
  tool-selection logic. This is required by the PRD's channel-parity NFR (stack-proposal.md §6.4), not a
  style preference.
- **Backend-persisted conversation state**, keyed by `(channel, phone_number)`, in the `messages` table
  (or an in-memory dict fallback keyed identically, only if time-constrained) — never a client-resends-
  full-history-each-turn design, for either channel.
- **Conflict detection is two-layered and the application-level check is mandatory, not optional.**
  `check_conflicts(staff_id, proposed_window)` in `B2B_BE/app/domain/conflicts.py` runs as an explicit
  step before any booking/availability write, returning the specific conflicting booking(s) as
  structured data (FR-26). A Postgres `EXCLUDE USING gist` constraint on the time-range column is the
  required DB-level backstop underneath it — the backstop does not replace the explicit check, and the
  explicit check is never skipped because the constraint exists.

**Forbidden:**
- **No MCP server layer for tool exposure**, for now (stack-proposal.md §6.1, §10). Do not stand up an
  MCP server, MCP client, or add an MCP SDK dependency to route agent-to-tool calls. This is a
  deliberate, revisitable near-term constraint tied to the current single-process, two-internal-agent
  shape — not a permanent architectural stance. Revisiting it is an Architect decision (new ADR), not
  something introduced ad hoc during implementation.
- **No forking of core agent/intent-parsing logic per channel.** Do not write a WhatsApp-specific
  version of intent parsing, tool selection, or agent reasoning that diverges from the Web Chat version
  ("same agent, every channel" — addendum §2.3, carried into the PRD's channel-parity NFR). Channel
  differences are confined to the thin adapter layer only.
- **No client-resent conversation history** as the session-state mechanism (see Required patterns
  above) — architecturally incompatible with the channel-parity requirement given WhatsApp's delivery
  model.
- **No heavyweight agent orchestration framework** (e.g., LangChain-style chains/graphs) as the
  tool-boundary layer. A thin, direct call to the LLM provider's native tool-calling API is required
  instead (stack-proposal.md §6.1). A lightweight structured-output convenience library
  (e.g., `pydantic-ai`, `instructor`) is permitted since it does not add a network hop or replace the
  direct-call pattern.
- **No full cloud infrastructure** (AWS ECS/Fargate, managed Kubernetes, etc.) for this build. Docker
  Compose plus local-and-tunnel or a single-service PaaS only.

## Naming Conventions

**Backend files/folders** — per the enforced tree above: singular, lowercase, snake_case module names
matching their domain concept (`appointments.py`, `availability.py`, `conflicts.py`); package directories
are lowercase, no underscores where a single word suffices (`api/`, `agent/`, `tools/`, `domain/`,
`models/`, `repositories/`).

**Frontend files/folders** — per the enforced tree above: lowercase, kebab-case for multi-word component
folders (e.g., `booking-confirm/`), PascalCase for component filenames (e.g., `ChatWindow.tsx`), camelCase
for hooks (`useConversation.ts`) and utility modules.

**API routes** — REST resource paths are lowercase, kebab-case, plural nouns: `/appointments`,
`/availability`, `/services`, `/staff`, `/dashboard`. Webhook routes are grouped under `/webhooks/`, e.g.
`/webhooks/whatsapp`. WebSocket/streaming chat endpoint: `/chat` (or `/ws/chat` if a distinct WS path is
needed alongside a REST chat endpoint) — pick one and keep it consistent, do not run both a REST and a
WS variant for the same purpose.

**Database tables** — snake_case, plural, per standard Postgres convention, matching the domain model in
stack-proposal.md §8:
- `salons`
- `staff` (includes a `role` enum column distinguishing owner/admin vs. staff — Ramesh is a `staff` row
  with `role = owner_admin`, never a separately-modeled entity, and never bookable per PRD Decision 1)
- `services`
- `bookings`
- `availability`
- `messages` (conversation/session state, keyed by `(channel, phone_number)`)

Foreign key columns follow `<referenced_table_singular>_id` (e.g., `bookings.staff_id`,
`bookings.service_id`). Do not introduce a table name outside this list without recording the addition as
a decision (this is a small, fixed domain model — an unplanned new table is a signal to check the
requirement against the PRD first).

## Testing Requirements

- **Backend:** `pytest`, run from `B2B_BE/`. **Frontend:** no framework is mandated by this proposal
  beyond what Vite/React ship with by default; if frontend tests are written, use Vitest + React Testing
  Library (the standard pairing for a Vite + React stack) rather than introducing a second, heavier test
  runner.
- **The PRD is explicitly happy-flow-only for this hackathon demo** (PRD §5, §6.2; handoff.md
  Constraints). Defensive and edge-case coverage — ambiguous intent, zero availability, malformed input,
  concurrent-write stress beyond what the DB constraint already guarantees — is **explicitly not
  required** for this build. Do not spend build time writing exhaustive edge-case tests the PRD does not
  ask for; that time is better spent elsewhere given the 24-hour window.
- **Where testing time exists at all, prioritize it in this order:**
  1. The three confirm-before-write behaviors — FR-9 (Booking Agent), FR-18, FR-27 — verifying that no
     booking/availability write occurs before the relevant human-confirmation step (SM-4a/b/c) is
     satisfied.
  2. The conflict-detection mechanism (FR-26) — `check_conflicts` returns the correct, specific
     conflicting booking(s) for an overlapping window, and no write proceeds when a conflict exists
     without the required confirmation/override step.
  3. Everything else, time permitting.
- Integration-style tests (hitting a real Postgres via `docker-compose`, not a mocked DB) are preferred
  for the two priorities above, since both are fundamentally about DB write ordering and transactional
  correctness, which a mocked repository layer would not actually verify.

## Security Baselines

- **Auth is phone-number lookup only, and this is explicitly not a real security boundary.** Per PRD §7
  and stack-proposal.md §6.3/§10: there is no password, OTP, session token, or any other identity
  verification anywhere in the system. Do not build a login flow, session-token issuance, password
  hashing, or an OTP mechanism for this project — none of that is in scope, and building it would be
  scope creep against an explicit PRD constraint, not a safety improvement worth adding unasked.
- **Role-scoped tool registries are the primary access-control mechanism** (see Architecture Constraints
  above), and they are a code-level convention, not a hard security boundary: a determined actor with
  direct API access could still call the underlying FastAPI endpoints out-of-band, bypassing the
  LLM+tool-registry gate entirely (stack-proposal.md §10). Do not describe this system as "secure" in any
  broader sense than "keeps the LLM-driven conversation flow honest about who can ask for what" — it does
  not protect against a malicious actor calling the API directly.
- **Standard input handling for LLM tool-calls:** every tool argument is validated by its Pydantic model
  before the tool body executes (type/shape validation is not optional even though deep defensive
  handling is out of scope) — this catches malformed LLM tool-call arguments as a normal Pydantic
  validation error, not a custom defensive layer.
- **Secrets** (LLM provider API key, Twilio Account SID/Auth Token/WhatsApp number) are read from
  environment variables via `app/config.py`, never hard-coded or committed. A `.env.example` (no real
  values) documents the required variables; the real `.env` is git-ignored.

## Dependency Policy

- **Favor mature, widely-used libraries over experimental ones**, consistent with the stack-proposal's
  "boring, proven" reasoning throughout (stack-proposal.md §2, §3, §6.1). The expected core dependency
  set:
  - Backend: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic` (v2), the official `twilio` Python
    SDK, an official LLM provider SDK (Anthropic or OpenAI), `pytest`.
  - Frontend: `react`, `react-dom`, `vite`, `typescript`; a WebSocket client only if the native
    `WebSocket` API is insufficient for the chosen chat-streaming approach.
- **No MCP SDK dependency for now**, per the tool-boundary decision in Architecture Constraints above
  (Forbidden). Adding one later is a re-architecture decision (new ADR), not a routine dependency bump.
- **No heavyweight agent-orchestration framework dependency** (LangChain-style chains/graphs) — see
  Architecture Constraints (Forbidden). A lightweight structured-output helper (`pydantic-ai`,
  `instructor`) is permitted at Developer discretion.
- New dependencies beyond the expected core set above are a Developer-phase discretion within the
  "mature, widely-used" guardrail — no formal dependency-approval gate is defined for this 24-hour build
  beyond that guardrail, but a dependency that would require its own infrastructure (a message queue, a
  vector store, a second database, a workflow engine) is out of scope and requires an Architect decision
  first, not an ad-hoc addition.
