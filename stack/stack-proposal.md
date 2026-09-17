---
title: Stack Proposal — Agentic Appointment Management Engine (Salon Edition)
status: approved
owner: Architect
created: 2026-09-17
updated: 2026-09-17
approved_date: 2026-09-17
sources:
  - bmad-output/planning-artifacts/prd/prd-salon-app-2026-09-17/prd.md
  - bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/brief.md
  - bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-17/addendum.md
  - CLAUDE.md (repository layout constraint)
gate: "Gate 3 — Stack Approval: APPROVED by user on 2026-09-17, unchanged from this document. The user's
  only question (Twilio WhatsApp integration path) was answered by confirming §6.2's Sandbox
  recommendation already covers it; no revision was requested."
---

# Stack Proposal — Agentic Appointment Management Engine (Salon Edition)

## 0. Starting-state check (verified before drafting)

Confirmed via direct repository inspection before writing this proposal, not assumed:

- `stack/` contains only `stack/README.md` (generic mechanism doc). No prior `stack-proposal.md`,
  `rules/base-rules.md`, or `rules/client-rules.md` exists. There is no prior approved decision to
  reconcile against — this is a fresh proposal, not a revision.
- `B2B_BE/` and `B2B_FE/` do not yet exist / contain no files. There is no existing code convention to
  preserve or contradict; every recommendation below is unconstrained by legacy code, but is still bound
  by `CLAUDE.md`'s fixed `B2B_BE/`/`B2B_FE/` top-level split for all application code.
- The user's stated leaning (Flutter + FastAPI + Postgres, `addendum.md` §2.2–2.4) is evaluated on its
  merits against the PRD below, not rubber-stamped — see each section's rationale and the "Where the
  stated leaning is confirmed vs. refined" note in §8.

## 1. Frontend

**Recommendation: React + TypeScript (Vite), one codebase serving two thin surfaces — the Web Chat
widget and the Owner Dashboard.**

**What drove this:**
- PRD §3 (Glossary) and §4.1/§4.2 name exactly two browser-facing surfaces: the Web Chat widget and the
  read-only Dashboard. Both are simple, chat-or-list rendering surfaces with no offline or native-device
  requirement (PRD §6.1, §6.2 — no payments, no device integration, no push notifications).
- PRD UJ-6 / FR-32 require the Dashboard to reflect shared-store changes live, without a manual refresh —
  this needs a client capable of a WebSocket or polling connection; both are trivial in a standard SPA
  stack.
- PRD NFR §7 (24-hour build window) rewards a stack with the fastest available path to a working chat UI
  (message bubbles, typing/streaming indicators, confirm/cancel affordances for FR-9/FR-18/FR-27's
  required explicit-confirmation steps) — the React ecosystem has the deepest supply of ready-made,
  MIT-licensed chat-UI components and examples of any frontend ecosystem as of this proposal.

**Resolving the "web chat" technology ambiguity (`addendum.md` §2.4 item 7 / PRD §9.2):** the Web Chat
widget and the Dashboard use the **same** technology (React + TypeScript), not Flutter-web and not two
different web stacks. Rationale: both are read/write- or read-only browser surfaces against the same
backend API, built by the same team in the same 24 hours; sharing one component library and API client
between them (`B2B_FE/src/shared/`) is strictly less work than maintaining two frontend stacks, and
nothing in the PRD asks for the Dashboard and Web Chat to diverge technologically.

**Why not Flutter (the stated leaning) for the web surfaces:** Flutter's central value proposition —
one codebase spanning mobile + web + desktop — is not realized here, because **no native mobile app is
in scope for this MVP** (see §4, Mobile, below, for the full reasoning). Stripped of that benefit,
Flutter-web is evaluated purely as a web technology and loses on three PRD-relevant points: (a) Flutter
web's renderer produces heavier initial payloads and weaker out-of-the-box accessibility than a
React SPA, a real cost for a widget meant to embed lightly into a business's site; (b) the ecosystem of
ready-made chat-UI patterns and examples for Flutter-web is materially thinner than React's, which
matters directly against the 24-hour NFR; (c) Dart/Flutter tooling has no advantage over
TypeScript/React once the backend is Python/FastAPI (no shared-language benefit either way). Flutter is
not ruled out for the future — see Constraints (§9) — but nothing in this PRD earns its cost today.

