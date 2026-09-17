---
title: Addendum — Agentic Appointment Management Engine — Salon Edition
status: draft
created: 2026-09-17
updated: 2026-09-17
---

# Addendum: Agentic Appointment Management Engine — Salon Edition

Companion to `brief.md`. Holds persona depth, the full technical-considerations discussion, risks, and the assumptions/open-questions log. Everything here is sourced from either (a) the user's finalized project-brief document, reproduced verbatim to this run, or (b) the user's prior-session architecture discussion, also reproduced to this run. Nothing here is fabricated market data or invented stakeholder positions — where a point is this pass's own discovery-flagged finding rather than user-supplied, it is labeled as such.

## 1. Personas (Depth)

### Customer — Primary
Wants to book a salon appointment without navigating a slot-picker UI, in plain language, on whichever channel (web chat or WhatsApp) they're already on. Identity key: phone number, collected conversationally, no password/OTP/session. New customer → agent also asks for name → creates a record → proceeds to booking. Returning customer → agent greets by name → skips straight to booking intent. Can, at any point in the conversation: browse services & pricing, book, view upcoming/past bookings, cancel, or reschedule (treated as cancel + re-run the normal booking flow).

### Ramesh — Owner/Admin
Runs the 4-chair unisex salon; 3 staff report to him in the seed data (himself plus Meena and Arjun — see role table). Permitted actions: add/edit/delete services & pricing via the Manager Agent (natural language); view the staff list and current bookings via the read-only dashboard. **[ASSUMPTION]** Treated as admin-only for this demo — he does not take customer appointments himself and does not manage his own availability, since that action is not in the confirmed scope. **This is the source brief's own unresolved open question (its §10):** *"Is Ramesh also a bookable service provider that customers can choose, or purely an admin who doesn't take appointments?"* Still open; owner: human/stakeholder, not the Architect or PM to decide unilaterally.

### Meena — Staff
Provides services at the salon. Only system action: manage her own availability (block/unblock) via the Manager Agent, in natural language (e.g., "block out Friday morning, I'm out" / "unblock Saturday"). Cannot edit pricing/services, cannot view the staff list or dashboard, cannot touch Arjun's or Ramesh's schedule.

### Arjun — Staff
Same shape as Meena: availability management only, no catalog access, no dashboard access, no cross-staff schedule access.

### Identity model (all three staff/owner personas)
Pre-seeded records, not created through signup. Web chat: agent asks for phone number, looks it up against the pre-seeded staff list. WhatsApp: phone number is already known from the channel, lookup happens immediately with no question asked. Match → Manager Agent knows who is talking, their role, and acts accordingly. No match → out of scope for the demo.

### Role-based permission matrix (source brief §6.2, reproduced)

| Action | Owner/Admin (Ramesh) | Staff (Meena, Arjun) |
|---|---|---|
| Block/unblock own availability | No | Yes |
| Add/edit/delete services & pricing | Yes | No |
| View staff list | Yes | No |
| View bookings (dashboard) | Yes | No |
| Override another staff member's schedule | No | No |

## 2. Technical Considerations

**Framing:** everything in this section is a starting point for the Architect phase, per the source brief's own §8 framing (`[ASSUMPTION — starting points for the Architect phase]`) and per the separate architecture-discussion session the user had before this brief was formalized. None of it is a locked PRD-level or brief-level technical decision; the PM/brief layer surfaces it, the Architect resolves it. This is also consistent with agent scope boundaries: the Product Manager does not own architecture, technical implementation, or UX decisions.

### 2.1 From the source brief itself (§8)
- **Interface:** web chat UI and WhatsApp Business API integration, both fronting the same agent core, plus a simple read-only dashboard page for the Owner/Admin.
- **Agents:** two distinct agents (Booking Agent, Manager Agent) sharing one availability/bookings data store — architected as coordinated sub-tasks/services, not one shared mega-prompt.
- **Intent parsing:** NLU/LLM-based parsing of date/time/service/staff preference from free text, plus cancel and reschedule intents.
- **Conflict detection:** simple rule-based check against existing bookings when the Manager Agent applies a change.
- **Role-based permission check:** Manager Agent checks the requester's role before acting.
- **Data model (minimal for demo):** one salon, its services, three staff/owner records with roles, a bookings table, an availability table.
- **No production concerns needed for demo:** scaling/persistence beyond the demo session can be minimal/in-memory if that speeds the build.