**Alternatives considered:**
- **Flutter-web** (the stated leaning) — rejected for the reasons above: its cross-platform payoff is
  moot with no mobile app in scope, and it is weaker than React specifically as a web-only technology for
  a 24-hour chat-UI build.
- **Plain vanilla JS/HTML widget (no framework)** — rejected: the Dashboard needs live-updating state
  (WebSocket-driven) and the chat widget needs conversational UI state (message history, in-flight
  confirmation prompts); a minimal component framework removes more risk than it costs to set up, and a
  shared component layer between the two surfaces needs *some* structure to avoid duplicated work.
- **Server-rendered templates (e.g., Jinja2 from FastAPI directly)** — rejected: FR-32's live-update
  requirement (Dashboard reflects shared-store changes without a manual refresh) and the chat widget's
  need for streaming/incremental agent responses both fit a client-side reactive framework much more
  naturally than a full-page-reload templating approach.

## 2. Backend

**Recommendation: FastAPI (Python 3.12+), one deployable service hosting both agents.**

**What drove this — evaluated against the PRD's actual technical demands, not accepted as a given:**
- Nearly every FR in the PRD (FR-5, FR-6–FR-9, FR-15–FR-17, FR-25–FR-27) depends on LLM-based
  natural-language intent parsing and tool/function-calling. Python has the deepest, most current
  ecosystem of LLM provider SDKs and structured-output/tool-calling helpers of any backend language as of
  this proposal — this is the single most build-time-relevant factor given the PRD's dominant technical
  risk (`addendum.md` §3: "LLM intent-parsing reliability for a live demo").
- `addendum.md` §2.2 confirms the agent-to-tool pattern: the agent calls the backend's *own* functions,
  registered as tools in the LLM's tool-use loop, never touching the DB directly. FastAPI's native
  Pydantic integration means a tool's argument schema, its HTTP request schema (if also exposed via API),
  and its LLM function-calling schema can all derive from one model definition — directly reducing
  duplicate schema-authoring work under the 24-hour constraint.
- FastAPI is async-native, which matches the actual call shape of the tool-use loop (LLM call → tool
  execution → DB query → LLM call again) — a chain of I/O-bound waits, not CPU-bound work.
- Twilio's official Python SDK is mature for both webhook parsing and TwiML/REST reply construction
  (`addendum.md` §2.3), reducing integration risk against the WhatsApp/Twilio setup-lead-time risk
  flagged in `addendum.md` §3.
- SQLAlchemy + Alembic map directly onto the minimal relational data model already specified in
  `addendum.md` §2.1 (salon, services, staff/owner with roles, bookings, availability).

**Alternatives considered:**
- **Node.js/Express (TypeScript)** — this was the *actual* prior founder-locked stack for the
  now-deleted marketplace-era product. Rejected for this iteration: Node's LLM SDKs are serviceable, but
  Python's agent/tool-orchestration and structured-output ecosystem is materially deeper, and no PRD
  requirement pulls toward Node specifically. Flagged explicitly per this agent's evidence obligations:
  the codebase does **not** contradict this choice — the old Node proposal was deleted by the user, not
  present, so there is no existing convention being overridden.
- **Django (Python)** — rejected: a heavier, batteries-included framework (ORM + admin + templating) is
  more machinery than this scope needs; FastAPI's minimalism and native async fit an agent-orchestration
  service better, and Django's synchronous-by-default ORM patterns add friction to the tool-call loop.
- **Go (Gin/Fiber or similar)** — rejected: strong concurrency, but an immature LLM/agent-tooling
  ecosystem compared to Python as of this proposal; would directly slow the PRD's highest-risk area
  (intent-parsing reliability) within a fixed 24-hour window.

## 3. Database

**Recommendation: PostgreSQL 16+ as the single primary store for all domain data (services, staff/owner
records, bookings, availability) and for conversation/session state (§6 below). Postgres is confirmed
formally here, not accepted silently, per `addendum.md` §4 row 9.**

**What drove this:**
- The data model in `addendum.md` §2.1 is explicitly relational: one salon, its services, three
  staff/owner records with roles, a bookings table, an availability table — with real foreign-key
  relationships (a booking references a staff member, a service, a customer).
- FR-9, FR-18, FR-27 all require "no write until explicit confirmation" — atomicity between the
  confirmation event and the resulting write matters, and FR-12 requires the old slot to be freed
  "before or atomically with" the new booking being created. Postgres's transactional guarantees satisfy
  this directly.
- FR-26's conflict check needs to reason about overlapping time windows for a staff member. Postgres's
  native range types (`tstzrange`) and `EXCLUDE USING gist` constraints give first-class support for this
  exact query shape (see §7, Conflict-Detection Mechanism, below).
- PRD §4.4 (Shared Data Store) is the demo's core proof point, and `addendum.md` §3 explicitly flags
  "shared-state race conditions between the two agents" as a top risk to the single most visible demo
  moment — a real relational database with transactions and constraints is the safest way to protect that
  moment, not a corner to cut.
- NFR §7 permits "minimal or in-memory" persistence as a floor if it speeds the build — Postgres does not
  trade against this: standing up Postgres in Docker takes minutes, not meaningfully slower than an
  in-memory store, while removing an entire class of concurrent-write-correctness risk.

**Alternatives considered:**
- **SQLite** — rejected as the primary store: weaker concurrent-write behavior under the
  two-agent-simultaneous-write scenario that is central to the demo's proof point, and no
  exclusion-constraint-grade support for time-range conflict backstops. Given Postgres-in-Docker is
  essentially as fast to stand up, there is no compelling reason to accept SQLite's concurrency
  weaknesses for this specific demo.
- **MongoDB / a document store** — rejected: the data model is explicitly relational (FK relationships
  between bookings, staff, services); a document model would force re-deriving referential integrity and
  double-booking prevention in application code that Postgres already provides via constraints and
  transactions — added risk for no benefit within 24 hours.
- **Pure in-memory Python structure (the NFR-permitted floor, taken literally)** — rejected as the
  primary store despite being PRD-permitted: hand-rolling correct locking/transaction semantics for
  concurrent agent writes in-process is *more* implementation risk than just using Postgres, which gives
  it for free. This satisfies the letter of NFR §7 (minimal is acceptable) while being materially safer
  against the demo's own flagged top risk.

## 4. Mobile — N/A for this MVP (explicit, not a silent omission)

**No native mobile app (iOS/Android) is proposed, and none is in scope for this MVP.**

**Reasoning, re-derived directly from the PRD, not assumed:** PRD §2 (personas), §4.1, and §4.2 name
exactly two channels a Customer, Staff member, or Owner/Admin can use to reach either agent: **Web Chat**
(a browser-based widget) and **WhatsApp** (reached via the salon's business number). WhatsApp itself is
the client application for that channel — there is no separate installed app to build, because the
customer already has WhatsApp installed and the backend only needs to speak Twilio's webhook/TwiML
protocol to it. No FR, user journey (UJ-1–UJ-6), or NFR in the PRD references a native iOS/Android app.
The brief's own "Vision (Post-MVP)" section (which explicitly lists deferred future capabilities:
multi-service/multi-person booking, voice channel, payments, ratings, staff specialization, stronger
auth, domain-agnostic packaging) also does not mention a native mobile app — so this is not a corner
being cut from a stated future requirement either; it is simply absent from every artifact.

This differs from the old, fully-deleted marketplace-era plan, which did include a Flutter mobile app —
that plan's mobile requirement is not carried forward into this PRD, and this proposal does not
reintroduce it by inertia from the user's Flutter-leaning statement (that statement's origin was the
prior marketplace-era discussion; the current PRD does not repeat the mobile requirement that motivated
it).

This stack does not preclude adding a native or cross-platform mobile client later if a real requirement
emerges post-MVP (the backend is channel-agnostic — REST/WebSocket API plus a Twilio webhook — so a
mobile client would be a new frontend consuming the same API, not a backend rework). It is not designed
into the current proposal, per this agent's scope boundary against speculative future-proofing; it is
recorded as a future option under Constraints (§9), not built now.