### 2.2 Confirmed high-level agent-to-tool pattern (prior-session architecture discussion, explicitly confirmed by the user)
Chat message → agent decides intent → agent calls one of the backend's own functions (registered as tools in the LLM tool-use loop) → FastAPI executes it against the DB → result returns to the agent → agent phrases the reply in natural language. The user explicitly confirmed these are the backend's own functions (`check_availability`, `book_appointment`, `update_availability`) registered as tools — not external third-party APIs — and that the agent never touches the DB directly. This pattern itself is treated as confirmed; the *mechanism* by which tools are exposed to the agent (MCP vs. direct in-process registration, §2.4 below) is not.

### 2.3 "Same agent, every channel" — a discovery finding for the Architect
A WhatsApp channel flow was diagrammed in the prior session, confirming: WhatsApp is a second front door to the *same* agent core, not a second agent. Entry differs (customer → Twilio → backend webhook, with `business_id` resolved from the receiving Twilio number); the middle tool-use loop is identical to the web chat flow; the exit differs (reply returned as TwiML through Twilio instead of a WebSocket push). This constrains the Architect phase: channel-specific logic (Twilio webhook parsing, TwiML formatting, WebSocket push) must stay isolated at the edges as thin adapters, and must not fork or duplicate the core agent/intent-parsing logic per channel.

### 2.4 Open architecture items explicitly flagged for the Architect phase (not to be resolved here)