## 5. Infrastructure

Scoped explicitly to a 24-hour hackathon build, not a production deployment — per PRD NFR §7.

**Containerization:** a `Dockerfile` in each of `B2B_BE/` and `B2B_FE/`, plus one root-level
`docker-compose.yml` orchestrating the backend, frontend, and Postgres for local dev/demo parity. This
`docker-compose.yml` is infrastructure/orchestration configuration referencing both folders — like
`CLAUDE.md` or `README.md`, it is not itself application code and is not a new top-level *application*
folder, so it does not conflict with `CLAUDE.md`'s `B2B_BE/`/`B2B_FE/` split; flagged explicitly here so
it is not mistaken for an exception being smuggled in.

**Hosting for the demo:** two viable options, both appropriate for 24 hours — the team should pick based
on how much they want the demo to depend on a laptop staying online:
1. **Local + tunnel (recommended default):** run `docker-compose up` locally; expose the backend
   publicly via ngrok or a Cloudflare Tunnel so Twilio's WhatsApp webhook has a reachable HTTPS URL. This
   is the fastest path to a working WhatsApp integration and directly mitigates the Twilio
   provisioning/lead-time risk flagged in `addendum.md` §3 by avoiding any cloud deployment step entirely.
2. **Single-service PaaS (Railway, Render, or Fly.io) deploying the same Dockerfiles** — a reasonable
   fallback if the team prefers not to depend on a laptop's network connection during judging; costs a
   few extra minutes of setup over option 1 for materially better demo-day reliability.

Full cloud infrastructure (e.g., AWS ECS/Fargate, managed Kubernetes) is explicitly **not** recommended:
no NFR in the PRD asks for production-grade scaling, and adding cloud-infra setup on top of the
already-flagged Twilio lead-time risk works against the 24-hour constraint rather than for it.

**CI/CD:** no pipeline is required by any PRD requirement. A single, optional GitHub Actions workflow
running backend tests (`pytest`) and a lint pass on push is a reasonable nice-to-have; a full
build/test/deploy pipeline is out of scope for this build window.

## 6. Key Libraries / Services

### 6.1 Agent-to-tool boundary: direct in-process registration, not MCP

**Recommendation: direct in-process tool registration** — Python functions with Pydantic-derived JSON
schemas, passed directly to the LLM provider's native tool/function-calling parameter. **Reject the
sketched MCP server layer for this MVP.**

**What drove this:** `addendum.md` §2.2 confirms both agents call the backend's *own* functions
(`check_availability`, `book_appointment`, `update_availability`), never external third-party APIs, and
that the agent never touches the DB directly — this pattern is confirmed; the open question is only the
*mechanism*. MCP's value is realized when tools must be discoverable/consumable by an external,
arbitrary MCP-compliant client, or when tool implementations must live in a separate process/service from
the agent loop. Neither condition holds here: both agents and all tool implementations live in one
backend service, sharing one DB connection pool, and nothing in the PRD asks for a third-party agent host
to consume these tools. Standing up an MCP server would add a network hop (agent → MCP client → MCP
server → domain function → DB), extra serialization, and another moving part to build and debug — for
zero present functional benefit — directly working against the "scope-to-time ratio" risk `addendum.md`
§3 flags for this exact build.

A useful secondary benefit of in-process registration: each agent gets its **own scoped tool registry**
per role (Booking Agent's registry; Manager Agent's Staff-mode registry; Manager Agent's Owner/Admin-mode
registry), which becomes a natural, code-level enforcement point for the role-based permission FRs
(FR-21–FR-23, FR-28–FR-30: a tool simply isn't registered/offered to a session identified as the wrong
role) — a defense-in-depth mechanism the MCP-server sketch did not call out.

**Alternatives considered:**
- **MCP server layer (the informally sketched approach)** — rejected for the reasons above. Not
  disqualified forever: if the product's stated B2B "plug into any business" framing
  (`brief.md`, Executive Summary) later needs to expose these tools to *external*, third-party agent
  hosts, MCP becomes the right tool for that problem — noted under Constraints (§9) as a deliberate,
  revisitable choice, not an oversight.
- **A heavyweight agent framework (e.g., LangChain-style chains/graphs)** — rejected as the tool-boundary
  layer: its abstractions add conceptual overhead beyond what two coordinated, deterministic tool-calling
  loops with explicit human-confirmation steps (FR-9, FR-18, FR-27, and the SM-4a/b/c checkpoints) need.
  A thin, direct call to the LLM provider's native tool-calling API is easier to reason about and easier
  to insert the required confirmation checkpoints into explicitly. A lightweight structured-output
  convenience library (e.g., `pydantic-ai`, `instructor`) is compatible with this decision either way
  since it does not add a network hop — left as a Developer-phase implementation detail, not an
  architecture-locking choice.

**LLM provider:** not locked by this proposal — any provider with a mature native tool/function-calling
API (Anthropic Claude or OpenAI's current GPT-4.x/5-class models are both viable) satisfies the boundary
decision above, since it is provider-agnostic. The specific model should be pinned in `base-rules.md` at
Gate 3 approval time, once the team confirms which provider's API keys/quota are available for the
hackathon.

### 6.2 WhatsApp integration

Twilio's WhatsApp **Sandbox** (not a production WhatsApp Business Account) via Twilio's Python SDK, with
a FastAPI webhook endpoint receiving inbound messages and replying via TwiML or Twilio's REST API. This
directly addresses `addendum.md` §3's flagged risk ("WhatsApp Business API / Twilio setup lead time
within a 24-hour window") by avoiding the business-number verification process entirely — the Sandbox
requires each demo phone number to be pre-joined ahead of time (an operational step, not a code change;
noted under Constraints, §9). `addendum.md` §2.3's confirmed shape (channel-specific logic — webhook
parsing, TwiML formatting — kept as thin adapters, never forking the core agent/tool-use loop per
channel) is adopted as-is.

**Gate 3 clarification recorded:** the user asked, at approval time, whether this Sandbox recommendation
already covers the Twilio WhatsApp integration path end-to-end. Confirmed yes — §6.2 as written (Sandbox
+ Python SDK + FastAPI webhook + thin channel adapter, never forking core agent logic) is the complete
answer; no addition or revision to this section was requested, and none was made.

### 6.3 Auth

None beyond phone-number lookup, per PRD §7 exactly as stated — no password, OTP, or session-token
authentication anywhere in the system, for Customers (FR-1–FR-3) or Staff/Owner (FR-14, FR-24).

### 6.4 Session / conversation-state handling — backend-persisted, not client-resent

**Resolving `addendum.md` §4 row 8:** conversation state is **persisted server-side**, keyed by
`(channel, phone_number)` — not resent as full history by the client each turn.

**What drove this — an elimination forced by the PRD's own channel-parity NFR, not a stylistic
preference:** PRD §7 requires Booking Agent and Manager Agent behavior to be identical in substance
across Web Chat and WhatsApp, with only the identity-question mechanics differing. WhatsApp's delivery
model (via Twilio) is a hard constraint here, not a design choice: each inbound webhook call delivers
only the new message plus the sender's phone number — there is no client-side chat log for a WhatsApp
user's device to "resend." A client-resends-full-history approach is therefore **not viable on WhatsApp
at all**, which means adopting it even for Web Chat alone would make the two channels' state-handling
mechanism diverge — directly violating the channel-parity NFR. Backend-persisted state is the only
approach that serves both channels identically, and it reuses the identity key the PRD already
establishes (phone number) rather than inventing a client-generated session token, which would sit
uncomfortably close to the auth mechanism the NFR explicitly wants to avoid.

**Storage:** a `messages` table in the same Postgres instance (`session_id`/`(channel, phone_number)`,
`role`, `content`, `created_at`) — a small incremental addition given Postgres is already justified for
domain data (§3), and more resilient against a mid-demo process restart than a pure in-memory dict. An
in-memory dict keyed the same way remains NFR-compliant as a fallback if time runs short, but is not the
primary recommendation given the storage is already available at no extra infra cost.