1. **Stack pivot vs. an existing approved-and-locked stack decision — highest-priority conflict.** The user is currently leaning toward Flutter for the chat frontend, FastAPI (Python) for the backend API layer, and Postgres for the database. This is a *change* from the salon-app marketplace-era approved stack. Critically, `stack/stack-proposal.md` in this repository (status: `approved`, dated 2026-09-05) states: *"Stack fixed by founder decision. Flutter (mobile) and Node.js (backend) are not open for re-evaluation at MVP."* That document specifies Node.js + Express (TypeScript) for the backend, not FastAPI/Python. The new pivot direction directly contradicts a decision that document explicitly forecloses re-opening. This is not a routine stack question for the Architect to quietly re-derive — it is a standing, founder-locked decision that a new direction now conflicts with, and it needs explicit human/founder sign-off before the Architect treats FastAPI as the direction, not just an Architect-phase technical evaluation. Flagging this conflict, not resolving it, is this brief's job.
2. **MCP vs. direct in-process tool registration.** A proposed backend package layout was sketched in the prior session using an MCP (Model Context Protocol) server layer for tools (`mcp/server.py` + `mcp/tools/{services,staff,availability,appointments}.py`) rather than plain in-process function registration. This is a meaningful architecture choice — the agent-to-tool boundary — that the Architect phase must evaluate explicitly, not inherit as a given because it was sketched informally.
3. **Repo-layout conflict.** The sketched layout (`backend/app/main.py`, `api/{chat,appointments,availability}.py`, `agent/{agent,prompts,state,tools}.py`, `mcp/...`, `domain/{appointments,availability,conflicts}.py`, `models/`, `repositories/`, `config.py`, `tests/`, `alembic/`, `pyproject.toml`) is not directly compatible with this repository's `CLAUDE.md`, which mandates a fixed, authoritative `B2B_BE/` (backend) / `B2B_FE/` (frontend) top-level split for all application code. The sketched tree would need to nest under `B2B_BE/`, with a Flutter equivalent nested under `B2B_FE/`, rather than being adopted as top-level folders. This is an open item for the Architect phase to resolve, not something settled here.
4. **Conversation state persistence.** Unresolved from the prior session: does the Flutter client resend full chat history each turn, or does the backend persist session/conversation state (a DB row, or an in-memory dict keyed by session id)? Open for the Architect.
5. **Postgres as a starting point, not a re-opened question.** Postgres was the working DB choice in the prior architecture discussion. Per the user's own framing, it should be treated as the Architect's starting point rather than re-opened as "any possible DB" — noted here so the Architect does not spend cycles re-litigating a choice the user has already leaned into, while still formally confirming it as part of Phase 3. (This is consistent with the founder-locked stack proposal's Postgres choice too, so it is the one part of the pivot direction that does *not* conflict with the standing approved decision.)
6. **Conflict detection must be explicit and explainable.** Also raised in the prior session: conflict detection must be an explicit pre-write check the agent can reason about and explain (e.g., "why did this booking fail"), not simply "the DB will reject it" via a constraint. This is a design requirement the Architect must carry forward, distinct from the source brief's simpler "[HACKATHON SCOPE] simple rule-based check" framing — the two are compatible but the explainability requirement is the sharper bar.
7. **"Web chat" technology ambiguity — this pass's own discovery finding, not sourced from either input document.** The source brief's §8 describes "Web chat UI" as one of the two customer/staff channels, distinct from "a simple read-only dashboard page." The prior-session architecture discussion separately describes "Flutter for the chat frontend." It is not established whether the web chat widget is a Flutter-web build of the same chat frontend used for (a hypothetical) mobile, a separate web technology from the dashboard, or the same technology as the dashboard. Flagging this for the Architect to resolve; not assumed one way or the other here.

## 3. Risks (Discovery Pass)

These are engineering/product risks surfaced by reading the brief and architecture discussion against a 24-hour hackathon constraint — not sourced from user-supplied research, since none was volunteered for this pass.

- **LLM intent-parsing reliability for a live demo.** Free-text parsing of service/date/time/staff-preference, plus cancel/reschedule intent, must work reliably enough for a live, judged demo; the source brief explicitly defers non-happy-path handling (ambiguous intent) as a "known limitation," which narrows but does not eliminate this risk for the happy-path cases actually being demoed.
- **WhatsApp Business API / Twilio setup lead time within a 24-hour window.** Business-number provisioning, webhook configuration, and template/session-message rules for WhatsApp Business (via Twilio, per the architecture discussion) can carry approval lead times that do not fit neatly inside a 24-hour build; this needs an early go/no-go check, not a late-stage discovery.
- **Shared-state race conditions between the two agents.** The Booking Agent (writes bookings) and Manager Agent (writes availability) both act against one shared data store; the demo's core proof point (a Manager Agent change is "immediately reflected" in the Booking Agent) depends on this being handled correctly, and race conditions here would undermine the single most visible demo moment.
- **Scope-to-time ratio.** Two customer-facing channels (web chat, WhatsApp) × two agent surfaces (Booking, Manager) × a live dashboard, built to a happy-flow-only bar, is still substantial surface area for 24 hours; sequencing and cut-lines should be an explicit Architect/Developer-phase concern.
- **External dependency risk (WhatsApp/Twilio).** Because the WhatsApp channel routes through a third-party (Twilio) webhook and TwiML reply path, any outage, rate limit, or sandbox restriction on that third party during the live demo window is a risk outside the team's direct control.

## 4. Assumptions & Open Questions — Resolution Log

| # | Item | Status | Source | Owner |
|---|---|---|---|---|
| 1 | Ramesh is admin-only, not a bookable service provider | Open — unresolved | Source brief §4, §10 (its own flagged open question) | Human/stakeholder |
| 2 | No traditional business KPIs tracked for the hackathon demo | Open (working assumption unless overridden) | Source brief §5 | Human/stakeholder |
| 3 | §8 technical considerations (interface, agents, intent parsing, conflict detection, data model) are Architect-phase starting points, not locked | Open by design — Architect to confirm/refine each | Source brief §8 | Architect |
| 4 | Stack pivot (Flutter + FastAPI + Postgres) vs. approved-and-locked stack (Node.js/Express + Flutter mobile + Postgres) | **Open — direct conflict, high priority** | Prior-session architecture discussion vs. `stack/stack-proposal.md` (status: approved) | Human/founder sign-off, then Architect |
| 5 | Confirmed agent-to-tool pattern (own backend functions as registered tools, agent never touches DB directly) | Resolved — treated as confirmed direction | Prior-session architecture discussion (user explicitly confirmed) | — |
| 6 | MCP tool layer vs. direct in-process tool registration | Open | Prior-session architecture discussion (sketched, not evaluated) | Architect |
| 7 | Repo-layout conflict: sketched `backend/app/...` tree vs. authoritative `B2B_BE/`/`B2B_FE/` split | Open | `CLAUDE.md` vs. prior-session sketch | Architect |
| 8 | Conversation state persistence (client resends history vs. backend-persisted session) | Open | Prior-session architecture discussion | Architect |
| 9 | Postgres as DB starting point | Resolved as a starting point (not re-opened as "any possible DB"); formal confirmation still owed | Prior-session architecture discussion; consistent with `stack/stack-proposal.md` | Architect (to formally confirm) |
| 10 | Conflict detection must be an explicit, explainable pre-write check, not a bare DB constraint | Resolved as a design requirement to carry forward | Prior-session architecture discussion | Architect/Developer |
| 11 | Specific human-verification moment to showcase during the build | Open — unresolved | Source brief §10 (its own flagged open question) | Human/whole team |
| 12 | "Web chat" frontend technology ambiguity (Flutter-web vs. separate web tech vs. same as dashboard) | Open — surfaced during this discovery pass, not from either source document | This brief's own discovery finding | Architect |

No item above has been resolved unilaterally by this brief where it constitutes an architecture, technical, or UX decision — those remain open for the Architect or UX Designer, or for the human where a business decision is required (items 1, 2, 4, 11).