**Alternative considered:** client resends full history each turn — rejected as the primary mechanism for
the channel-parity reason above; it is not merely "not preferred," it is architecturally incompatible with
uniform behavior across WhatsApp and Web Chat.

## 7. Conflict-Detection Mechanism (FR-26)

FR-26 specifies the *behavior*: before applying a block, check the proposed window against existing
bookings, and if a conflict exists, **name which booking(s) cause it** — not a silent rejection, and not
"the database rejected it." `addendum.md` §2.4 item 6 sharpens this beyond the brief's simpler
"rule-based check" framing; this proposal adopts the sharper, explainability-bearing version as the
actual requirement, since FR-26's own testable consequences already demand it.

**Recommendation — two-layered:**
1. **Primary, explicit application-level check (satisfies FR-26 directly):** a domain function,
   `check_conflicts(staff_id, proposed_window)` (living in `B2B_BE/app/domain/conflicts.py`), queries
   existing bookings for that staff member overlapping the proposed window — using a Postgres
   `tstzrange` column and the `&&` overlap operator, or an equivalent `start < proposed_end AND end >
   proposed_start` query — and returns the **specific conflicting booking row(s)** (customer, service,
   time) as structured data. This is called as its own explicit step in the agent's tool-use loop,
   *before* any write, which is also exactly where the SM-4c human-verification checkpoint (PRD §8) sits.
   The agent uses this structured result to phrase the explainable response FR-26 requires (e.g., "Friday
   10am is already booked with a customer for a haircut").
2. **Secondary, DB-level backstop (protects the demo's core proof point, §4.4):** a Postgres
   `EXCLUDE USING gist` constraint on the same time-range column, as a safety net against a genuine race
   between the two agents writing near-simultaneously — `addendum.md` §3 explicitly flags shared-state
   race conditions as a top risk to the single most visible demo moment. This constraint is never the
   source of the customer/staff-facing explanation; it exists only to guarantee correctness if the
   application-level check is ever raced.

**Alternatives considered:**
- **Bare DB constraint only** — explicitly rejected, per `addendum.md` §2.4 item 6 and FR-26's own
  testable consequences: a constraint violation gives no structured, nameable booking detail without a
  follow-up query anyway, so the explicit application-level check is necessary regardless of whether a
  constraint also exists.
- **Application-level check with no DB backstop** — rejected: given two agents can act concurrently on
  the same shared store (the demo's own central proof point), omitting a DB-level guarantee risks exactly
  the race-condition failure mode `addendum.md` §3 flags as a top risk.

## 8. §9.2-carried technical considerations (`addendum.md` §2.1) — adopted as-is or refined

- **Interface** (web chat + WhatsApp + dashboard) — adopted as-is; made concrete above (§1, §6.2).
- **Agents as coordinated services, not one mega-prompt** — adopted as-is, **refined**: "coordinated
  services" is implemented as two clearly separated agent modules
  (`B2B_BE/app/agent/booking_agent.py`, `B2B_BE/app/agent/manager_agent.py`), each with its own system
  prompt and scoped tool registry, running within **one deployable backend process** — not as literally
  separate deployable microservices. No FR or NFR in the PRD asks for independent scaling or independent
  deployment cadence between the two agents, and splitting them into separate network services would add
  deployment/networking complexity the 24-hour NFR does not reward. The "not a mega-prompt" requirement is
  satisfied at the module/prompt level, which is what it actually protects against.
- **Intent parsing** — adopted as-is, **refined** to a specific mechanism: the LLM's native tool/function
  calling interface *is* the intent-parsing mechanism (the model selects which tool to call and with what
  extracted arguments) rather than a separate upstream NLU pipeline (e.g., spaCy/regex) feeding into the
  agent. This is simpler (one model call per turn), matches the already-confirmed
  "agent decides intent → agent calls tool" pattern (`addendum.md` §2.2), and reduces build surface within
  24 hours.
- **Conflict detection** — refined per §7 above: the addendum's own sharper, explainability-bearing
  framing is adopted as the real requirement, not the brief's simpler "rule-based check" phrasing.
- **Data model** — adopted as-is; mapped directly onto Postgres tables: `salons`, `staff` (with a `role`
  enum: owner/admin, staff), `services`, `bookings`, `availability`, plus `messages` for conversation
  state (§6.4). A `salons` table is included even though this MVP seeds exactly one salon, since it is a
  trivially small addition and keeps the stated B2B "plug into any business" framing (`brief.md`,
  Executive Summary) honest without overbuilding anything else for multi-tenancy.

## 9. Repository Layout — `B2B_BE/` / `B2B_FE/` nesting

Per `CLAUDE.md`'s fixed, authoritative split, the informally sketched backend package layout
(`addendum.md` §2.4 item 3) is nested under `B2B_BE/` in full, and an equivalent structure is proposed
for the frontend under `B2B_FE/`. The `mcp/` directory from the original sketch is **not** carried
forward, per the §6.1 decision above; it is replaced by `app/tools/`.

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
      state/                   # conversation-state read/write (see §6.4)
    tools/                     # in-process tool registrations (replaces the sketched mcp/ layer)
      services.py
      staff.py
      availability.py
      appointments.py
    domain/
      appointments.py
      availability.py
      conflicts.py             # explicit conflict-check mechanism (§7)
    models/                    # SQLAlchemy models
    repositories/               # DB access layer
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

docker-compose.yml             # orchestration only — not application code; see §5
```

## 10. Constraints — what this stack rules out for the future

- **Rejecting MCP now** means: if the stated B2B "plug into any business" vision later needs to expose
  booking/availability tools to *external*, third-party agent hosts (not just this app's own two agents),
  that is a genuine re-architecture — wrapping today's in-process functions in a network-facing MCP (or
  equivalent) server — not a config flip. This is a deliberate, revisitable near-term choice, not an
  oversight.
- **A single Postgres instance** rules out, without later work, an eventually-consistent multi-region or
  horizontally-sharded write path — irrelevant to this single-salon hackathon demo, but would need
  revisiting for genuine multi-tenant B2B scale (already out of scope per PRD §5/§6.2).
- **No mobile app in this proposal** means the React web frontend does not directly reuse code for a
  future native app the way a Flutter-web choice would have — a real new frontend build, not a recompile,
  if native mobile ever becomes an actual requirement. Accepted deliberately because no current PRD
  artifact (including the Vision/Post-MVP list) asks for it.
- **No auth beyond phone lookup** rules out any near-term customer self-service account or payment
  feature (both already out of scope per PRD §5) without adding a real identity layer first.
- **Twilio WhatsApp Sandbox** (recommended for the demo) rules out receiving messages from arbitrary,
  un-joined WhatsApp numbers in front of judges unless each demo phone number is pre-joined to the sandbox
  ahead of time — an operational/procedural constraint the team must handle before demo day, not a
  code-level fix.
- **Role-scoped in-process tool registries** are a lightweight convention, not a hard security boundary —
  since there is no real authentication (per NFR §7), a determined actor with direct API access could
  still call the underlying FastAPI endpoints out-of-band, bypassing the LLM+tool-registry gate. This is
  an accepted risk given the NFR's explicit auth-minimalism, not a defect in this proposal, and this stack
  should not be described as "secure" beyond what a hackathon demo needs.

## 11. Open items for Gate 3

None of the eight PRD §9.2 carried-forward items remain unresolved by this proposal (see §8 map below).
The one thing this document cannot decide for itself is approval: per this agent's scope boundary, stack
approval is a human decision (Gate 3), not this agent's own judgement, regardless of how confident the
recommendation above is.

**Resolved at Gate 3 (2026-09-17):** the user approved this proposal unchanged. The user's sole
clarifying question — whether the Twilio WhatsApp integration path was fully covered — was answered by
confirming §6.2's Sandbox recommendation already addresses it end-to-end (see the note appended to §6.2).
No open items remain against this document. Downstream: `stack/rules/base-rules.md` is now the locked
coding-rules artifact derived from this approved stack; the UX Designer and Developer agents build
against it, not against this proposal directly.
